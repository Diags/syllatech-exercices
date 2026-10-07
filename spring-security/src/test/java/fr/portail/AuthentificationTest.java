package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.comptes.AuthentificationNaive;
import fr.portail.comptes.ServiceDUtilisateurs;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;

/** Chapitre 2 — le trio, les messages, et la fuite par le temps. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class AuthentificationTest {

    @Autowired
    AuthenticationManager gestionnaire;

    @Autowired
    ServiceDUtilisateurs utilisateurs;

    @Autowired
    AuthentificationNaive naive;

    @Autowired
    PasswordEncoder encodeur;

    @Nested
    @DisplayName("le trio")
    class Trio {

        @ParameterizedTest(name = "{0} s'authentifie")
        @ValueSource(strings = {"awa", "karim", "lea"})
        void lesComptesDuPortail(String identifiant) {
            var authentification = gestionnaire.authenticate(
                    new UsernamePasswordAuthenticationToken(identifiant,
                            "motdepasse"));
            assertThat(authentification.isAuthenticated()).isTrue();
            assertThat(authentification.getName()).isEqualTo(identifiant);
        }

        @Test
        @DisplayName("le UserDetailsService rend les roles, prefixes par Spring")
        void lesRoles() {
            var details = utilisateurs.loadUserByUsername("lea");
            assertThat(details.getAuthorities().stream()
                    .map(Object::toString).toList())
                    .contains("ROLE_ADMIN", "ROLE_RH", "ROLE_USER");
        }

        @Test
        @DisplayName("un compte inconnu leve UsernameNotFoundException")
        void leCompteInconnu() {
            assertThatThrownBy(() -> utilisateurs.loadUserByUsername("fantome"))
                    .isInstanceOf(UsernameNotFoundException.class);
        }

        @Test
        @DisplayName("Spring la traduit en BadCredentialsException")
        void springLaTraduit() {
            assertThatThrownBy(() -> gestionnaire.authenticate(
                    new UsernamePasswordAuthenticationToken("fantome", "x")))
                    .as("le meme type d'exception que pour un mot de passe faux : "
                        + "c'est ce qui empeche d'enumerer les comptes")
                    .isInstanceOf(BadCredentialsException.class);
        }

        @Test
        @DisplayName("un mot de passe faux donne exactement la meme exception")
        void leMotDePasseFaux() {
            assertThatThrownBy(() -> gestionnaire.authenticate(
                    new UsernamePasswordAuthenticationToken("awa", "pas-le-bon")))
                    .isInstanceOf(BadCredentialsException.class);
        }

        @Test
        @DisplayName("et le meme message")
        void leMemeMessage() {
            String surUnInconnu = messageDe("fantome", "x");
            String surUnMauvais = messageDe("awa", "pas-le-bon");
            assertThat(surUnInconnu).isEqualTo(surUnMauvais);
        }

        private String messageDe(String identifiant, String motDePasse) {
            try {
                gestionnaire.authenticate(new UsernamePasswordAuthenticationToken(
                        identifiant, motDePasse));
                return "(accepte)";
            } catch (org.springframework.security.core.AuthenticationException refus) {
                return refus.getMessage();
            }
        }
    }

    @Nested
    @DisplayName("la fuite par le temps")
    class FuiteTemporelle {

        @Test
        @DisplayName("l'authentification ecrite a la main distingue les deux chemins")
        void laNaiveFuit() {
            long inconnu = mediane(() -> naive.verifier("fantome", "x"));
            long mauvais = mediane(() -> naive.verifier("awa", "pas-le-bon"));
            assertThat(mauvais)
                    .as("PIECE A CONVICTION : sur un compte inconnu elle part "
                        + "avant BCrypt, et l'ecart se chronometre")
                    .isGreaterThan(inconnu * 10);
        }

        @Test
        @DisplayName("celle de Spring ne les distingue pas")
        void springNeFuitPas() {
            long inconnu = mediane(() -> tenter("fantome", "x"));
            long mauvais = mediane(() -> tenter("awa", "pas-le-bon"));
            double rapport = (double) Math.max(inconnu, mauvais)
                    / Math.max(1, Math.min(inconnu, mauvais));
            assertThat(rapport)
                    .as("`mitigateAgainstTimingAttack` fait tourner BCrypt "
                        + "contre une empreinte factice — mesure : %d vs %d ns"
                                .formatted(inconnu, mauvais))
                    .isLessThan(2.0);
        }

        @Test
        @DisplayName("les deux refusent, dans tous les cas")
        void lesDeuxRefusent() {
            assertThat(naive.verifier("fantome", "x")).isFalse();
            assertThat(naive.verifier("awa", "pas-le-bon")).isFalse();
            assertThat(naive.verifier("awa", "motdepasse")).isTrue();
        }

        private long mediane(Runnable geste) {
            for (int i = 0; i < 3; i++) {
                geste.run();
            }
            var temps = new long[9];
            for (int i = 0; i < temps.length; i++) {
                long debut = System.nanoTime();
                geste.run();
                temps[i] = System.nanoTime() - debut;
            }
            java.util.Arrays.sort(temps);
            return temps[temps.length / 2];
        }

        private void tenter(String identifiant, String motDePasse) {
            try {
                gestionnaire.authenticate(new UsernamePasswordAuthenticationToken(
                        identifiant, motDePasse));
            } catch (org.springframework.security.core.AuthenticationException refus) {
                // c'est le cas mesure
            }
        }
    }

    @Nested
    @DisplayName("BCrypt")
    class Bcrypt {

        @Test
        @DisplayName("le sel est dans l'empreinte")
        void leSel() {
            assertThat(encodeur.encode("motdepasse"))
                    .isNotEqualTo(encodeur.encode("motdepasse"));
        }

        @Test
        @DisplayName("l'empreinte porte son cout")
        void leCout() {
            assertThat(new BCryptPasswordEncoder(12).encode("x"))
                    .startsWith("$2a$12$");
            assertThat(new BCryptPasswordEncoder(4).encode("x"))
                    .startsWith("$2a$04$");
        }

        @ParameterizedTest(name = "au cout {0}, une verification est plus lente")
        @ValueSource(ints = {10, 12})
        void plusLeCoutMonte(int cout) {
            var encodeurFort = new BCryptPasswordEncoder(cout);
            String empreinte = encodeurFort.encode("motdepasse");
            long debut = System.nanoTime();
            encodeurFort.matches("motdepasse", empreinte);
            long duree = (System.nanoTime() - debut) / 1_000_000;
            assertThat(duree)
                    .as("au cout %d, une verification prend %d ms".formatted(cout, duree))
                    .isGreaterThan(10);
        }

        @Test
        @DisplayName("l'encodeur delegant exige le prefixe")
        void leDelegant() {
            var delegant = PasswordEncoderFactories.createDelegatingPasswordEncoder();
            assertThat(delegant.encode("x")).startsWith("{bcrypt}");
            assertThatThrownBy(() -> delegant.matches("x",
                    new BCryptPasswordEncoder().encode("x")))
                    .as("une base remplie sans prefixe ne se relit plus apres "
                        + "migration vers le delegant")
                    .isInstanceOf(IllegalArgumentException.class);
        }

        @Test
        @DisplayName("aucun mot de passe du portail n'est stocke en clair")
        void aucunMotDePasseEnClair() {
            for (var identifiant : java.util.List.of("awa", "karim", "lea")) {
                assertThat(utilisateurs.compte(identifiant).empreinte())
                        .startsWith("$2a$")
                        .doesNotContain("motdepasse");
            }
        }
    }
}
