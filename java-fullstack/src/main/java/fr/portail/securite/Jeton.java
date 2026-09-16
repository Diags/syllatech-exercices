package fr.portail.securite;

import tools.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Instant;
import java.util.Base64;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * Un JWT signe en HMAC-SHA256, ecrit a la main.
 *
 * <p>POURQUOI A LA MAIN PLUTOT QU'AVEC UNE BIBLIOTHEQUE
 * <p>Parce qu'un JWT n'a rien de magique, et que le chapitre 4 doit
 * pouvoir en OUVRIR la charge utile devant vous. Trois parties separees par
 * des points, chacune en Base64URL : un en-tete, une charge utile, une
 * signature. Les deux premieres ne sont pas chiffrees — elles sont
 * ENCODEES. Quiconque tient le jeton les lit.
 *
 * <p>⚠️ LA CONSEQUENCE, ET C'EST LA SEULE CHOSE A RETENIR : on ne met
 * JAMAIS dans un JWT ce qu'on ne mettrait pas sur une carte postale. Un
 * identifiant, des roles, une expiration — oui. Une adresse, un salaire, un
 * numero de securite sociale — jamais.
 *
 * <p>⚠️ Et la verification compare les signatures en TEMPS CONSTANT. Un
 * {@code equals} ordinaire s'arrete au premier octet different : le temps
 * de reponse dit alors combien d'octets sont justes, et une signature se
 * devine octet par octet. {@code MessageDigest.isEqual} ne s'arrete pas.
 */
public final class Jeton {

    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Base64.Encoder ENCODEUR =
            Base64.getUrlEncoder().withoutPadding();
    private static final Base64.Decoder DECODEUR = Base64.getUrlDecoder();

    /** Ce qu'une verification rend : un verdict, et pourquoi. */
    public record Verdict(boolean valide, String motif, String sujet,
                          List<String> roles, Instant expiration) {

        public static Verdict refuse(String motif) {
            return new Verdict(false, motif, null, List.of(), null);
        }
    }

    private final byte[] cle;

    public Jeton(String cle) {
        this.cle = cle.getBytes(StandardCharsets.UTF_8);
    }

    /** Fabrique un jeton signe. */
    public String signer(String sujet, List<String> roles, String usage,
                         long dureeEnSecondes, Instant maintenant) {
        Map<String, Object> entete = new LinkedHashMap<>();
        entete.put("alg", "HS256");
        entete.put("typ", "JWT");

        Map<String, Object> charge = new LinkedHashMap<>();
        charge.put("sub", sujet);
        charge.put("roles", roles);
        charge.put("usage", usage);
        charge.put("iat", maintenant.getEpochSecond());
        charge.put("exp", maintenant.getEpochSecond() + dureeEnSecondes);

        String corps = encoder(enJson(entete)) + "." + encoder(enJson(charge));
        return corps + "." + ENCODEUR.encodeToString(signature(corps));
    }

    /** Verifie la signature, puis l'expiration, puis l'usage. */
    public Verdict verifier(String jeton, String usageAttendu,
                            Instant maintenant) {
        if (jeton == null || jeton.isBlank()) {
            return Verdict.refuse("jeton absent");
        }
        String[] parties = jeton.split("\\.");
        if (parties.length != 3) {
            return Verdict.refuse("format invalide");
        }

        // >>> depart: verifier le jeton — la signature AVEC L'ALGORITHME DU SERVEUR (jamais celui annonce dans l'en-tete), en temps constant, puis l'expiration, puis l'usage attendu
        //     return new Verdict(true, "ok", "inconnu", List.of(), maintenant);
        // ⚠️ L'ALGORITHME EST IMPOSE PAR NOUS, JAMAIS LU DANS LE JETON.
        // Faire confiance au champ `alg` de l'en-tete est l'attaque
        // « alg: none » : un jeton qui se declare non signe, et une
        // bibliotheque complaisante qui l'accepte.
        String corps = parties[0] + "." + parties[1];
        byte[] attendue = signature(corps);
        byte[] presentee;
        try {
            presentee = DECODEUR.decode(parties[2]);
        } catch (IllegalArgumentException erreur) {
            return Verdict.refuse("signature illisible");
        }
        if (!MessageDigest.isEqual(attendue, presentee)) {
            return Verdict.refuse("signature invalide");
        }

        Map<String, Object> charge = lireLaCharge(parties[1]);
        if (charge == null) {
            return Verdict.refuse("charge utile illisible");
        }
        Object expiration = charge.get("exp");
        if (!(expiration instanceof Number secondes)) {
            return Verdict.refuse("expiration absente");
        }
        Instant expire = Instant.ofEpochSecond(secondes.longValue());
        if (!expire.isAfter(maintenant)) {
            return Verdict.refuse("jeton expire");
        }
        if (usageAttendu != null && !usageAttendu.equals(charge.get("usage"))) {
            // ⚠️ SANS CE CONTROLE, un refresh token serait accepte comme un
            // access token : il est signe par la meme cle, et il vit des
            // jours. Toute la logique des deux durees tomberait.
            return Verdict.refuse("mauvais usage de jeton");
        }

        @SuppressWarnings("unchecked")
        List<String> roles = charge.get("roles") instanceof List<?> liste
                ? liste.stream().map(String::valueOf).toList()
                : List.of();
        return new Verdict(true, "ok", String.valueOf(charge.get("sub")),
                           roles, expire);
        // <<<
    }

    /**
     * ⚠️ LA CHARGE UTILE, LUE SANS AUCUNE CLE. Cette methode existe pour le
     * chapitre 4, et elle n'a besoin de rien : c'est du Base64, pas du
     * chiffrement. N'importe qui peut en faire autant avec le jeton.
     */
    public static Map<String, Object> chargeUtileSansVerification(String jeton) {
        String[] parties = jeton.split("\\.");
        return parties.length < 2 ? Map.of() : lireLaCharge(parties[1]);
    }

    private static Map<String, Object> lireLaCharge(String partie) {
        try {
            @SuppressWarnings("unchecked")
            Map<String, Object> charge = JSON.readValue(
                    DECODEUR.decode(partie), Map.class);
            return charge;
        } catch (Exception erreur) {
            return null;
        }
    }

    private byte[] signature(String corps) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(cle, "HmacSHA256"));
            return mac.doFinal(corps.getBytes(StandardCharsets.UTF_8));
        } catch (java.security.GeneralSecurityException erreur) {
            throw new IllegalStateException("signature impossible", erreur);
        }
    }

    private static String encoder(byte[] octets) {
        return ENCODEUR.encodeToString(octets);
    }

    /**
     * ⚠️ Spring Boot 4 embarque JACKSON 3 (`tools.jackson`), pas Jackson 2
     * (`com.fasterxml.jackson.databind`). Le paquet a change, et les
     * exceptions ne sont plus verifiees : `writeValueAsBytes` ne declare
     * plus de `JsonProcessingException`. Un `import` recopie d'un tutoriel
     * de 2024 ne compile donc pas.
     */
    private static byte[] enJson(Map<String, Object> valeur) {
        return JSON.writeValueAsBytes(valeur);
    }
}
