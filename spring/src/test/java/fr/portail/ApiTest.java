package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.offre.OffreService;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.web.client.RestClient;

/** Chapitre 3 — DTO, validation, ProblemDetail. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ApiTest {

    @LocalServerPort
    int port;

    @Autowired
    OffreService service;

    private RestClient client;

    @BeforeEach
    void ouvrir() {
        client = RestClient.builder().baseUrl("http://localhost:" + port).build();
        service.remettreAZeroLesEntrees();
    }

    @Nested
    @DisplayName("le DTO est le contrat public")
    class Contrat {

        @Test
        @DisplayName("la liste publiee ne contient ni salaire reel ni note interne")
        void leDtoNeFuitPas() {
            var corps = obtenir("/api/public/offres").corps();
            assertThat(corps).doesNotContain("salaireReel");
            assertThat(corps).doesNotContain("noteInterne");
            assertThat(corps).doesNotContain("contactEmail");
            assertThat(corps).contains("titre", "salaireMin", "entreprise");
        }

        @Test
        @DisplayName("l'entite publiee, elle, laisse tout sortir")
        void lEntiteFuit() {
            var corps = obtenir("/api/public/offres/entites-brutes").corps();
            assertThat(corps)
                    .as("PIECE A CONVICTION : cette route rend l'entite JPA. "
                        + "Si elle cessait de fuir, la demonstration du "
                        + "chapitre 3 serait morte sans qu'on le sache")
                    .contains("salaireReel")
                    .contains("noteInterne")
                    .contains("contactEmail");
        }

        @Test
        @DisplayName("les deux routes decrivent pourtant les memes offres")
        void memeNombreDOffres() {
            // ⚠️ Pas de nombre absolu : d'autres tests de cette classe creent
            // des offres, et JUnit ne promet aucun ordre. Ce qui compte est
            // que les deux routes voient la MEME chose — c'est le propos.
            long parDto = compter(obtenir("/api/public/offres").corps(), "\"titre\"");
            long parEntite = compter(
                    obtenir("/api/public/offres/entites-brutes").corps(), "\"titre\"");
            assertThat(parDto).isEqualTo(parEntite).isGreaterThanOrEqualTo(10);
        }
    }

    @Nested
    @DisplayName("la validation a la frontiere")
    class Validation {

        @Test
        @DisplayName("un corps invalide rend 400")
        void quatreCentsSurUnCorpsInvalide() {
            var reponse = poster("""
                    {"titre": "", "salaireMin": -5,
                     "contactEmail": "pas-un-courriel", "entreprise": "Nordeau"}
                    """);
            assertThat(reponse.code()).isEqualTo(HttpStatus.BAD_REQUEST);
        }

        @Test
        @DisplayName("et le service n'a pas ete appele")
        void leServiceNEstPasAtteint() {
            poster("""
                    {"titre": "", "salaireMin": -5,
                     "contactEmail": "pas-un-courriel", "entreprise": "Nordeau"}
                    """);
            assertThat(service.entrees())
                    .as("la validation est AVANT la methode, pas dedans")
                    .isZero();
        }

        @Test
        @DisplayName("la reponse est un ProblemDetail, au type de la RFC 9457")
        void leProblemDetail() {
            var reponse = poster("""
                    {"titre": "", "salaireMin": -5,
                     "contactEmail": "x", "entreprise": "Nordeau"}
                    """);
            assertThat(reponse.typeDeContenu())
                    .contains("application/problem+json");
            assertThat(reponse.corps())
                    .contains("\"status\":400")
                    .contains("\"title\"")
                    .contains("\"type\"");
        }

        @Test
        @DisplayName("chaque contrainte a son message")
        void lesMessagesDeContrainte() {
            var reponse = poster("""
                    {"titre": "", "salaireMin": -5,
                     "contactEmail": "x", "entreprise": "Nordeau"}
                    """);
            assertThat(reponse.corps())
                    .contains("le titre est obligatoire")
                    .contains("le salaire minimum est un nombre positif")
                    .contains("courriel");
        }

        @Test
        @DisplayName("un corps valide rend 201 et l'adresse de la ressource")
        void deuxCentUn() {
            var reponse = poster("""
                    {"titre": "Poste de test", "salaireMin": 41000,
                     "contactEmail": "rh@nordeau.test", "entreprise": "Nordeau"}
                    """);
            assertThat(reponse.code()).isEqualTo(HttpStatus.CREATED);
            assertThat(reponse.adresse()).contains("/api/public/offres/");
            assertThat(service.entrees()).isEqualTo(1);
        }

        @Test
        @DisplayName("les champs hors contrat sont ignores")
        void lesChampsEnTrop() {
            var reponse = poster("""
                    {"titre": "Poste hors contrat", "salaireMin": 42000,
                     "contactEmail": "rh@nordeau.test", "entreprise": "Nordeau",
                     "id": 9999, "salaireReel": 1}
                    """);
            assertThat(reponse.code()).isEqualTo(HttpStatus.CREATED);
            assertThat(reponse.corps()).doesNotContain("9999");
            assertThat(reponse.corps()).doesNotContain("salaireReel");
        }
    }

    @Nested
    @DisplayName("une seule forme d'erreur")
    class FormeDErreur {

        @Test
        @DisplayName("une erreur metier rend un ProblemDetail, pas un 500")
        void lErreurMetier() {
            var reponse = poster("""
                    {"titre": "Poste chez un fantome", "salaireMin": 40000,
                     "contactEmail": "rh@nulle-part.test",
                     "entreprise": "Entreprise Fantome"}
                    """);
            assertThat(reponse.code().value()).isEqualTo(422);
            assertThat(reponse.typeDeContenu()).contains("application/problem+json");
            assertThat(reponse.corps())
                    .contains("Entreprise inconnue")
                    .contains("entreprise-inconnue")
                    .contains("Entreprise Fantome");
        }

        @Test
        @DisplayName("le 422 s'appelle desormais UNPROCESSABLE_CONTENT")
        void leNomDuCode422() {
            // La RFC 9110 a renomme « Unprocessable Entity » en
            // « Unprocessable Content », et Spring Framework 7 a suivi.
            // `HttpStatus.valueOf(422)` rend la nouvelle constante ; l'ancien
            // nom existe encore, deprecie, et ce n'est PAS la meme valeur
            // d'enumeration. Comparer les deux echoue sur un message aussi
            // deroutant que « expected: 422 ... but was: 422 ... ».
            assertThat(HttpStatus.valueOf(422))
                    .isEqualTo(HttpStatus.UNPROCESSABLE_CONTENT);
            assertThat(HttpStatus.UNPROCESSABLE_CONTENT.value()).isEqualTo(422);
        }

        @Test
        @DisplayName("la trace de nos classes ne sort jamais")
        void pasDeTrace() {
            var reponse = poster("""
                    {"titre": "Poste chez un fantome", "salaireMin": 40000,
                     "contactEmail": "rh@nulle-part.test",
                     "entreprise": "Entreprise Fantome"}
                    """);
            assertThat(reponse.corps()).doesNotContain("fr.portail");
            assertThat(reponse.corps()).doesNotContain("Exception");
        }

        @Test
        @DisplayName("les deux erreurs ont les memes champs")
        void memeForme() {
            var validation = poster("""
                    {"titre": "", "salaireMin": 1,
                     "contactEmail": "rh@nordeau.test", "entreprise": "Nordeau"}
                    """);
            var metier = poster("""
                    {"titre": "Poste", "salaireMin": 1,
                     "contactEmail": "rh@nordeau.test", "entreprise": "Fantome"}
                    """);
            for (var champ : java.util.List.of("\"type\"", "\"title\"",
                    "\"status\"", "\"detail\"", "\"instance\"")) {
                assertThat(validation.corps()).contains(champ);
                assertThat(metier.corps()).contains(champ);
            }
        }
    }

    // ── la plomberie du test ─────────────────────────────────────────────

    private record Reponse(HttpStatus code, String corps, String typeDeContenu,
                           String adresse) {
    }

    private Reponse obtenir(String chemin) {
        return client.get().uri(chemin).exchange((requete, reponse) ->
                lire(reponse));
    }

    private Reponse poster(String json) {
        return client.post().uri("/api/public/offres")
                .contentType(MediaType.APPLICATION_JSON)
                .body(json)
                .exchange((requete, reponse) -> lire(reponse));
    }

    private static Reponse lire(
            org.springframework.http.client.ClientHttpResponse reponse)
            throws java.io.IOException {
        String corps = new String(reponse.getBody().readAllBytes(),
                java.nio.charset.StandardCharsets.UTF_8);
        var type = reponse.getHeaders().getContentType();
        var adresse = reponse.getHeaders().getFirst("Location");
        return new Reponse(HttpStatus.valueOf(reponse.getStatusCode().value()),
                corps, type == null ? "" : type.toString(),
                adresse == null ? "" : adresse);
    }

    private static long compter(String texte, String motif) {
        return texte == null ? 0
                : texte.split(java.util.regex.Pattern.quote(motif), -1).length - 1;
    }
}
