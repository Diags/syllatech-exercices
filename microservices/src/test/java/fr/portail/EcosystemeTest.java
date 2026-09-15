package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.commun.Banc;
import fr.portail.passerelle.Passerelle;
import fr.portail.services.OffresService;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

/**
 * L'écosystème complet, démarré et interrogé en vrai HTTP.
 *
 * <p>Ces tests sont les plus lents du projet : chacun démarre un serveur
 * Eureka, des instances du service et une passerelle. Ils sont aussi les seuls
 * à vérifier ce que l'apprenant verra — la découverte, l'équilibrage, le
 * disjoncteur.
 *
 * <p>⚠️ Ils ne tournent pas en parallèle : l'annuaire écoute sur un port fixe,
 * et deux bancs simultanés se disputeraient le 8761.
 */
class EcosystemeTest {

    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5)).build();

    @Test
    @Timeout(180)
    @DisplayName("deux instances s'enregistrent sous le meme nom")
    void lAnnuaireVoitLesDeux() {
        try (var banc = Banc.avecInstances(2)) {
            String annuaire = banc.urlEureka() + "/eureka/apps";
            boolean vues = Banc.attendre(
                    () -> compter(annuaire, "<instance>") >= 2,
                    Duration.ofSeconds(60));

            assertThat(vues)
                    .as("sans instance-id unique, l'annuaire n'en verrait qu'une")
                    .isTrue();
            assertThat(Banc.get(annuaire).corps())
                    .contains("OFFRES-SERVICE");
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("une instance arretee finit par disparaitre de l'annuaire")
    void lInstanceMorteEstOubliee() {
        try (var banc = Banc.avecInstances(2)) {
            String annuaire = banc.urlEureka() + "/eureka/apps";
            Banc.attendre(() -> compter(annuaire, "<instance>") >= 2,
                    Duration.ofSeconds(60));

            banc.tuerLInstance(banc.portsDesInstances().getFirst());

            assertThat(Banc.attendre(
                    () -> compter(annuaire, "<instance>") <= 1,
                    Duration.ofSeconds(30)))
                    .as("avec les defauts d'Eureka, cela prendrait 90 secondes")
                    .isTrue();
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("la passerelle route, reecrit le chemin, et equilibre")
    void laPasserelleRouteEtEquilibre() {
        try (var banc = Banc.complet(2)) {
            String url = banc.urlPasserelle() + "/api/offres";
            assertThat(Banc.attendre(() -> Banc.get(url).code() == 200,
                    Duration.ofSeconds(60))).isTrue();

            OffresService.remettreAZero();
            for (int appel = 0; appel < 20; appel++) {
                assertThat(Banc.get(url).code()).isEqualTo(200);
            }

            assertThat(OffresService.total()).isEqualTo(20);
            assertThat(OffresService.servies().keySet())
                    .as("les deux instances doivent avoir servi")
                    .hasSize(2);
        }
    }

    /**
     * ⚠️ La découverte du chapitre 3, figée en test.
     *
     * <p>Un 500 n'est pas un échec pour le disjoncteur par défaut : c'est une
     * réponse. Il faut {@code setStatusCodes(...)} pour qu'il compte.
     */
    @Test
    @Timeout(180)
    @DisplayName("un 500 n'ouvre le circuit que si la route le declare")
    void le500NOuvrePasLeCircuitParDefaut() {
        try (var banc = Banc.complet(1)) {
            String souple = banc.urlPasserelle() + "/api/offres";
            String stricte = banc.urlPasserelle() + "/api/strict/offres";
            assertThat(Banc.attendre(() -> Banc.get(souple).code() == 200,
                    Duration.ofSeconds(60))).isTrue();
            Passerelle.remettreAZero();
            for (var port : banc.portsDesInstances()) {
                Banc.post("http://localhost:" + port + "/panne?active=true");
            }

            for (int appel = 0; appel < 8; appel++) {
                assertThat(Banc.get(souple).code())
                        .as("la route souple relaie le 500 tel quel")
                        .isEqualTo(500);
            }
            assertThat(Passerelle.replis())
                    .as("aucun repli : le circuit ne s'est jamais ouvert")
                    .isZero();

            for (int appel = 0; appel < 8; appel++) {
                assertThat(Banc.get(stricte).code())
                        .as("la route stricte bascule sur le repli")
                        .isEqualTo(200);
            }
            assertThat(Passerelle.replis()).isEqualTo(8);
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("la passerelle refuse ce qui n'a pas de jeton")
    void laPasserelleRefuseSansJeton() {
        try (var banc = Banc.complet(1)) {
            String protegee = banc.urlPasserelle() + "/api/prive/entetes";
            assertThat(Banc.attendre(
                    () -> avec(protegee, "Bearer bon").code() == 200,
                    Duration.ofSeconds(60))).isTrue();

            assertThat(avec(protegee, null).code()).isEqualTo(401);
            assertThat(avec(protegee, "Basic abc").code()).isEqualTo(401);
            assertThat(avec(protegee, "Bearer bon").code()).isEqualTo(200);
        }
    }

    /**
     * ⚠️ Le point que le schéma d'architecture ne montre jamais.
     */
    @Test
    @Timeout(180)
    @DisplayName("le service repond quand meme si on contourne la passerelle")
    void leServiceRepondEnDirect() {
        try (var banc = Banc.complet(1)) {
            String protegee = banc.urlPasserelle() + "/api/prive/entetes";
            Banc.attendre(() -> avec(protegee, "Bearer bon").code() == 200,
                    Duration.ofSeconds(60));

            var directe = Banc.get("http://localhost:"
                    + banc.portsDesInstances().getFirst() + "/entetes");

            assertThat(directe.code())
                    .as("la passerelle n'est pas une frontiere de securite")
                    .isEqualTo(200);
            assertThat(directe.corps()).contains("(absent)");
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("la passerelle pose un identifiant de correlation par requete")
    void laCorrelationEstPosee() {
        try (var banc = Banc.complet(1)) {
            String protegee = banc.urlPasserelle() + "/api/prive/entetes";
            Banc.attendre(() -> avec(protegee, "Bearer bon").code() == 200,
                    Duration.ofSeconds(60));

            String premiere = avec(protegee, "Bearer bon").corps();
            String seconde = avec(protegee, "Bearer bon").corps();

            assertThat(premiere).contains("X-Request-Id")
                    .doesNotContain("\"X-Request-Id\":\"(absent)\"");
            assertThat(premiere)
                    .as("un identifiant different a chaque requete")
                    .isNotEqualTo(seconde);
        }
    }

    private static int compter(String url, String motif) {
        var reponse = Banc.get(url);
        if (reponse.code() != 200) {
            return 0;
        }
        int compte = 0;
        int position = 0;
        while ((position = reponse.corps().indexOf(motif, position)) >= 0) {
            compte++;
            position += motif.length();
        }
        return compte;
    }

    private static Banc.Reponse avec(String url, String autorisation) {
        var construction = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10)).GET();
        if (autorisation != null) {
            construction.header("Authorization", autorisation);
        }
        try {
            var reponse = CLIENT.send(construction.build(),
                    HttpResponse.BodyHandlers.ofString());
            return new Banc.Reponse(reponse.statusCode(), reponse.body());
        } catch (java.io.IOException | InterruptedException panne) {
            if (panne instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            return new Banc.Reponse(0, panne.getClass().getSimpleName());
        }
    }
}
