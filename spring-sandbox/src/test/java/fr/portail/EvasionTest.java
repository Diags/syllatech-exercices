package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionDansLaJvm;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.TimeoutException;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les tests d'evasion : on n'affirme pas qu'une cage tient, on l'attaque.
 *
 * <p>⚠️ LE PREDICAT EST TOUJOURS LE MEME, ET C'EST LE POINT :
 *
 * <pre>
 *   assertThat(resultat.codeSortie() != 0 || resultat.delaiDepasse()).isTrue();
 * </pre>
 *
 * <p>On ne sait pas d'avance COMMENT la cage tiendra. Un refus de privilege,
 * une erreur d'execution, un delai depasse, une mort par manque de memoire :
 * les quatre sont des succes du bac a sable. Ecrire
 * {@code assertThat(code).isEqualTo(77)} rendrait le test faux le jour ou la
 * cage tient autrement — et c'est un jour ou l'on veut qu'il passe.
 *
 * <p>Un code 0 avec une sortie utile est le seul echec, et c'est un ticket
 * bloquant.
 *
 * <p>Ces tests doivent tourner en integration continue a chaque changement du
 * bac a sable, de son image, ou de sa version de runtime.
 */
class EvasionTest {

    private static final ExecutionEnBacASable BAC = new ExecutionEnBacASable(3, 48);

    /** Le seul verdict qui compte. */
    private static void doitEtreBloquee(Resultat resultat, String attaque) {
        assertThat(resultat.codeSortie() != 0 || resultat.delaiDepasse())
                .as("EVASION : « " + attaque + " » a rendu le code 0.\n"
                    + "sortie : " + resultat.sortie().strip())
                .isTrue();
        assertThat(resultat.bloque()).isTrue();
    }

    @ParameterizedTest(name = "{0}")
    @CsvSource(delimiter = '|', textBlock = """
        lire un fichier de l'hote  | lire_fichier "pom.xml"
        lire /etc/passwd           | lire_fichier "/etc/passwd"
        lire un secret de l'app    | secret jobportal.cle-api
        sortir vers le reseau      | connexion "127.0.0.1" 80
        sortir vers l'exterieur    | connexion "example.com" 443
        immobiliser le service     | boucle
        saturer le noeud           | memoire 400
        """)
    @Timeout(120)
    @DisplayName("aucune soumission hostile n'aboutit a un succes")
    void aucuneEvasion(String nom, String code) {
        Resultat resultat = BAC.lancer(DemandeExecution.script(code));
        doitEtreBloquee(resultat, nom);
    }

    @Test
    @Timeout(60)
    @DisplayName("l'enchainement d'attaques ne passe pas davantage")
    void lEnchainement() {
        Resultat resultat = BAC.lancer(DemandeExecution.script("""
                ecrire on commence gentiment
                somme 1 1
                lire_fichier "/etc/hostname"
                connexion "127.0.0.1" 22
                """));

        doitEtreBloquee(resultat, "enchainement");
        assertThat(resultat.sortie())
                .as("les lignes honnetes sortent avant la premiere porte fermee")
                .contains("on commence gentiment", "2");
        assertThat(resultat.erreurs())
                .as("le script s'arrete a la PREMIERE porte, pas a la derniere")
                .contains("lire des fichiers")
                .doesNotContain("connexion reseau");
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ l'inondation de sortie N'EST PAS bloquee — elle est plafonnee")
    void lInondationPasse() {
        // Honnetete du tableau : une seule des sept attaques rend un code 0,
        // et c'est celle-la. Le bac a sable ne la refuse pas — il n'y a rien
        // d'illegitime a ecrire sur sa propre sortie standard. C'est le
        // PLAFOND qui protege le runner, et il agit apres coup.
        Resultat resultat = BAC.lancer(DemandeExecution.script(
                ("ecrire " + "X".repeat(500) + "\n").repeat(80)));

        assertThat(resultat.codeSortie()).isZero();
        assertThat(resultat.sortie()).endsWith("(tronque)");
        assertThat(resultat.sortie().length()).isLessThan(11_000);
    }

    @Test
    @Timeout(120)
    @DisplayName("⚠️ LA MESURE : la meme batterie contre la JVM de l'application")
    void laMemeBatterieDansLaJvm() {
        // ⚠️ Ce test AFFIRME que la mauvaise implantation laisse passer.
        // Il n'est pas a « corriger » : le jour ou il echouerait, c'est
        // que `ExecutionDansLaJvm` aurait ete durcie — et le cours perdrait
        // sa piece a conviction.
        ExecutionDansLaJvm dansLaJvm =
                new ExecutionDansLaJvm(nom -> "sk-secret-de-production");

        List<String> passees = new ArrayList<>();
        for (String code : List.of("lire_fichier \"pom.xml\"",
                                   "secret jobportal.cle-api",
                                   "memoire 64")) {
            Resultat resultat = avecUneLaisse(dansLaJvm, code);
            if (resultat != null && resultat.codeSortie() == 0) {
                passees.add(code);
            }
        }

        assertThat(passees)
                .as("dans la JVM de l'application, ces trois-la aboutissent")
                .containsExactlyInAnyOrder("lire_fichier \"pom.xml\"",
                                           "secret jobportal.cle-api",
                                           "memoire 64");

        // Et les MEMES soumissions, a travers la frontiere de processus :
        for (String code : passees) {
            doitEtreBloquee(BAC.lancer(DemandeExecution.script(code)), code);
        }
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ dans la JVM, la boucle ne rend JAMAIS la main")
    void laBoucleNeRendJamaisLaMain() {
        // Il n'y a pas de « code de sortie » a verifier : il n'y a pas de
        // sortie. `Thread.stop` est supprime depuis Java 20, `cancel(true)`
        // pose un drapeau que la boucle ne regarde pas, et il n'existe
        // AUCUNE facon d'arreter un fil qui ne coopere pas.
        //
        // Le fil abandonne ici tourne jusqu'a la fin de la JVM de test. Dans
        // un vrai serveur, il tourne jusqu'au redemarrage.
        Resultat jamais = avecUneLaisse(
                new ExecutionDansLaJvm(nom -> null), "boucle");
        assertThat(jamais)
                .as("l'appel n'a pas rendu la main dans le delai imparti")
                .isNull();

        // Meme soumission, a travers la frontiere : tuee, et le runner vit.
        Resultat tuee = BAC.lancer(DemandeExecution.script("boucle"));
        assertThat(tuee.delaiDepasse()).isTrue();
        assertThat(BAC.lancer(DemandeExecution.script("ecrire vivant"))
                      .sortie().strip()).isEqualTo("vivant");
    }

    /**
     * Appelle un service SANS borne interne en lui en imposant une de
     * l'exterieur, sur un fil demon pour que la JVM de test puisse finir.
     *
     * @return {@code null} quand l'appel n'a jamais rendu la main
     */
    private static Resultat avecUneLaisse(fr.portail.runner.ServiceExecution service,
                                          String code) {
        ExecutorService pool = Executors.newSingleThreadExecutor(tache -> {
            Thread fil = new Thread(tache, "evasion-non-bornee");
            fil.setDaemon(true);
            return fil;
        });
        try {
            Future<Resultat> promesse = pool.submit(
                    () -> service.lancer(DemandeExecution.script(code)));
            return promesse.get(8, TimeUnit.SECONDS);
        } catch (TimeoutException abandon) {
            return null;
        } catch (Exception erreur) {
            return new Resultat("", String.valueOf(erreur), 1, false, 0);
        } finally {
            pool.shutdownNow();
        }
    }
}
