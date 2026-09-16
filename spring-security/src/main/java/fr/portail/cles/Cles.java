package fr.portail.cles;

import com.nimbusds.jose.jwk.JWKSet;
import com.nimbusds.jose.jwk.RSAKey;
import com.nimbusds.jose.jwk.source.ImmutableJWKSet;
import com.nimbusds.jose.jwk.source.JWKSource;
import com.nimbusds.jose.proc.SecurityContext;
import java.security.KeyPair;
import java.security.KeyPairGenerator;
import java.security.NoSuchAlgorithmException;
import java.security.interfaces.RSAPrivateKey;
import java.security.interfaces.RSAPublicKey;
import java.util.UUID;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.oauth2.jwt.NimbusJwtEncoder;

/**
 * La paire de clés du portail, générée au démarrage.
 *
 * <p>Ce projet est son propre émetteur de jetons : il signe en RS256 avec la
 * clé privée, et publie la clé publique sur {@code /oauth2/jwks} — exactement
 * ce que fait un KeyCloak. Un jeton produit ici est donc un vrai JWT, validé
 * par le vrai {@link NimbusJwtDecoder} de Spring Security.
 *
 * <p>⚠️ <strong>Générée à chaque démarrage, et c'est voulu.</strong> Une clé
 * privée dans un dépôt Git est une clé compromise, et il n'existe pas de
 * façon « pédagogique » d'en poser une. Conséquence à connaître : les jetons
 * émis par un démarrage ne valent plus rien au suivant — c'est d'ailleurs ce
 * qui arrive à une flotte d'instances qui ne partagent pas leurs clés, et une
 * bonne raison de plus de déléguer l'émission à un serveur d'autorisation.
 *
 * <p>2048 bits : le minimum recommandé aujourd'hui pour RSA. Le chapitre 4
 * affiche la taille et l'algorithme, plutôt que de les affirmer.
 */
@Configuration
public class Cles {

    /** L'identifiant de la clé, celui qui apparaît dans l'en-tête du jeton. */
    public static final String IDENTIFIANT = UUID.randomUUID().toString();

    private final RSAPublicKey publique;

    private final RSAPrivateKey privee;

    public Cles() {
        var paire = engendrer();
        this.publique = (RSAPublicKey) paire.getPublic();
        this.privee = (RSAPrivateKey) paire.getPrivate();
    }

    public RSAPublicKey publique() {
        return publique;
    }

    public RSAPrivateKey privee() {
        return privee;
    }

    /** La clé, au format JWK — c'est ce que publie un point {@code /jwks}. */
    public RSAKey jwk() {
        return new RSAKey.Builder(publique)
                .privateKey(privee)
                .keyID(IDENTIFIANT)
                .build();
    }

    @Bean
    JWKSource<SecurityContext> sourceDeCles() {
        return new ImmutableJWKSet<>(new JWKSet(jwk()));
    }

    @Bean
    JwtEncoder encodeurDeJetons(JWKSource<SecurityContext> source) {
        return new NimbusJwtEncoder(source);
    }

    /**
     * Le décodeur que la chaîne de filtres utilisera.
     *
     * <p>Il n'est construit qu'à partir de la clé <strong>publique</strong> :
     * vérifier une signature ne demande jamais la clé privée. C'est ce qui
     * permet à dix services de valider les jetons d'un même émetteur sans que
     * l'un d'eux puisse en fabriquer.
     */
    @Bean
    JwtDecoder decodeurDeJetons() {
        return NimbusJwtDecoder.withPublicKey(publique).build();
    }

    private static KeyPair engendrer() {
        try {
            var generateur = KeyPairGenerator.getInstance("RSA");
            generateur.initialize(2048);
            return generateur.generateKeyPair();
        } catch (NoSuchAlgorithmException impossible) {
            throw new IllegalStateException("RSA absent de cette JVM", impossible);
        }
    }
}
