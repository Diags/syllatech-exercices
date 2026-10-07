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
 * <p>Ce qui est vérifié ici n'est pas « ça n'a pas planté » mais « la mesure
 * annoncée est bien celle qui s'affiche ». Un chapitre dont la narration se
 * désaccorde de sa mesure devient faux sans faire d'erreur ; ces tests sont
 * le garde-fou.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Evenementiel   | compteur idempotent
        Chapitre2Axon           | SimpleCommandBus
        Chapitre3Cqrs           | apres le rejeu
        Chapitre4EventSourcing  | un snapshot existe-t-il
        Chapitre5Saga           | AnnulerCandidature (compensation)
        Chapitre6Projet         | evenement PERDU
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
    @DisplayName("le chapitre 1 montre le compteur naif qui ment")
    void leCompteurNaifMent() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Evenementiel");
        assertThat(sortie).contains("compteur naif           2                   2");
        assertThat(sortie).contains("compteur idempotent     2                   1");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 2 montre que le bus et le magasin sont le meme objet")
    void leBusEstLeMagasin() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre2Axon");
        assertThat(sortie).contains("bus d'evenements               EmbeddedEventStore");
        assertThat(sortie).contains("IllegalArgumentException");
        assertThat(sortie).contains("SubscribingEventProcessor");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 3 reconstruit la vue a l'identique")
    void laVueSeReconstruit() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Cqrs");
        assertThat(sortie).contains("apres le vidage       0");
        assertThat(sortie).contains("le modele d'ecriture a-t-il bouge    non");
        assertThat(sortie).contains("etat de c-awa                  RETENUE");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 4 montre le rejeu qui s'allonge, puis le snapshot")
    void leRejeuEtLeSnapshot() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4EventSourcing");
        assertThat(sortie).contains("evenements relus au chargement     0");
        assertThat(sortie).contains("sans snapshot, il en relirait      7");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 5 montre les deux chemins de la saga")
    void lesDeuxCheminsDeLaSaga() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Saga");
        assertThat(sortie).contains("saga terminee (succes) pour c-awa");
        assertThat(sortie).contains("creneau REFUSE");
        assertThat(sortie).contains("saga terminee (compensee) pour c-lea");
        assertThat(sortie).contains("c-lea               ANNULEE");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 6 montre l'outbox qui rattrape la panne")
    void lOutboxRattrape() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Projet");
        assertThat(sortie).contains("sans outbox       1               0");
        assertThat(sortie).contains("avec outbox       1               1");
        assertThat(sortie).contains("traceId distincts              1");
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
