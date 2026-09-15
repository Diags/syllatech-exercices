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
 * <p>Chacun démarre un écosystème complet : ce sont les tests les plus lents
 * du projet, et les seuls qui vérifient ce que l'apprenant verra à l'écran.
 * La sortie de chaque chapitre est retenue — plusieurs assertions la relisent.
 */
class ChapitresTest {

    private static final Map<String, String> SORTIES = new ConcurrentHashMap<>();

    @ParameterizedTest(name = "{0} s'execute et affiche ses mesures")
    @CsvSource(delimiter = '|', textBlock = """
        Chapitre1Decoupage    | par HTTP (microservice)
        Chapitre2Annuaire     | OFFRES-SERVICE
        Chapitre3Passerelle   | UN 500 N'OUVRE PAS LE CIRCUIT
        Chapitre4Docker       | version precise
        Chapitre5Kubernetes   | maxUnavailable
        Chapitre6Securite     | X-Request-Id
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
    @DisplayName("le chapitre 1 chiffre le cout du reseau")
    void leCoutDuReseau() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre1Decoupage");
        assertThat(sortie).contains("en memoire (monolithe)");
        assertThat(sortie).contains("par HTTP (microservice)");
        assertThat(sortie).contains("aucune connexion");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 2 montre les delais par defaut d'Eureka")
    void lesDelaisDEureka() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre2Annuaire");
        assertThat(sortie).contains("expiration d'un bail      90 s");
        assertThat(sortie).contains("auto-preservation         activee");
        assertThat(sortie).contains("oubliee par l'annuaire         oui");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 3 montre le circuit qui reste ferme, puis s'ouvre")
    void leCircuitOuvreSeulementSiDeclare() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre3Passerelle");
        assertThat(sortie).contains("replis servis              0");
        assertThat(sortie).contains("replis servis              8");
        assertThat(sortie).contains("OPEN");
        assertThat(sortie).contains("le circuit s'est-il referme      oui");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 4 lit le Dockerfile et le compose")
    void leChapitreDocker() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre4Docker");
        assertThat(sortie).contains("non-root ?");
        assertThat(sortie)
                .as("`latest` doit etre signale comme n'etant pas une version")
                .contains("offres-service:latest");
        assertThat(sortie).contains("attend la DISPONIBILITE");
        assertThat(sortie).contains("service_healthy");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 5 calcule la mise a jour, et le creux a zero")
    void leChapitreKubernetes() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre5Kubernetes");
        assertThat(sortie).contains("sonde de vivacite         declare           ABSENT");
        assertThat(sortie).contains("surge=0 indispo=4");
        assertThat(sortie).contains("0 pod");
    }

    @Test
    @Timeout(300)
    @DisplayName("le chapitre 6 montre le contournement de la passerelle")
    void leChapitreSecurite() throws Exception {
        String sortie = executer("fr.portail.chapitres.Chapitre6Securite");
        assertThat(sortie).contains("en direct, sans jeton         200");
        assertThat(sortie).contains("identifiants differents        oui");
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
