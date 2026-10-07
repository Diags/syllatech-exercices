package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.paiement.ServicePaiement;
import fr.portail.paiement.SignatureStripe;
import fr.portail.securite.Jeton;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Le JWT et la signature Stripe — les deux sont de VRAIS HMAC-SHA256.
 *
 * <p>⚠️ Plusieurs de ces tests AFFIRMENT ce qui passe. La charge utile d'un
 * JWT se lit sans cle, et un access token survit a la desactivation de son
 * compte : ce ne sont pas des defauts a corriger, ce sont les proprietes
 * qu'il faut connaitre pour choisir une duree de vie.
 */
class SecuriteTest {

    private static final String CLE = "une-cle-de-test-suffisamment-longue";
    private final Jeton jeton = new Jeton(CLE);
    private final Instant maintenant = Instant.parse("2026-01-15T10:00:00Z");

    private String signer(String usage, long duree) {
        return jeton.signer("awa", List.of("ROLE_USER", "ROLE_RH"), usage,
                            duree, maintenant);
    }

    // -- le JWT ------------------------------------------------------------

    @Test
    @DisplayName("un jeton valide est accepte, avec son sujet et ses roles")
    void leJetonValide() {
        Jeton.Verdict verdict =
                jeton.verifier(signer("access", 300), "access", maintenant);

        assertThat(verdict.valide()).isTrue();
        assertThat(verdict.sujet()).isEqualTo("awa");
        assertThat(verdict.roles()).containsExactly("ROLE_USER", "ROLE_RH");
        assertThat(verdict.expiration())
                .isEqualTo(maintenant.plusSeconds(300));
    }

    @Test
    @DisplayName("⚠️ LA MESURE : la charge utile se lit SANS AUCUNE CLE")
    void laChargeUtileEstLisible() {
        String presente = signer("access", 300);

        // Personne n'a la cle ici — c'est du Base64, pas du chiffrement.
        Map<String, Object> charge =
                Jeton.chargeUtileSansVerification(presente);

        assertThat(charge).containsEntry("sub", "awa");
        assertThat(charge).containsEntry("usage", "access");
        assertThat(charge.get("roles").toString()).contains("ROLE_RH");

        // La regle : on ne met jamais dans un JWT ce qu'on ne mettrait pas
        // sur une carte postale.
        assertThat(charge).doesNotContainKeys("motDePasse", "adresse", "salaire");
    }

    @Test
    @DisplayName("⚠️ un role change en Base64 invalide la signature")
    void leRoleTrafiqueEstRefuse() {
        String[] parties = signer("access", 300).split("\\.");
        String trafiquee = Base64.getUrlEncoder().withoutPadding()
                .encodeToString(new String(
                        Base64.getUrlDecoder().decode(parties[1]),
                        StandardCharsets.UTF_8)
                        .replace("ROLE_USER", "ROLE_ADMIN")
                        .getBytes(StandardCharsets.UTF_8));

        Jeton.Verdict verdict = jeton.verifier(
                parties[0] + "." + trafiquee + "." + parties[2],
                "access", maintenant);

        assertThat(verdict.valide()).isFalse();
        assertThat(verdict.motif()).isEqualTo("signature invalide");
    }

    @Test
    @DisplayName("⚠️ « alg: none » est refuse — l'algorithme vient du serveur")
    void algNoneEstRefuse() {
        String[] parties = signer("access", 300).split("\\.");
        String entete = Base64.getUrlEncoder().withoutPadding()
                .encodeToString("{\"alg\":\"none\",\"typ\":\"JWT\"}"
                        .getBytes(StandardCharsets.UTF_8));

        // Un jeton « alg: none » n'a que deux parties : il est refuse avant
        // meme qu'on calcule quoi que ce soit. Accepter deux parties est
        // exactement ce que faisaient les implantations vulnerables.
        assertThat(jeton.verifier(entete + "." + parties[1] + ".", "access",
                                  maintenant).valide())
                .isFalse();
    }

    @Test
    @DisplayName("un jeton signe avec une autre cle est refuse")
    void uneAutreCleEstRefusee() {
        String forge = new Jeton("la-cle-de-l-attaquant")
                .signer("awa", List.of("ROLE_ADMIN"), "access", 300, maintenant);

        assertThat(jeton.verifier(forge, "access", maintenant).motif())
                .isEqualTo("signature invalide");
    }

    @Test
    @DisplayName("⚠️ un REFRESH token n'est pas accepte comme access token")
    void leRefreshNEstPasUnAccess() {
        // Il est signe par la MEME cle : sans un champ `usage` verifie, il
        // passerait partout — et il vit des jours.
        String refresh = signer("refresh", 604_800);

        assertThat(jeton.verifier(refresh, "access", maintenant).motif())
                .isEqualTo("mauvais usage de jeton");
        assertThat(jeton.verifier(refresh, "refresh", maintenant).valide())
                .isTrue();
    }

    @Test
    @DisplayName("un jeton expire est refuse, a la seconde pres")
    void leJetonExpire() {
        String court = signer("access", 300);

        assertThat(jeton.verifier(court, "access",
                maintenant.plusSeconds(299)).valide()).isTrue();
        assertThat(jeton.verifier(court, "access",
                maintenant.plusSeconds(300)).motif())
                .isEqualTo("jeton expire");
    }

