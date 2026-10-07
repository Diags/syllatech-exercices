package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.securite.SecurityConfig;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.config.ConfigurableListableBeanFactory;
import org.springframework.boot.autoconfigure.condition.ConditionEvaluationReport;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.web.client.RestClient;

/** Chapitre 2 — l'auto-configuration, les profils, Actuator. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AutoConfigurationTest {

    @Autowired
    ConfigurableApplicationContext contexte;

    @Autowired
    Environment env;

    @org.springframework.boot.test.web.server.LocalServerPort
    int port;

    @Nested
    @DisplayName("le rapport de conditions")
    class Rapport {

        @Test
        @DisplayName("Spring Boot tient un rapport, et il n'est pas vide")
        void leRapportExiste() {
            assertThat(decisions()).isNotEmpty();
        }

        @Test
        @DisplayName("il contient des decisions retenues ET des ecartees")
        void lesDeuxVerdicts() {
            var decisions = decisions();
            long retenues = decisions.values().stream()
                    .filter(ConditionEvaluationReport.ConditionAndOutcomes::isFullMatch)
                    .count();
            assertThat(retenues).isPositive();
            assertThat(decisions.size() - retenues)
                    .as("des classes sont ecartees faute de trouver leur "
                        + "dependance : c'est le `if` a l'oeuvre")
                    .isPositive();
        }

        @Test
        @DisplayName("la source de donnees vient d'une decision, pas de notre code")
        void laSourceDeDonnees() {
            assertThat(decisions().keySet())
                    .anyMatch(source -> source.contains("DataSourceAutoConfiguration"));
            assertThat(contexte.getBeanNamesForType(javax.sql.DataSource.class))
                    .isNotEmpty();
        }

        @Test
        @DisplayName("le gestionnaire de transactions aussi")
        void leGestionnaireDeTransactions() {
            assertThat(contexte.getBean(PlatformTransactionManager.class))
                    .isNotNull();
        }

        private java.util.Map<String,
                ConditionEvaluationReport.ConditionAndOutcomes> decisions() {
            var fabrique = (ConfigurableListableBeanFactory) contexte.getBeanFactory();
            return ConditionEvaluationReport.get(fabrique)
                    .getConditionAndOutcomesBySource();
        }
    }

    @Nested
    @DisplayName("notre bean gagne toujours")
    class NotreBeanGagne {

        @Test
        @DisplayName("le PasswordEncoder est celui de SecurityConfig")
        void lEncodeur() {
            assertThat(contexte.getBean(PasswordEncoder.class))
                    .isInstanceOf(BCryptPasswordEncoder.class);
        }

        @Test
        @DisplayName("il n'y en a qu'un, et il vient de notre configuration")
        void unSeulEncodeur() {
            assertThat(contexte.getBeanNamesForType(PasswordEncoder.class))
                    .containsExactly("encodeurDeMotDePasse");
            assertThat(SecurityConfig.class.getDeclaredMethods())
                    .anyMatch(m -> m.getName().equals("encodeurDeMotDePasse"));
        }

        @Test
        @DisplayName("la chaine de filtres aussi est la notre")
        void laChaine() {
            assertThat(contexte.getBeanNamesForType(
                    org.springframework.security.web.SecurityFilterChain.class))
                    .containsExactly("chaine");
        }
    }

    @Nested
    @DisplayName("les starters ont bien apporte leurs bibliotheques")
    class Starters {

        @Test
        @DisplayName("chaque starter declare amene ce qu'on attend de lui")
        void lesBibliotheques() {
            for (var bibliotheque : List.of("spring-webmvc", "tomcat-embed-core",
                    "jackson-databind", "hibernate-core", "spring-data-jpa",
                    "spring-security-web", "hibernate-validator")) {
                assertThat(surLeClasspath(bibliotheque))
                        .as(bibliotheque + " devrait etre sur le classpath")
                        .isTrue();
            }
        }

        @Test
        @DisplayName("quatre lignes de pom en amenent bien plus que quatre")
        void leRapport() {
            long jars = java.util.Arrays.stream(
                            System.getProperty("java.class.path", "")
                                    .split(java.io.File.pathSeparator))
                    .filter(e -> e.endsWith(".jar")).count();
            assertThat(jars).isGreaterThan(40);
        }

        private boolean surLeClasspath(String artefact) {
            return java.util.Arrays.stream(
                            System.getProperty("java.class.path", "")
                                    .split(java.io.File.pathSeparator))
                    .anyMatch(e -> e.replace('\\', '/').contains("/" + artefact + "-"));
        }
    }

    @Nested
    @DisplayName("profils et configuration externe")
    class Profils {

        @Test
        @DisplayName("sans profil actif, c'est le profil PAR DEFAUT qui s'applique")
        void leProfilParDefaut() {
            // `spring.profiles.default: dev` dans application.yml. Aucun
            // profil n'est « actif » ici : les tests n'en posent pas. C'est
            // une distinction qui trompe — `getActiveProfiles()` rend un
            // tableau vide alors que le profil dev est bien celui qui joue.
            assertThat(env.getActiveProfiles()).isEmpty();
            assertThat(env.getDefaultProfiles()).contains("dev");
            assertThat(env.matchesProfiles("dev")).isTrue();
        }

        @Test
        @DisplayName("dev montre le detail de la sante")
        void devMontreLeDetail() {
            assertThat(env.getProperty("management.endpoint.health.show-details"))
                    .isEqualTo("always");
        }

        @Test
        @DisplayName("le fichier de configuration decrit bien deux profils")
        void deuxProfils() throws Exception {
            var yaml = new String(getClass().getResourceAsStream(
                    "/application.yml").readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
            assertThat(yaml).contains("on-profile: dev");
            assertThat(yaml).contains("on-profile: prod");
            assertThat(yaml)
                    .as("en prod, le schema est gere par des migrations")
                    .contains("ddl-auto: validate");
            assertThat(yaml)
                    .as("le secret vient de l'environnement, jamais du depot")
                    .contains("${DB_PASSWORD:");
        }

        @Test
        @DisplayName("aucun mot de passe en clair n'est ecrit dans le fichier")
        void pasDeSecretEnDur() throws Exception {
            var yaml = new String(getClass().getResourceAsStream(
                    "/application.yml").readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
            for (var ligne : yaml.lines().toList()) {
                if (ligne.strip().startsWith("password:")) {
                    assertThat(ligne)
                            .as("un mot de passe doit venir de l'environnement "
                                + "ou etre vide : " + ligne)
                            .containsAnyOf("${", "\"\"");
                }
            }
        }
    }

    @Nested
    @DisplayName("Actuator")
    class Actuator {

        @Test
        @DisplayName("health est ouvert")
        void health() {
            assertThat(code("/actuator/health")).isEqualTo(200);
        }

        @Test
        @DisplayName("beans et env ne sont pas exposes")
        void lesPointsSensibles() {
            assertThat(code("/actuator/beans")).isNotEqualTo(200);
            assertThat(code("/actuator/env")).isNotEqualTo(200);
            assertThat(code("/actuator/heapdump")).isNotEqualTo(200);
        }

        @Test
        @DisplayName("l'exposition est une liste explicite, pas un `*`")
        void lExpositionEstExplicite() {
            String expose = env.getProperty(
                    "management.endpoints.web.exposure.include", "");
            assertThat(expose).doesNotContain("*");
            assertThat(expose).contains("health");
        }

        private int code(String chemin) {
            return RestClient.builder().baseUrl("http://localhost:" + port)
                    .build().get().uri(chemin)
                    .exchange((requete, reponse) -> {
                        reponse.getBody().readAllBytes();
                        return reponse.getStatusCode().value();
                    });
        }
    }
}
