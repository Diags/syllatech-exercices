package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.langage.Capacite;
import fr.portail.langage.Interprete;
import fr.portail.langage.Politique;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Le petit langage du candidat, et la politique qui le borne.
 *
 * <p>⚠️ Plusieurs de ces tests affirment que la menace FONCTIONNE : sous
 * {@code toutPermis}, un script lit vraiment un fichier de l'hote. Ce ne
 * sont pas des tests « a corriger » — ce sont les mesures du chapitre 1. Un
 * jour ou ils echoueraient, c'est le langage qui aurait change, pas la
 * demonstration qui serait devenue fausse.
 */
class LangageTest {

    private static Interprete permissif() {
        return new Interprete(Politique.toutPermis(),
                              nom -> "valeur-" + nom);
    }

    private static Interprete bacASable() {
        return new Interprete(Politique.rienDuTout());
    }

    // -- le langage lui-meme ----------------------------------------------

    @ParameterizedTest(name = "« {0} » → sortie « {1} », code {2}")
    @CsvSource(delimiter = '|', textBlock = """
        ecrire bonjour      | bonjour | 0
        somme 21 21         | 42      | 0
        somme -3 3          | 0       | 0
        ecrire  a   b       | a b     | 0
        """)
    @DisplayName("les verbes sans privilege font ce qu'ils disent")
    void lesVerbesOrdinaires(String source, String attendu, int code) {
        Interprete.Trace trace = bacASable().executer(source);
        assertThat(trace.sortie().strip()).isEqualTo(attendu.strip());
        assertThat(trace.code()).isEqualTo(code);
    }

    @Test
    @DisplayName("« sortie n » rend le code demande et arrete le script")
    void leCodeDeSortie() {
        Interprete.Trace trace = bacASable().executer("""
                ecrire avant
                sortie 9
                ecrire apres
                """);
        assertThat(trace.code()).isEqualTo(9);
        assertThat(trace.sortie()).contains("avant").doesNotContain("apres");
    }

    @Test
    @DisplayName("les commentaires et les lignes vides sont ignores")
    void lesCommentaires() {
        Interprete.Trace trace = bacASable().executer("""
                # le sujet

                ecrire ok
                """);
        assertThat(trace.sortie().strip()).isEqualTo("ok");
        assertThat(trace.code()).isZero();
    }

    @Test
    @DisplayName("un verbe inconnu rend le code 2, pas une exception")
    void leVerbeInconnu() {
        Interprete.Trace trace = bacASable().executer("teleporter lune");
        assertThat(trace.code()).isEqualTo(2);
        assertThat(trace.erreurs()).contains("verbe inconnu");
    }

    @Test
    @DisplayName("les guillemets gardent les espaces d'un argument")
    void lesGuillemets() {
        Interprete.Trace trace = permissif().executer(
                "ecrire \"deux mots\" et trois");
        assertThat(trace.sortie().strip()).isEqualTo("deux mots et trois");
    }

    // -- la menace, mesuree -----------------------------------------------

    @Test
    @DisplayName("⚠️ sous « tout permis », le script LIT un fichier de l'hote")
    void laMenaceEstReelle(@TempDir Path dossier) throws Exception {
        Path fichier = dossier.resolve("dossier-rh.txt");
        Files.writeString(fichier, "salaires 2026");

        Interprete.Trace trace = permissif().executer(
                "lire_fichier \"" + fichier.toString().replace('\\', '/') + "\"");

        assertThat(trace.code()).isZero();
        assertThat(trace.sortie()).contains("salaires 2026");
    }

    @Test
    @DisplayName("⚠️ sous « tout permis », le script LIT une propriete")
    void leSecretEstLisible() {
        Interprete.Trace trace = permissif().executer("secret jobportal.cle-api");
        assertThat(trace.code()).isZero();
        assertThat(trace.sortie().strip()).isEqualTo("valeur-jobportal.cle-api");
    }

    // -- la politique ------------------------------------------------------

    @ParameterizedTest(name = "« {0} » est refuse avec le code 77")
    @CsvSource(delimiter = '|', textBlock = """
        lire_fichier "/etc/passwd"   | lire des fichiers
        connexion "127.0.0.1" 80     | ouvrir une connexion reseau
        secret jobportal.cle-api     | lire les proprietes de l'application
        """)
    @DisplayName("sous « rien du tout », les trois portes sont fermees")
    void lesTroisPortes(String source, String libelle) {
        Interprete.Trace trace = bacASable().executer(source);
        assertThat(trace.code()).isEqualTo(77);
        assertThat(trace.erreurs()).contains(libelle.strip());
        assertThat(trace.sortie()).isEmpty();
    }

    @Test
    @DisplayName("une politique se decoupe : le disque sans le reseau")
    void unePolitiquePartielle() {
        Politique lecture = Politique.de("lecture seule", Capacite.FICHIERS);
        assertThat(lecture.accorde(Capacite.FICHIERS)).isTrue();
        assertThat(lecture.accorde(Capacite.RESEAU)).isFalse();
        assertThat(lecture.accordees()).hasSize(1);

        Interprete.Trace trace = new Interprete(lecture)
                .executer("connexion \"127.0.0.1\" 80");
        assertThat(trace.code()).isEqualTo(77);
    }

    @Test
    @DisplayName("⚠️ « tout permis » accorde les trois capacites — c'est le defaut d'un moteur de script")
    void toutPermisAccordeTout() {
        assertThat(Politique.toutPermis().accordees())
                .containsExactlyInAnyOrder(Capacite.values());
        assertThat(Politique.rienDuTout().accordees()).isEmpty();
    }

    // -- le plafond de sortie ----------------------------------------------

    @Test
    @DisplayName("la sortie est plafonnee AVANT de traverser HTTP")
    void laSortieEstPlafonnee() {
        String enorme = "X".repeat(Interprete.PLAFOND_DE_SORTIE + 5_000);
        String tronque = Interprete.tronquer(enorme);

        assertThat(tronque).hasSize(Interprete.PLAFOND_DE_SORTIE + "…(tronque)".length());
        assertThat(tronque).endsWith("(tronque)");
        assertThat(Interprete.tronquer("court")).isEqualTo("court");
    }

    @Test
    @DisplayName("un script qui inonde la sortie est coupe au plafond")
    void leScriptQuiInonde() {
        String source = ("ecrire " + "A".repeat(400) + "\n").repeat(200);
        Interprete.Trace trace = bacASable().executer(source);

        assertThat(trace.sortie().length())
                .isLessThanOrEqualTo(Interprete.PLAFOND_DE_SORTIE + 32);
        assertThat(trace.sortie()).endsWith("(tronque)");
    }

    /**
     * ⚠️ Six verbes sur huit seulement. {@code boucle} et {@code memoire} ne
     * peuvent PAS etre appeles ici : ils ne rendent jamais la main, et la
     * JVM de test n'a aucun moyen de les arreter. Ils sont mesures dans
     * {@link BacASableTest}, ou un processus separe leur impose un delai et
     * un plafond — ce qui est exactement la these du cours.
     */
    @Test
    @DisplayName("les six verbes qui se terminent sont reconnus")
    void lesVerbesQuiSeTerminent() {
        List<String> verbes = List.of("ecrire x", "somme 1 1", "sortie 0",
                "lire_fichier \"x\"", "connexion \"x\" 1", "secret x");
        for (String source : verbes) {
            Interprete.Trace trace = bacASable().executer(source);
            assertThat(trace.erreurs())
                    .as("« " + source + " » doit etre un verbe connu")
                    .doesNotContain("verbe inconnu");
        }
    }
}
