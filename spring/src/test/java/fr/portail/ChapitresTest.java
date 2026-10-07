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
 * Les six chapitres doivent tourner — et rester vrais.
 *
 * <p>Chacun démarre une vraie application Spring Boot : ces tests sont donc
 * les plus lents du projet. Ils sont aussi les seuls à vérifier ce que
 * l'apprenant verra réellement à l'écran, et pas seulement ce que le code
 * rend.
 *
 * <p>La sortie de chaque chapitre est retenue : plusieurs assertions la
 * relisent, et la relancer coûterait un démarrage complet à chaque fois.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Beans     | requetes ayant lu le nom d'UN AUTRE client
        Chapitre2Boot      | decisions evaluees
        Chapitre3Rest      | application/problem+json
        Chapitre4Jpa       | findAllAvecEntreprise()
        Chapitre5Securite  | AuthorizationFilter
        Chapitre6Docker    | part de notre code dans le total
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
    @DisplayName("le chapitre 4 montre bien 5 requetes contre 1")
    void leNPlusUnEstVisible() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Jpa");
        assertThat(sortie).contains("findAll()");
        assertThat(sortie).contains("findAllAvecEntreprise()");
        assertThat(sortie)
                .as("les deux pieges du cours doivent apparaitre")
                .contains("exception VERIFIEE")
                .contains("appel INTERNE");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 5 imprime la chaine de filtres, dans l'ordre")
    void laChaineEstImprimee() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Securite");
        assertThat(sortie).contains("BasicAuthenticationFilter");
        assertThat(sortie.indexOf("BasicAuthenticationFilter"))
                .isLessThan(sortie.indexOf("AuthorizationFilter"));
        assertThat(sortie).contains("/rapports/salaires");
    }

    @Test
    @DisplayName("les six classes de chapitre existent")
    void lesSixChapitres() {
        for (var nom : List.of("Chapitre1Beans", "Chapitre2Boot",
                "Chapitre3Rest", "Chapitre4Jpa", "Chapitre5Securite",
                "Chapitre6Docker")) {
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
