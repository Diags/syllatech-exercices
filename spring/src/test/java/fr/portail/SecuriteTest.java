package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.securite.AdminController;
import fr.portail.securite.RouteOubliee;
import java.util.Base64;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.test.web.server.LocalServerPort;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.FilterChainProxy;
import org.springframework.web.client.RestClient;

/** Chapitre 5 — la chaîne de filtres, le refus par défaut, BCrypt. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class SecuriteTest {

    @LocalServerPort
    int port;

    @Autowired
    FilterChainProxy proxy;

    @Autowired
    PasswordEncoder encodeur;

    @BeforeEach
    void repartirDeZero() {
        AdminController.remettreAZero();
        RouteOubliee.remettreAZero();
    }

    @Nested
    @DisplayName("la chaine de filtres")
    class Chaine {

        @Test
        @DisplayName("elle existe, et elle a plus de dix filtres")
        void elleExiste() {
            assertThat(proxy.getFilterChains()).isNotEmpty();
            assertThat(filtres()).hasSizeGreaterThan(10);
        }

        @Test
        @DisplayName("l'authentification vient AVANT l'autorisation")
        void lOrdre() {
            var noms = filtres();
            int authentification = noms.indexOf("BasicAuthenticationFilter");
            int autorisation = noms.indexOf("AuthorizationFilter");
            assertThat(authentification)
                    .as("les filtres presents : " + noms).isNotNegative();
            assertThat(autorisation).isGreaterThan(authentification);
        }

        @Test
        @DisplayName("l'autorisation est le dernier filtre")
        void lAutorisationEstLaDerniere() {
            assertThat(filtres().getLast()).isEqualTo("AuthorizationFilter");
        }

        @Test
        @DisplayName("un contexte de securite est pose avant tout le reste")
        void leContexteEstPoseTot() {
            var noms = filtres();
            assertThat(noms.indexOf("SecurityContextHolderFilter"))
                    .isLessThan(noms.indexOf("BasicAuthenticationFilter"));
        }

        private List<String> filtres() {
            return proxy.getFilterChains().getFirst().getFilters().stream()
                    .map(f -> f.getClass().getSimpleName()).toList();
        }
    }

    @Nested
    @DisplayName("le refus par defaut")
    class RefusParDefaut {

        @Test
        @DisplayName("les routes publiques repondent 200 a l'anonyme")
        void lesRoutesPubliques() {
            assertThat(code(anonyme(), "/api/public/offres")).isEqualTo(200);
            assertThat(code(anonyme(), "/actuator/health")).isEqualTo(200);
        }

        @Test
        @DisplayName("une route JAMAIS citee dans la configuration est fermee")
        void laRouteOubliee() {
            assertThat(code(anonyme(), "/rapports/salaires"))
                    .as("`anyRequest().authenticated()` protege ce qu'on a "
                        + "oublie de lister")
                    .isEqualTo(401);
        }

        @Test
        @DisplayName("...et elle s'ouvre a qui est authentifie")
        void laRouteOublieePourUnConnecte() {
            assertThat(code(comme("karim", "motdepasse"), "/rapports/salaires"))
                    .isEqualTo(200);
        }

        @Test
        @DisplayName("une route reservee refuse un role insuffisant")
        void leRoleInsuffisant() {
            assertThat(code(anonyme(), "/api/admin/tableau-de-bord")).isEqualTo(401);
            assertThat(code(comme("karim", "motdepasse"),
                    "/api/admin/tableau-de-bord")).isEqualTo(403);
            assertThat(code(comme("awa", "motdepasse"),
                    "/api/admin/tableau-de-bord")).isEqualTo(200);
        }

        @Test
        @DisplayName("une panne sur une route OUVERTE ressort en 401")
        void laPanneDeguisee() {
            assertThat(code(anonyme(), "/api/public/panne"))
                    .as("PIECE A CONVICTION : la route est permitAll et leve "
                        + "une exception. Spring MVC fait une seconde passe "
                        + "vers /error, qui retraverse la chaine de filtres — "
                        + "et /error n'est cite nulle part dans la config")
                    .isEqualTo(401);
        }

        @Test
        @DisplayName("la meme panne, authentifie, ressort bien en 500")
        void laPanneVueParUnConnecte() {
            assertThat(code(comme("karim", "motdepasse"), "/api/public/panne"))
                    .isEqualTo(500);
        }

        @Test
        @DisplayName("`/actuator/health` ouvert ne rend pas `/actuator/health/x` ouvert")
        void leCheminExact() {
            assertThat(code(anonyme(), "/actuator/health")).isEqualTo(200);
            assertThat(code(anonyme(), "/actuator/health/liveness"))
                    .as("requestMatchers(\"/actuator/health\") designe ce "
                        + "chemin exactement ; il faudrait `/actuator/health/**`")
                    .isEqualTo(401);
        }

        @Test
        @DisplayName("un mauvais mot de passe rend 401, pas 403")
        void leMauvaisMotDePasse() {
            assertThat(code(comme("awa", "pas-le-bon"),
                    "/api/admin/tableau-de-bord")).isEqualTo(401);
        }
    }

    @Nested
    @DisplayName("un refus n'atteint pas le controleur")
    class AvantLeControleur {

        @Test
        @DisplayName("vingt requetes refusees, zero entree")
        void zeroEntree() {
            for (int i = 0; i < 20; i++) {
                code(anonyme(), "/api/admin/tableau-de-bord");
                code(comme("karim", "motdepasse"), "/api/admin/tableau-de-bord");
                code(anonyme(), "/rapports/salaires");
            }
            assertThat(AdminController.entrees()).isZero();
            assertThat(RouteOubliee.entrees()).isZero();
        }

        @Test
        @DisplayName("une requete autorisee, elle, entre bien")
        void uneEntree() {
            code(comme("awa", "motdepasse"), "/api/admin/tableau-de-bord");
            assertThat(AdminController.entrees()).isEqualTo(1);
        }
    }

    @Nested
    @DisplayName("BCrypt")
    class Bcrypt {

        @Test
        @DisplayName("le meme mot de passe donne deux empreintes differentes")
        void leSel() {
            assertThat(encodeur.encode("motdepasse"))
                    .isNotEqualTo(encodeur.encode("motdepasse"));
        }

        @Test
        @DisplayName("les deux valident pourtant le mot de passe")
        void lesDeuxValident() {
            for (int i = 0; i < 3; i++) {
                assertThat(encodeur.matches("motdepasse",
                        encodeur.encode("motdepasse"))).isTrue();
            }
        }

        @Test
        @DisplayName("un mot de passe voisin est refuse")
        void leMauvais() {
            String empreinte = encodeur.encode("motdepasse");
            assertThat(encodeur.matches("motdepass", empreinte)).isFalse();
            assertThat(encodeur.matches("Motdepasse", empreinte)).isFalse();
            assertThat(encodeur.matches("", empreinte)).isFalse();
        }

        @Test
        @DisplayName("l'empreinte porte son algorithme et son cout")
        void lEnTete() {
            assertThat(encodeur.encode("motdepasse")).startsWith("$2a$10$");
        }

        @Test
        @DisplayName("une verification coute du temps, et c'est la protection")
        void leCout() {
            String empreinte = encodeur.encode("motdepasse");
            long debut = System.nanoTime();
            for (int i = 0; i < 5; i++) {
                encodeur.matches("motdepasse", empreinte);
            }
            long parEssai = (System.nanoTime() - debut) / 5 / 1_000_000;
            assertThat(parEssai)
                    .as("au cout 10, une verification prend des dizaines de "
                        + "millisecondes : c'est ce qui borne un attaquant")
                    .isGreaterThan(5);
        }
    }

    // ── la plomberie du test ─────────────────────────────────────────────

    private RestClient anonyme() {
        return RestClient.builder().baseUrl("http://localhost:" + port).build();
    }

    private RestClient comme(String utilisateur, String motDePasse) {
        String jeton = Base64.getEncoder().encodeToString(
                (utilisateur + ":" + motDePasse)
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8));
        return RestClient.builder().baseUrl("http://localhost:" + port)
                .defaultHeader("Authorization", "Basic " + jeton).build();
    }

    private static int code(RestClient client, String chemin) {
        return client.get().uri(chemin).exchange((requete, reponse) -> {
            reponse.getBody().readAllBytes();
            return reponse.getStatusCode().value();
        });
    }
}
