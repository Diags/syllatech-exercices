package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les six chapitres tournent, et disent toujours la même chose.
 *
 * <p>Chacun démarre une vraie application : ce sont les tests les plus lents
 * du projet, et les seuls qui vérifient ce que l'apprenant verra à l'écran.
 * La sortie de chaque chapitre est retenue — plusieurs assertions la relisent.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Chaine           | AuthorizationFilter
        Chapitre2Authentification | mitigateAgainstTimingAttack
        Chapitre3CorsCsrf         | Invalid CORS request
        Chapitre4Jwt              | PASSE ENCORE
        Chapitre5Oauth2           | telechargements du JWKS
        Chapitre6Keycloak         | regle consultee
        """)
    @Timeout(300)
    @DisplayName("chaque chapitre tourne de bout en bout")
    void chaqueChapitreTourne(String classe, String attendu) throws Exception {
        String sortie = executer("fr.portail.chapitres." + classe);
        assertThat(sortie)
                .as(classe + " n'a pas affiche « " + attendu.strip() + " »\n"
                    + apercu(sortie))
                .contains(attendu.strip());
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 1 montre 0 entree pour 40 requetes refusees")
    void leRefusNAtteintPasLeCode() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Chaine");
        assertThat(sortie).contains("entrees dans les controleurs       0");
        assertThat(sortie).contains("aucune identite");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 4 montre les trois attaques refusees")
    void lesAttaquesSontRefusees() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Jwt");
        assertThat(sortie)
                .contains("alg: none")
                .contains("signe en HMAC avec la cle PUBLIQUE")
                .contains("un role change en Base64");
        assertThat(sortie)
                .as("le JWKS ne doit jamais publier `d`")
                .contains("d — l'exposant PRIVE");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 6 montre 403 sans le pont, 200 avec")
    void lePontChangeTout() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Keycloak");
        assertThat(sortie).contains("sans convertisseur");
        assertThat(sortie).contains("convertisseur ACTIF");
    }

    @Test
    @DisplayName("les six classes de chapitre sont la")
    void lesSixChapitres() {
        for (var nom : List.of("Chapitre1Chaine", "Chapitre2Authentification",
                "Chapitre3CorsCsrf", "Chapitre4Jwt", "Chapitre5Oauth2",
                "Chapitre6Keycloak")) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }

    private static String executer(String classe) throws Exception {
        var retenue = SORTIES.get(classe);
        if (retenue != null) {
            return retenue;
        }
        var capture = new ByteArrayOutputStream();
        var originale = System.out;
        try {
            System.setOut(new PrintStream(capture, true, StandardCharsets.UTF_8));
            Class.forName(classe).getDeclaredMethod("main", String[].class)
                    .invoke(null, (Object) new String[0]);
        } finally {
            System.setOut(originale);
        }
        var sortie = capture.toString(StandardCharsets.UTF_8);
        SORTIES.put(classe, sortie);
        return sortie;
    }

    private static String apercu(String sortie) {
        var lignes = sortie.lines().toList();
        return "--- sortie (" + lignes.size() + " lignes) ---\n"
                + String.join("\n", lignes.subList(0, Math.min(30, lignes.size())));
    }
}
