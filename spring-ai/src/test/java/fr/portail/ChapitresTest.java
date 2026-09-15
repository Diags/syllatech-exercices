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
        Chapitre1ChatClient  | morceaux recus
        Chapitre2Structure   | json-schema.org
        Chapitre3Rag         | Context information is below
        Chapitre4Outils      | rechercherOffres a rendu
        Chapitre5Multimodal  | image/png
        Chapitre6Production  | gen_ai.client.token.usage
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
    @DisplayName("le chapitre 1 montre 1 message sans defaultSystem, 2 avec")
    void leMessageSystemeCompte() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1ChatClient");
        assertThat(sortie).contains("sans defaultSystem, messages envoyes");
        assertThat(sortie).contains("avec defaultSystem, messages envoyes");
        assertThat(sortie).contains("UnsupportedOperationException");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 2 montre passe, passe, puis ECHEC sur le template")
    void lePiegeAAccoladesEstMesure() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre2Structure");
        assertThat(sortie)
                .as("la narration annonce deux lignes qui passent et une qui echoue")
                .contains("concatene ET un vrai parametre a cote")
                .contains("ECHEC : IllegalStateException");
        assertThat(sortie).contains("StreamReadException");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 3 montre l'advisor disparu et la question remplacee")
    void leRagMontreSesDeuxPieges() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Rag");
        assertThat(sortie)
                .as("`QuestionAnswerAdvisor` n'existe plus en Spring AI 2")
                .contains("ABSENTE du classpath");
        assertThat(sortie)
                .as("un seuil trop haut remplace la question, sans erreur")
                .contains("outside your knowledge base")
                .contains("erreur levee                   aucune");
        assertThat(sortie)
                .as("le document le mieux classe est celui qui dit NON")
                .contains("dit NON au teletravail");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 4 montre 2 appels au modele pour 1 outil")
    void lAllerRetourEstMesure() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Outils");
        assertThat(sortie).contains("appels au modele               2");
        assertThat(sortie).contains("appels a l'outil               1");
        assertThat(sortie)
                .as("le schema JSON deduit doit s'afficher en entier")
                .contains("json-schema.org")
                .contains("\"motCle\"");
        assertThat(sortie).contains("outils joints a l'appel          3");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 5 montre l'image hors du texte")
    void leMultimodalMontreLImageHorsDuTexte() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Multimodal");
        assertThat(sortie).contains("l'image y apparait-elle        NON");
        assertThat(sortie).contains("est-il un ChatModel ?            NON");
        assertThat(sortie).contains("reponses identiques            oui");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 6 montre la metrique et la fragilite du juge")
    void laProductionMontreSesChiffres() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Production");
        assertThat(sortie).contains("gen_ai.client.token.usage");
        assertThat(sortie)
                .as("« Yes, absolument. » veut dire oui, et echoue quand meme")
                .contains("Yes, absolument");
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
