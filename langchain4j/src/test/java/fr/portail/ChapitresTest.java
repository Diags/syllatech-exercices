package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
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
 *
 * <p>Ce qui est vérifié ici n'est pas « ça n'a pas planté » mais « la mesure
 * annoncée est bien celle qui s'affiche ». Un chapitre dont la narration se
 * désaccorde de sa mesure devient faux sans faire d'erreur ; ces tests sont
 * le garde-fou.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Demarrer   | est-ce un proxy JDK
        Chapitre2AiServices | RESPONSE_FORMAT_JSON_SCHEMA
        Chapitre3Rag        | Answer using the following information
        Chapitre4Outils     | rechercherOffres a rendu
        Chapitre5Memoire    | temps jusqu'au premier jeton
        Chapitre6Production | vus par l'ecouteur
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
    @DisplayName("le chapitre 1 montre le proxy et deux messages")
    void leProxyEstMontre() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Demarrer");
        assertThat(sortie).contains("est-ce un proxy JDK        oui");
        assertThat(sortie).contains("[SYSTEM]").contains("[USER]");
        assertThat(sortie).contains("methodes a ecrire", "doChat");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 2 montre les DEUX facons d'imposer un format")
    void lesDeuxFaconsSontMontrees() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre2AiServices");
        assertThat(sortie)
                .as("sans capacite, le schema est ecrit dans le prompt")
                .contains("You must answer strictly in the following JSON format");
        assertThat(sortie)
                .as("avec la capacite, il passe dans la requete")
                .contains("dans la requete");
        assertThat(sortie).contains("OutputParsingException");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 3 montre le chevauchement nul et le seuil muet")
    void leRagMontreSesDeuxPieges() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Rag");
        assertThat(sortie)
                .as("recursive(300, 30) ne chevauche rien sur de la prose")
                .contains("30 caracteres           8           0 caracteres");
        assertThat(sortie)
                .as("un minScore trop haut ne leve rien")
                .contains("passages rendus                0")
                .contains("erreur levee                   aucune");
        assertThat(sortie).contains("dit NON au teletravail");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 4 montre 2 appels au modele pour 1 outil, et la boucle a 100")
    void lAllerRetourEtLaBoucle() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Outils");
        assertThat(sortie).contains("appels au modele               2");
        assertThat(sortie).contains("appels a l'outil               1");
        assertThat(sortie)
                .as("le plafond par defaut laisse passer cent appels")
                .contains("aucun (defaut)        100");
        assertThat(sortie).contains("outils joints avec `.tools()`    3");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 5 montre l'isolation des memoires et le flux")
    void laMemoireEtLeFlux() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Memoire");
        assertThat(sortie).contains("IllegalConfigurationException au BUILD");
        assertThat(sortie).contains("le prompt d'awa parle de Nantes    non");
        assertThat(sortie).contains("texte recolle = texte d'un coup      oui");
        assertThat(sortie).contains("[TEXT, IMAGE]");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 6 montre l'ecouteur muet de l'exemple du cours")
    void lEcouteurMuet() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Production");
        assertThat(sortie).contains("`chat` (exemple du cours)   3             0");
        assertThat(sortie).contains("TimeoutException");
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
