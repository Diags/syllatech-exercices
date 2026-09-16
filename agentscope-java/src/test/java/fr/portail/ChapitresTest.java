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
 * <p>Ce sont les tests les plus lents du projet — le chapitre 6 demarre une
 * vraie application Spring Boot — et les seuls qui verifient ce que
 * l'apprenant verra a l'ecran. La sortie de chaque chapitre est retenue :
 * plusieurs assertions la relisent.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Agent        | un agent ReAct
        Chapitre2Modeles      | TYPE D'EVENEMENT
        Chapitre3Outils       | repli sur le MODE
        Chapitre4Sandbox      | LE CHEMIN N'EST PAS FILTRE
        Chapitre5MultiAgents  | CE QUE LE MIDDLEWARE A VU
        Chapitre6Integrer     | APRES REDEMARRAGE
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
    @DisplayName("le chapitre 1 oppose 0 outil execute a 2, et 0 reference a 3")
    void leChapitre1OpposeLesDeux() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Agent");

        assertThat(sortie).contains("appels au modele           1                      3");
        assertThat(sortie).contains("outils EXECUTES            0                      2");
        assertThat(sortie)
                .as("le simple appel ne cite aucune reference reelle")
                .contains("0 (aucune)");
        assertThat(sortie).contains("rechercher_offres(java)");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 3 montre qu'une regle au joker ne protege rien")
    void leChapitre3MontreLeJoker() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Outils");

        assertThat(sortie).contains("⚠️ NON — repli sur le MODE");
        assertThat(sortie)
                .as("la mesure phare : l'agent annonce une action qui n'a pas eu lieu")
                .contains("CE QUE « DEMANDER APPROBATION » NE FAIT PAS TOUT SEUL")
                .contains("catalogue compte toujours 6 offres, pour 0 outil(s)");
        assertThat(sortie)
                .as("la chaine vide, elle, s'applique")
                .contains("\"\" (chaine vide)");
        assertThat(sortie)
                .as("les cinq modes sont tabules")
                .contains("EXPLORE").contains("BYPASS").contains("DONT_ASK");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 4 montre ce que le filtre laisse passer")
    void leChapitre4MontreLesLimites() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Sandbox");

        assertThat(sortie).contains("refusees : 4 sur 10");
        assertThat(sortie).contains("LE CHEMIN N'EST PAS FILTRE");
        assertThat(sortie)
                .as("ni Docker ni Kubernetes ne sont lances, et c'est dit")
                .contains("NI DOCKER NI KUBERNETES NE SONT LANCES ICI");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 5 montre le sous-agent perdu en silence")
    void leChapitre5MontreLeSousAgentPerdu() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5MultiAgents");

        assertThat(sortie).contains("Le premier sous-agent a DISPARU");
        assertThat(sortie).contains("demander_au_chercheur");
        assertThat(sortie)
                .as("le middleware compte la boucle entiere")
                .contains("appels au modele");
    }

    @Test
    @Timeout(600)
    @DisplayName("le chapitre 6 montre l'etat qui survit, et celui qui ne survit pas")
    void leChapitre6MontreLaPersistance() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Integrer");

        assertThat(sortie).contains("sur disque (fichiers JSON)");
        assertThat(sortie).contains("en memoire (le DEFAUT)");
        assertThat(sortie)
                .as("de vrais fragments SSE sont recus")
                .contains("fragments SSE recus");
        assertThat(sortie).contains("OFF-101");
    }

    @Test
    @DisplayName("les six classes de chapitre sont la")
    void lesSixChapitres() {
        for (String nom : List.of("Chapitre1Agent", "Chapitre2Modeles",
                "Chapitre3Outils", "Chapitre4Sandbox", "Chapitre5MultiAgents",
                "Chapitre6Integrer")) {
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