    @Test
    @DisplayName("un jeton mal forme est refuse sans exception")
    void lesJetonsMalFormes() {
        for (String mauvais : List.of("", "pas-un-jeton", "a.b", "a.b.c.d")) {
            Jeton.Verdict verdict =
                    jeton.verifier(mauvais, "access", maintenant);
            assertThat(verdict.valide()).as(mauvais).isFalse();
            assertThat(verdict.motif()).isNotBlank();
        }
        assertThat(jeton.verifier(null, "access", maintenant).motif())
                .isEqualTo("jeton absent");
    }

    // -- la signature Stripe ----------------------------------------------

    private static final String CORPS = """
            {"type":"checkout.session.completed","data":{"object":\
            {"id":"cs_test_abc","amount_total":4900,"payment_status":"paid"}}}""";

    @Test
    @DisplayName("un webhook signe par Stripe est accepte")
    void leWebhookValide() {
        SignatureStripe signature = new SignatureStripe("whsec_test");
        Instant t = Instant.now();

        assertThat(signature.verifier(CORPS, signature.enTete(CORPS, t), t)
                .valide()).isTrue();
    }

    @Test
    @DisplayName("⚠️ LA MESURE : le meme en-tete sur un montant modifie est refuse")
    void leCorpsTrafiqueEstRefuse() {
        SignatureStripe signature = new SignatureStripe("whsec_test");
        Instant t = Instant.now();
        String enTete = signature.enTete(CORPS, t);

        // La signature couvre l'horodatage ET le corps : recopier une
        // signature valide sur un autre corps ne marche pas.
        String trafique = CORPS.replace("\"amount_total\":4900",
                                        "\"amount_total\":1");
        assertThat(signature.verifier(trafique, enTete, t).motif())
                .isEqualTo("signature invalide");
    }

    @Test
    @DisplayName("⚠️ un webhook VALIDE rejoue 30 min plus tard est refuse")
    void leRejeuEstRefuse() {
        SignatureStripe signature = new SignatureStripe("whsec_test");
        Instant maintenant = Instant.now();
        Instant vieux = maintenant.minus(Duration.ofMinutes(30));

        // Sans tolerance de temps, un webhook capte une fois serait
        // rejouable indefiniment : sa signature reste valide pour toujours.
        SignatureStripe.Verdict verdict = signature.verifier(
                CORPS, signature.enTete(CORPS, vieux), maintenant);

        assertThat(verdict.valide()).isFalse();
        assertThat(verdict.motif()).contains("hors tolerance");
    }

    @Test
    @DisplayName("un webhook juste dans la fenetre passe")
    void laFenetreDeTolerance() {
        SignatureStripe signature = new SignatureStripe("whsec_test");
        Instant maintenant = Instant.now();
        Instant limite = maintenant.minus(SignatureStripe.TOLERANCE)
                .plusSeconds(1);

        assertThat(signature.verifier(CORPS, signature.enTete(CORPS, limite),
                                      maintenant).valide()).isTrue();
    }

    @Test
    @DisplayName("un en-tete absent, incomplet ou illisible est refuse")
    void lesEnTetesInvalides() {
        SignatureStripe signature = new SignatureStripe("whsec_test");
        Instant t = Instant.now();

        assertThat(signature.verifier(CORPS, null, t).motif())
                .isEqualTo("en-tete absent");
        assertThat(signature.verifier(CORPS, "v1=abcd", t).motif())
                .isEqualTo("en-tete incomplet");
        assertThat(signature.verifier(CORPS, "t=hier,v1=abcd", t).motif())
                .isEqualTo("horodatage illisible");
        assertThat(signature.verifier(CORPS,
                "t=" + t.getEpochSecond() + ",v1=zz", t).motif())
                .isEqualTo("signature illisible");
    }

    @Test
    @DisplayName("⚠️ LA MESURE : le retour du navigateur marque la commande PAYEE, sans paiement")
    void leRetourDuNavigateurNeProuveRien() {
        ServicePaiement paiement = new ServicePaiement("whsec_test");
        Map<String, String> session = paiement.creerUneSession("CMD-99", 129_000);

        assertThat(paiement.etat("CMD-99"))
                .isEqualTo(ServicePaiement.Etat.EN_ATTENTE);

        // ⚠️ PIECE A CONVICTION. L'URL de retour est tapable a la main :
        // marquer la commande payee ici suffit a se faire livrer sans payer.
        paiement.confirmerDepuisLeNavigateur(session.get("sessionId"));

        assertThat(paiement.etat("CMD-99"))
                .as("1 290 € pour une requete GET")
                .isEqualTo(ServicePaiement.Etat.PAYEE);
    }

    @Test
    @DisplayName("le webhook signe, lui, est la seule confirmation qui vaille")
    void leWebhookEstLaSourceDeVerite() {
        ServicePaiement paiement = new ServicePaiement("whsec_test");
        Map<String, String> session = paiement.creerUneSession("CMD-42", 4900);
        Instant t = Instant.now();
        String corps = CORPS.replace("cs_test_abc", session.get("sessionId"));

        // Un webhook non signe ne change rien.
        paiement.traiterLeWebhook(corps, "t=" + t.getEpochSecond() + ",v1=00", t);
        assertThat(paiement.etat("CMD-42"))
                .isEqualTo(ServicePaiement.Etat.EN_ATTENTE);

        // Le webhook signe, oui.
        paiement.traiterLeWebhook(corps, paiement.signature().enTete(corps, t), t);
        assertThat(paiement.etat("CMD-42"))
                .isEqualTo(ServicePaiement.Etat.PAYEE);
        assertThat(paiement.webhooksAcceptes()).isEqualTo(1);
        assertThat(paiement.webhooksRefuses()).isEqualTo(1);
    }
}
