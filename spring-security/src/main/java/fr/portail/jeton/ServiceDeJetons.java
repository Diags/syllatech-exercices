package fr.portail.jeton;

import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.security.oauth2.jose.jws.JwsAlgorithm;
import org.springframework.security.oauth2.jose.jws.SignatureAlgorithm;
import org.springframework.security.oauth2.jwt.JwsHeader;
import org.springframework.security.oauth2.jwt.JwtClaimsSet;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.JwtEncoderParameters;
import org.springframework.stereotype.Service;

/**
 * L'émetteur de jetons du portail.
 *
 * <p>Il produit trois choses, et la distinction est le sujet du chapitre 5 :
 *
 * <ul>
 *   <li>un <strong>access token</strong>, court, présenté à l'API à chaque
 *       appel. Il porte les rôles, au format KeyCloak — dans
 *       {@code realm_access.roles}, sans préfixe ;</li>
 *   <li>un <strong>ID token</strong>, qui décrit l'utilisateur pour le
 *       <em>client</em> et ne sert jamais à appeler l'API ;</li>
 *   <li>un <strong>refresh token</strong>, long, <strong>stocké ici</strong>
 *       et donc révocable — c'est toute la différence avec les deux autres.</li>
 * </ul>
 *
 * <p>Le chapitre 4 mesure la conséquence : révoquer un utilisateur ne fait
 * rien à son access token, qui reste valable jusqu'à son expiration. On ne
 * peut pas révoquer ce qu'on ne consulte pas.
 */
@Service
public class ServiceDeJetons {

    /** Volontairement très court : c'est la seule défense d'un jeton volé. */
    public static final Duration DUREE_ACCES = Duration.ofMinutes(5);

    public static final Duration DUREE_RAFRAICHISSEMENT = Duration.ofDays(30);

    /** L'émetteur. Le décodeur le vérifiera, claim par claim. */
    public static final String EMETTEUR = "https://portail.exemple.test";

    private final JwtEncoder encodeur;

    /**
     * Les refresh tokens encore valables.
     *
     * <p>C'est cette table qui rend la révocation possible : un refresh token
     * est un identifiant opaque qu'on retrouve ici, ou pas. L'access token,
     * lui, n'est écrit nulle part — et c'est précisément pourquoi il est
     * irrévocable.
     */
    private final Map<String, String> rafraichissements = new ConcurrentHashMap<>();

    ServiceDeJetons(JwtEncoder encodeur) {
        this.encodeur = encodeur;
    }

    /** Un access token signé, au format qu'émettrait KeyCloak. */
    public String acces(String utilisateur, List<String> roles) {
        return acces(utilisateur, roles, DUREE_ACCES);
    }

    public String acces(String utilisateur, List<String> roles, Duration duree) {
        var maintenant = Instant.now();
        var claims = JwtClaimsSet.builder()
                .issuer(EMETTEUR)
                .subject(utilisateur)
                .issuedAt(maintenant)
                .expiresAt(maintenant.plus(duree))
                .id(UUID.randomUUID().toString())
                .audience(List.of("portail-api"))
                // ⚠️ LE FORMAT KEYCLOAK. Les roles sont dans un claim
                // IMBRIQUE, et SANS le prefixe `ROLE_` qu'attend Spring.
                // Le chapitre 6 mesure ce que cela coute quand on n'a pas
                // pose le convertisseur.
                .claim("realm_access", Map.of("roles", roles))
                .claim("typ", "Bearer")
                .build();
        return signer(claims);
    }

    /**
     * Un jeton déjà expiré, pour le chapitre 4.
     *
     * <p>⚠️ Il faut reculer {@code issuedAt} AUSSI. Une première version se
     * contentait d'une durée négative, et {@code JwtClaimsSet} refusait de se
     * construire : « expiresAt must be after issuedAt ». Le garde-fou est du
     * bon côté — on ne fabrique pas par accident un jeton incohérent.
     */
    public String accesExpire(String utilisateur, List<String> roles) {
        var emis = Instant.now().minus(Duration.ofMinutes(10));
        var claims = JwtClaimsSet.builder()
                .issuer(EMETTEUR)
                .subject(utilisateur)
                .issuedAt(emis)
                .expiresAt(emis.plus(Duration.ofMinutes(5)))
                .id(UUID.randomUUID().toString())
                .audience(List.of("portail-api"))
                .claim("realm_access", Map.of("roles", roles))
                .build();
        return signer(claims);
    }

    /**
     * Un ID token : il décrit l'utilisateur, il n'ouvre aucune porte.
     *
     * <p>Remarquez ce qu'il n'a pas : ni {@code realm_access}, ni
     * {@code audience} vers l'API. Le présenter à l'API serait une erreur —
     * et le chapitre 5 mesure ce qu'elle produit.
     */
    public String identite(String utilisateur, String courriel, String nom) {
        var maintenant = Instant.now();
        var claims = JwtClaimsSet.builder()
                .issuer(EMETTEUR)
                .subject(utilisateur)
                .issuedAt(maintenant)
                .expiresAt(maintenant.plus(Duration.ofMinutes(5)))
                .audience(List.of("portail-spa"))
                .claim("email", courriel)
                .claim("name", nom)
                .claim("typ", "ID")
                .build();
        return signer(claims);
    }

    /** Un refresh token : opaque, stocké, donc révocable. */
    public String rafraichissement(String utilisateur) {
        String jeton = UUID.randomUUID().toString();
        rafraichissements.put(jeton, utilisateur);
        return jeton;
    }

    /** À qui appartient ce refresh token, s'il est encore valable ? */
    public java.util.Optional<String> porteurDu(String rafraichissement) {
        return java.util.Optional.ofNullable(
                rafraichissements.get(rafraichissement));
    }

    /** Révoque un refresh token. L'access token déjà émis, lui, survit. */
    public boolean revoquer(String rafraichissement) {
        return rafraichissements.remove(rafraichissement) != null;
    }

    public int rafraichissementsValables() {
        return rafraichissements.size();
    }

    /**
     * Un jeton signé avec un algorithme donné — pour le chapitre 4.
     *
     * <p>Sert à fabriquer les jetons que le décodeur doit <strong>refuser</strong>.
     */
    private String signer(JwtClaimsSet claims) {
        JwsAlgorithm algorithme = SignatureAlgorithm.RS256;
        var entete = JwsHeader.with(algorithme)
                .keyId(fr.portail.cles.Cles.IDENTIFIANT)
                .build();
        return encodeur.encode(JwtEncoderParameters.from(entete, claims))
                .getTokenValue();
    }
}
