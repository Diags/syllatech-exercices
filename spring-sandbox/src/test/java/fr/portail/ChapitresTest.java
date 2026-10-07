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
 * Les six chapitres tournent, et disent toujours la meme chose.
 *
 * <p>Chacun demarre un vrai runner Spring Boot et lance de vrais processus :
 * ce sont les tests les plus lents du projet, et les seuls qui verifient ce
 * que l'apprenant verra a l'ecran. La sortie de chaque chapitre est retenue
 * — plusieurs assertions la relisent.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Menace    | C'est la meme chaine
        Chapitre2Runner    | 400 BAD_REQUEST
        Chapitre3Piloter   | delai depasse
        Chapitre4Durcir    | portes sont fermees
        Chapitre5Integrer  | mise en file
        Chapitre6Evasion   | ATTAQUES NON BLOQUEES
        """)
    @Timeout(600)
    @DisplayName("chaque chapitre tourne de bout en bout")
    void chaqueChapitreTourne(String classe, String attendu) throws Exception {
        String sortie = executer("fr.portail.chapitres." + classe);
        assertThat(sortie)
                .as(classe + " n'a pas affiche « " + attendu.strip() + " »\n"
                    + apercu(sortie))
                .contains(attendu.strip());
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 1 fait lire le VRAI secret par le code du candidat")
    void leChapitre1MontreLaFuite() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Menace");

        // La demonstration ne vaut que si la chaine lue par le script est
        // exactement celle de `application.properties`.
        assertThat(sortie).contains("sk-secret-de-production-a-ne-jamais-divulguer");
        assertThat(sortie).contains("C'est la meme chaine");

        // ⚠️ Et le refus du SecurityManager est DEMANDE a la JVM qui tourne,
        // pas affirme : beaucoup de documentations le disent « supprime ».
        // Il est seulement desactive — et cette nuance-la se mesure.
        assertThat(sortie)
                .contains("UnsupportedOperationException")
                .contains("Setting a Security Manager is not supported")
                .contains("getSecurityManager  : null");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 3 montre une mort sans message, et le dit")
    void leChapitre3ExpliqueLeSilence() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Piloter");

        assertThat(sortie).contains("code de sortie: 3");
        assertThat(sortie).contains("(aucune)");
        assertThat(sortie)
                .as("un code sans message doit etre explique, pas subi")
                .contains("ExitOnOutOfMemoryError");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 4 oppose 11 portes fermees a 10 ouvertes, et audite l'image livree")
    void leChapitre4CompteLesPortes() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Durcir");

        assertThat(sortie).contains("conforme : les 11 portes sont fermees");
        assertThat(sortie).contains("⚠️ 10 porte(s) ouverte(s) sur 11");
        assertThat(sortie)
                .as("l'audit d'image lit le Dockerfile du depot")
                .contains("conforme : les 5 regles sont satisfaites")
                .contains("⚠️ 5 regle(s) non satisfaite(s) sur 5");
        assertThat(sortie)
                .as("la sortie du bac a sable est hostile, et le chapitre le montre")
                .contains("&lt;script&gt;");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 6 compte les evasions des deux cotes de la frontiere")
    void leChapitre6CompteLesEvasions() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Evasion");

        assertThat(sortie).contains("ATTAQUES NON BLOQUEES");
        assertThat(sortie)
                .as("la boucle dans la JVM ne rend jamais la main")
                .contains("JAMAIS RENDUE");
        assertThat(sortie)
                .as("le disjoncteur s'ouvre au troisieme echec de demarrage")
                .contains("OUVERT");
        assertThat(sortie)
                .as("le predicat d'un test d'evasion est toujours le meme")
                .contains("codeSortie() != 0 || r.delaiDepasse()");
    }

    @Test
    @DisplayName("les six classes de chapitre sont la")
    void lesSixChapitres() {
        for (String nom : List.of("Chapitre1Menace", "Chapitre2Runner",
                "Chapitre3Piloter", "Chapitre4Durcir", "Chapitre5Integrer",
                "Chapitre6Evasion")) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }

    private static String executer(String classe) throws Exception {
        String retenue = SORTIES.get(classe);
        if (retenue != null) {
            return retenue;
        }
        ByteArrayOutputStream capture = new ByteArrayOutputStream();
        PrintStream originale = System.out;
        try {
            System.setOut(new PrintStream(capture, true, StandardCharsets.UTF_8));
            Class.forName(classe).getDeclaredMethod("main", String[].class)
                    .invoke(null, (Object) new String[0]);
        } finally {
            System.setOut(originale);
        }
        String sortie = capture.toString(StandardCharsets.UTF_8);
        SORTIES.put(classe, sortie);
        return sortie;
    }

    private static String apercu(String sortie) {
        List<String> lignes = sortie.lines().toList();
        return "--- sortie (" + lignes.size() + " lignes) ---\n"
                + String.join("\n", lignes.subList(0, Math.min(30, lignes.size())));
    }
}
