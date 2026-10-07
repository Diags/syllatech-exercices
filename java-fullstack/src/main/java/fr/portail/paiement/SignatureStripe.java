package fr.portail.paiement;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * La verification d'un webhook Stripe — la VRAIE, en HMAC-SHA256.
 *
 * <p>Ce fichier n'imite rien : le schema de signature de Stripe est un
 * en-tete {@code Stripe-Signature} de la forme {@code t=…,v1=…}, et la
 * signature est le HMAC-SHA256 de la chaine {@code t + "." + corps}, avec
 * le secret du point de terminaison. Tout est calculable hors ligne, et
 * c'est ce que ce chapitre mesure.
 *
 * <p>⚠️ POURQUOI C'EST LA SEULE SOURCE DE VERITE. Le retour du navigateur
 * apres un paiement — {@code /succes?session_id=…} — est une URL que
 * l'utilisateur peut taper lui-meme. Marquer une commande payee sur ce
 * retour, c'est offrir la boutique. Le webhook, lui, vient de Stripe et
 * porte une signature qu'on ne peut pas fabriquer sans le secret.
 */
public final class SignatureStripe {

    /** Le verdict, et sa raison. */
    public record Verdict(boolean valide, String motif) {

        public static Verdict refuse(String motif) {
            return new Verdict(false, motif);
        }

        public static final Verdict OK = new Verdict(true, "signature valide");
    }

    /**
     * ⚠️ LA TOLERANCE DE TEMPS N'EST PAS DECORATIVE. Sans elle, un webhook
     * capte une fois peut etre REJOUE indefiniment : sa signature reste
     * valide pour toujours. Cinq minutes est la valeur recommandee par
     * Stripe.
     */
    public static final Duration TOLERANCE = Duration.ofMinutes(5);

    private final byte[] secret;

    public SignatureStripe(String secret) {
        this.secret = secret.getBytes(StandardCharsets.UTF_8);
    }

    /** Fabrique l'en-tete, comme Stripe le ferait. */
    public String enTete(String corps, Instant horodatage) {
        long t = horodatage.getEpochSecond();
        return "t=" + t + ",v1=" + HexFormat.of().formatHex(hmac(t + "." + corps));
    }

    /** Verifie l'en-tete recu. Trois controles, et ils comptent tous. */
    public Verdict verifier(String corps, String enTete, Instant maintenant) {
        if (enTete == null || enTete.isBlank()) {
            return Verdict.refuse("en-tete absent");
        }
        Long horodatage = null;
        String presentee = null;
        for (String morceau : enTete.split(",")) {
            String[] paire = morceau.trim().split("=", 2);
            if (paire.length != 2) {
                continue;
            }
            if (paire[0].equals("t")) {
                try {
                    horodatage = Long.parseLong(paire[1]);
                } catch (NumberFormatException erreur) {
                    return Verdict.refuse("horodatage illisible");
                }
            } else if (paire[0].equals("v1")) {
                presentee = paire[1];
            }
        }
        if (horodatage == null || presentee == null) {
            return Verdict.refuse("en-tete incomplet");
        }

        // >>> depart: les TROIS controles — l'horodatage dans la fenetre (anti-rejeu), la signature sur `t + "." + corps`, et une comparaison en TEMPS CONSTANT
        //     return Verdict.OK;
        // 1. L'horodatage entre-t-il dans la fenetre ? (anti-rejeu)
        Duration ecart = Duration.between(Instant.ofEpochSecond(horodatage),
                                          maintenant).abs();
        if (ecart.compareTo(TOLERANCE) > 0) {
            return Verdict.refuse("horodatage hors tolerance ("
                                  + ecart.toMinutes() + " min)");
        }

        // 2. La signature couvre-t-elle l'horodatage ET le corps ?
        //    ⚠️ C'est ce qui empeche de recopier une signature valide sur
        //    un autre corps : les deux sont dans le meme HMAC.
        byte[] attendue = hmac(horodatage + "." + corps);
        byte[] recue;
        try {
            recue = HexFormat.of().parseHex(presentee);
        } catch (IllegalArgumentException erreur) {
            return Verdict.refuse("signature illisible");
        }

        // 3. La comparaison est en TEMPS CONSTANT.
        //    ⚠️ `String.equals` s'arrete au premier caractere different : le
        //    temps de reponse dit alors combien de caracteres sont justes, et
        //    la signature se devine caractere par caractere. Ce n'est pas
        //    theorique — c'est la raison d'etre de `MessageDigest.isEqual`.
        if (!MessageDigest.isEqual(attendue, recue)) {
            return Verdict.refuse("signature invalide");
        }
        return Verdict.OK;
        // <<<
    }

    private byte[] hmac(String charge) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return mac.doFinal(charge.getBytes(StandardCharsets.UTF_8));
        } catch (java.security.GeneralSecurityException erreur) {
            throw new IllegalStateException("HMAC impossible", erreur);
        }
    }
}
