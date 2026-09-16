package fr.portail;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.commun.Console;
import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les six chapitres doivent tourner — et rester vrais.
 *
 * <p>Un chapitre qui plante n'enseigne rien, et un chapitre qu'on ne relance
 * jamais dérive sans qu'on le voie. Ces tests les exécutent tous les six et
 * cherchent, dans leur sortie, les phrases que le chapitre promet.
 *
 * <p>Ce sont aussi les tests les plus lents du projet : le chapitre 5 lance
 * cinq mille tâches, deux fois. C'est le prix d'une mesure qui n'est pas
 * simulée — la sortie de chaque chapitre est donc retenue et relue.
 */
class ChapitresTest {

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Fondamentaux | de -128 a 127
        Chapitre2Objets       | extends HashSet
        Chapitre3Collections  | Arrays.asList
        Chapitre4Streams      | peek a vu 0
        Chapitre5Concurrence  | threads porteurs distincts
        Chapitre6Java25       | Le portail publie 2 offres.
        """)
    @Timeout(180)
    @DisplayName("chaque chapitre tourne de bout en bout")
    void chaqueChapitreTourne(String classe, String attendu) throws Exception {
        String sortie = executer("fr.portail.chapitres." + classe);
        assertTrue(sortie.contains(attendu.strip()),
                classe + " n'a pas affiche « " + attendu.strip() + " ».\n"
                + apercu(sortie));
    }

    @Nested
    @DisplayName("les chapitres restent coherents avec le cours")
    class Coherence {

        @Test
        @Timeout(120)
        @DisplayName("le chapitre 2 montre bien le compteur a 6 et la composition a 3")
        void leCompteurDouble() throws Exception {
            String sortie = executer("fr.portail.chapitres.Chapitre2Objets");
            assertTrue(sortie.contains("extends HashSet         6"), apercu(sortie));
            assertTrue(sortie.contains("composition             3"), apercu(sortie));
        }

        @Test
        @Timeout(120)
        @DisplayName("le chapitre 4 montre 100 elements consommes par sorted")
        void sortedConsommeTout() throws Exception {
            String sortie = executer("fr.portail.chapitres.Chapitre4Streams");
            assertTrue(sortie.contains("apres 100 elements"), apercu(sortie));
            assertTrue(sortie.contains("apres 3 elements"), apercu(sortie));
        }

        @Test
        @Timeout(120)
        @DisplayName("le chapitre 6 fait tourner un fichier source compact")
        void leFichierCompactTourne() throws Exception {
            String sortie = executer("fr.portail.chapitres.Chapitre6Java25");
            assertTrue(sortie.contains("- OFF-014"), apercu(sortie));
            assertTrue(sortie.contains("- OFF-021"), apercu(sortie));
        }
    }

    @Nested
    @DisplayName("la console partagee")
    class ConsoleDeTest {

        @Test
        @DisplayName("plier respecte la largeur demandee")
        void plierRespecteLaLargeur() {
            var lignes = Console.plier(
                    "un texte assez long pour devoir etre coupe en plusieurs "
                    + "lignes de largeur raisonnable", 20);
            assertTrue(lignes.size() > 1);
            for (var ligne : lignes) {
                assertTrue(ligne.length() <= 22, "ligne trop longue : " + ligne);
            }
        }

        @Test
        @DisplayName("plier ne perd aucun mot")
        void plierNePerdRien() {
            String texte = "un texte assez long pour devoir etre coupe en morceaux";
            assertTrue(String.join(" ", Console.plier(texte, 15)).equals(texte));
        }

        @Test
        @DisplayName("les deux-points ne commencent jamais une ligne")
        void laPonctuationResteCollee() {
            var lignes = Console.plier(
                    "voici une phrase de longueur bien choisie pour que le "
                    + "deux-points tombe pile : au debut d'une ligne", 52);
            for (var ligne : lignes) {
                assertFalse(ligne.startsWith(":"), "deux-points orphelin : " + ligne);
                assertFalse(ligne.startsWith(";"), "point-virgule orphelin : " + ligne);
            }
        }

        @Test
        @DisplayName("un guillemet ouvrant ne termine jamais une ligne")
        void leGuillemetOuvrantResteAvecSonMot() {
            var lignes = Console.plier(
                    "une phrase construite pour que le guillemet ouvrant tombe "
                    + "juste au bout de la ligne « immuable » et pas ailleurs", 56);
            for (var ligne : lignes) {
                assertFalse(ligne.endsWith("«"), "guillemet orphelin : " + ligne);
            }
        }

        @Test
        @DisplayName("plier d'un texte vide rend une liste vide")
        void plierDuVide() {
            assertTrue(Console.plier("", 20).isEmpty());
        }

        @Test
        @DisplayName("un mot plus long que la largeur n'est pas coupe")
        void leMotTropLong() {
            var lignes = Console.plier("court supercalifragilisticexpialidocious", 10);
            assertTrue(lignes.contains("supercalifragilisticexpialidocious"));
        }
    }

    /**
     * Lance le {@code main} d'une classe et rend ce qu'elle a écrit.
     *
     * <p>Le résultat est retenu : le chapitre 5 lance cinq mille tâches, et
     * plusieurs tests lisent sa sortie. La relancer à chaque assertion
     * ajouterait une trentaine de secondes pour rien — et une suite de tests
     * qu'on n'attend pas est une suite qu'on ne lance plus.
     */
    private static final java.util.Map<String, String> SORTIES =
            new java.util.concurrent.ConcurrentHashMap<>();

    private static String executer(String classe) throws Exception {
        var retenue = SORTIES.get(classe);
        if (retenue != null) {
            return retenue;
        }
        var capture = new ByteArrayOutputStream();
        var originale = System.out;
        try {
            System.setOut(new PrintStream(capture, true, StandardCharsets.UTF_8));
            Class.forName(classe)
                    .getDeclaredMethod("main", String[].class)
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
                + String.join("\n", lignes.subList(0, Math.min(40, lignes.size())));
    }

    @Test
    @DisplayName("les six classes de chapitre sont bien la")
    void lesSixChapitres() {
        var noms = List.of("Chapitre1Fondamentaux", "Chapitre2Objets",
                "Chapitre3Collections", "Chapitre4Streams",
                "Chapitre5Concurrence", "Chapitre6Java25");
        for (var nom : noms) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }
}
