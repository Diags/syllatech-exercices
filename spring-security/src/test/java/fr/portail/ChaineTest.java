package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.jeton.ServiceDeJetons;
import fr.portail.securite.SecurityConfig;
import fr.portail.web.Controleurs;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.util.Base64;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.FilterChainProxy;

/** Chapitres 1, 3 et 6 — la chaîne, CORS, et la sécurité au niveau méthode. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class ChaineTest {

    @LocalServerPort
    int port;

    @Autowired
    FilterChainProxy proxy;

    @Autowired
    ServiceDeJetons jetons;

    private final HttpClient client = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NEVER).build();

    @BeforeEach
    void repartirDeZero() {
        Controleurs.remettreAZero();
        SecurityContextHolder.clearContext();
    }

    @Nested
    @DisplayName("la chaine de filtres")
    class Chaine {

        @Test
        @DisplayName("l'application a deux chaines")
        void deuxChaines() {
            assertThat(proxy.getFilterChains()).hasSize(2);
        }

        @Test
        @DisplayName("l'authentification vient avant l'autorisation")
        void lOrdre() {
            var noms = filtresDeLApi();
            assertThat(noms.indexOf("BearerTokenAuthenticationFilter"))
                    .isNotNegative()
                    .isLessThan(noms.indexOf("AuthorizationFilter"));
        }

        @Test
        @DisplayName("l'autorisation est le dernier filtre")
        void leDernier() {
            assertThat(filtresDeLApi().getLast()).isEqualTo("AuthorizationFilter");
        }

        @Test
        @DisplayName("le contexte est pose avant qu'on lise le jeton")
        void leContexteDAbord() {
            var noms = filtresDeLApi();
            assertThat(noms.indexOf("SecurityContextHolderFilter"))
                    .isLessThan(noms.indexOf("BearerTokenAuthenticationFilter"));
        }

        private List<String> filtresDeLApi() {
            return proxy.getFilterChains().getLast().getFilters().stream()
                    .map(f -> f.getClass().getSimpleName()).toList();
        }
    }

    @Nested
    @DisplayName("sans etat")
    class SansEtat {

        @Test
        @DisplayName("l'API ne pose aucun cookie")
        void aucunCookie() {
            var reponse = obtenir("/api/moi", "Authorization",
                    "Bearer " + jetons.acces("awa", List.of("USER")));
            assertThat(reponse.headers().allValues("Set-Cookie")).isEmpty();
        }

        @Test
        @DisplayName("l'API ne cree aucune session")
        void aucuneSession() {
            var reponse = obtenir("/api/moi", "Authorization",
                    "Bearer " + jetons.acces("awa", List.of("USER")));
            assertThat(reponse.body()).contains("\"sessionHttp\":\"aucune\"");
        }

        @Test
        @DisplayName("la chaine de session, elle, en pose un")
        void laSessionEnPose() {
            var reponse = obtenir("/session/connexion",
                    "Authorization", basic("awa", "motdepasse"));
            assertThat(reponse.headers().allValues("Set-Cookie"))
                    .anyMatch(c -> c.startsWith("JSESSIONID="));
        }

        @Test
        @DisplayName("le contexte de securite est lie au thread")
        void leThreadLocal() throws Exception {
            SecurityContextHolder.getContext().setAuthentication(
                    new UsernamePasswordAuthenticationToken("test", "n/a",
                            AuthorityUtils.createAuthorityList("ROLE_TEST")));
            var vuAilleurs = new java.util.ArrayList<String>();
            var autre = new Thread(() -> vuAilleurs.add(String.valueOf(
                    SecurityContextHolder.getContext().getAuthentication())));
            autre.start();
            autre.join();
            assertThat(SecurityContextHolder.getContext().getAuthentication())
                    .isNotNull();
            assertThat(vuAilleurs).containsExactly("null");
        }
    }

    @Nested
    @DisplayName("un refus n'atteint pas le code")
    class AvantLeControleur {

        @Test
        @DisplayName("vingt requetes sans jeton, zero entree")
        void zeroEntree() {
            for (int i = 0; i < 20; i++) {
                obtenir("/api/moi");
                obtenir("/api/rh/candidatures");
            }
            assertThat(Controleurs.entrees()).isZero();
        }

        @Test
        @DisplayName("une requete autorisee, elle, entre")
        void uneEntree() {
            obtenir("/api/rh/candidatures", "Authorization",
                    "Bearer " + jetons.acces("awa", List.of("RH")));
            assertThat(Controleurs.entrees()).isEqualTo(1);
        }

        @Test
        @DisplayName("une panne sur une route ouverte ressort en 401 pour l'anonyme")
        void lErreurRetraverseLaChaine() {
            assertThat(obtenir("/api/public/panne").statusCode())
                    .as("la passe vers /error retraverse la chaine, et /error "
                        + "n'est liste nulle part")
                    .isEqualTo(401);
        }

        @Test
        @DisplayName("la meme panne, authentifiee, ressort en 500")
        void laMemePanneAuthentifiee() {
            assertThat(obtenir("/api/public/panne", "Authorization",
                    "Bearer " + jetons.acces("awa", List.of("USER"))).statusCode())
                    .isEqualTo(500);
        }
    }

    @Nested
    @DisplayName("CORS")
    class Cors {

        @Test
        @DisplayName("sans en-tete Origin, l'API repond tout")
        void sansOrigine() {
            var reponse = obtenir("/api/public/offres");
            assertThat(reponse.statusCode()).isEqualTo(200);
            assertThat(reponse.body())
                    .as("un script n'envoie pas d'Origin : CORS ne le gene en rien")
                    .contains("OFF-014");
        }

        @Test
        @DisplayName("depuis l'origine autorisee, l'en-tete est pose")
        void origineAutorisee() {
            var reponse = obtenir("/api/public/offres",
                    "Origin", SecurityConfig.ORIGINE_AUTORISEE);
            assertThat(reponse.statusCode()).isEqualTo(200);
            assertThat(reponse.headers().firstValue("Access-Control-Allow-Origin"))
                    .contains(SecurityConfig.ORIGINE_AUTORISEE);
        }

        @Test
        @DisplayName("depuis une autre origine, Spring refuse la requete")
        void origineRefusee() {
            var reponse = obtenir("/api/public/offres",
                    "Origin", "https://site-pirate.test");
            assertThat(reponse.statusCode())
                    .as("le CorsFilter de Spring va plus loin que la "
                        + "specification : il refuse au lieu de simplement "
                        + "omettre l'en-tete")
                    .isEqualTo(403);
            assertThat(reponse.body()).doesNotContain("OFF-014");
        }

        @Test
        @DisplayName("le preflight repond aux origines autorisees")
        void lePreflight() {
            var reponse = envoyer("OPTIONS", "/api/moi",
                    "Origin", SecurityConfig.ORIGINE_AUTORISEE,
                    "Access-Control-Request-Method", "GET");
            assertThat(reponse.statusCode()).isEqualTo(200);
            assertThat(reponse.headers().firstValue("Access-Control-Allow-Methods"))
                    .isPresent();
            assertThat(reponse.headers().firstValue("Access-Control-Max-Age"))
                    .contains("3600");
        }

        @Test
        @DisplayName("l'etoile avec des identifiants est refusee a la construction")
        void lEtoileEtLesIdentifiants() {
            var dangereuse = new org.springframework.web.cors.CorsConfiguration();
            dangereuse.setAllowedOrigins(List.of("*"));
            dangereuse.setAllowCredentials(true);
            org.assertj.core.api.Assertions
                    .assertThatThrownBy(dangereuse::validateAllowCredentials)
                    .isInstanceOf(IllegalArgumentException.class);
        }

        @Test
        @DisplayName("la politique du portail nomme une seule origine")
        void uneSeuleOrigine(@Autowired
                @org.springframework.beans.factory.annotation
                        .Qualifier("corsConfigurationSource")
                org.springframework.web.cors.CorsConfigurationSource source) {
            // ⚠️ Le qualificatif est necessaire : Spring MVC declare LUI AUSSI
            // un `CorsConfigurationSource` — le `mvcHandlerMappingIntrospector`,
            // qui lit les `@CrossOrigin`. C'est d'ailleurs pour cela que
            // `cors()` cherche un bean PAR SON NOM plutot que par son type.
            assertThat(source).isNotNull();
            assertThat(SecurityConfig.ORIGINE_AUTORISEE).doesNotContain("*");
        }
    }

    // ── la plomberie du test ─────────────────────────────────────────────

    private HttpResponse<String> obtenir(String chemin, String... entetes) {
        return envoyer("GET", chemin, entetes);
    }

    private HttpResponse<String> envoyer(String methode, String chemin,
                                         String... entetes) {
        try {
            var construction = HttpRequest.newBuilder()
                    .uri(URI.create("http://localhost:" + port + chemin));
            for (int i = 0; i + 1 < entetes.length; i += 2) {
                construction.header(entetes[i], entetes[i + 1]);
            }
            construction.method(methode, HttpRequest.BodyPublishers.noBody());
            return client.send(construction.build(),
                    HttpResponse.BodyHandlers.ofString());
        } catch (java.io.IOException | InterruptedException erreur) {
            if (erreur instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new IllegalStateException("requete impossible", erreur);
        }
    }

    private static String basic(String utilisateur, String motDePasse) {
        return "Basic " + Base64.getEncoder().encodeToString(
                (utilisateur + ":" + motDePasse)
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }
}
