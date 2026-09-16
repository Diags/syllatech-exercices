package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionDansLaJvm;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

/**
 * Ce qu'une frontiere de PROCESSUS apporte — mesure, pas affirme.
 *
 * <p>Chaque test de cette classe lance un vrai {@code java} enfant. Ce sont
 * les tests les plus lents apres les chapitres, et ce sont eux qui portent
 * la these du cours : le tueur qui fonctionne est le systeme d'exploitation.
 */
class BacASableTest {

    private static final ExecutionEnBacASable BAC = new ExecutionEnBacASable(3, 48);

    private static Resultat lancer(String code) {
        return BAC.lancer(DemandeExecution.script(code));
    }

    // -- la ligne de commande ----------------------------------------------

    @Test
    @DisplayName("la commande porte les quatre drapeaux qui bornent l'enfant")
    void laCommandeEstBornee() {
        List<String> commande = BAC.commande();

        assertThat(commande).contains("-Xmx48m");
        assertThat(commande).contains("-XX:+ExitOnOutOfMemoryError");
        assertThat(commande).contains("-XX:ActiveProcessorCount=1");
        assertThat(commande).endsWith("fr.portail.bac.Executeur");
        assertThat(commande.getFirst())
                .as("c'est un vrai executable java")
                .contains("java");
    }

    @Test
    @DisplayName("⚠️ l'enfant ne recoit ni Spring, ni le metier, sur son chemin de classes")
    void leCheminDeClassesEstMinimal() {
        List<String> commande = BAC.commande();
        String chemin = commande.get(commande.indexOf("-cp") + 1);

        // Moins il y a de classes dans un bac a sable, moins il y a de
        // gadgets a enchainer. Ici : un seul repertoire.
        assertThat(chemin).doesNotContain("spring-boot");
        assertThat(chemin).doesNotContain("jackson");
        assertThat(chemin.split(java.io.File.pathSeparator))
                .as("un seul element sur le chemin de classes")
                .hasSize(1);
    }

    // -- les trois garde-fous ----------------------------------------------

    @Test
    @Timeout(30)
    @DisplayName("⚠️ LA MESURE : une boucle sans fin est TUEE au bout du delai")
    void leDelaiEstDur() {
        long depart = System.nanoTime();
        Resultat resultat = lancer("ecrire je pars\nboucle");
        long secondes = (System.nanoTime() - depart) / 1_000_000_000L;

        assertThat(resultat.delaiDepasse()).isTrue();
        assertThat(resultat.codeSortie()).isEqualTo(-1);
        assertThat(resultat.erreurs()).contains("processus tue");
        assertThat(secondes)
                .as("le delai est de 3 s : on ne l'attend ni moins, ni bien plus")
                .isBetween(2L, 12L);
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ LA MESURE : une allocation sans fin tue l'ENFANT, pas le runner")
    void laMemoireEstBornee() {
        Resultat resultat = lancer("memoire 400");

        assertThat(resultat.codeSortie()).isNotZero();
        assertThat(resultat.delaiDepasse())
                .as("l'enfant meurt tout de suite, il n'atteint pas le delai")
                .isFalse();

        // Le runner, lui, est toujours la — et il repond.
        Resultat suivant = lancer("ecrire encore vivant");
        assertThat(suivant.sortie().strip()).isEqualTo("encore vivant");
        assertThat(suivant.codeSortie()).isZero();
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ `-XX:+ExitOnOutOfMemoryError` ne laisse AUCUN message")
    void laMortEstNette() {
        Resultat resultat = lancer("memoire 400");

        // Le diagnostic se lit dans le CODE DE SORTIE, pas dans une pile
        // d'appels : la JVM enfant est terminee a l'instant du manque, sans
        // laisser le `catch` s'executer. C'est une chose a savoir avant de
        // chercher une trace qui n'existe pas.
        assertThat(resultat.codeSortie()).isEqualTo(3);
        assertThat(resultat.erreurs()).isBlank();
    }

    @Test
    @Timeout(60)
    @DisplayName("la sortie est plafonnee avant de traverser HTTP")
    void laSortieEstPlafonnee() {
        Resultat resultat = lancer(("ecrire " + "X".repeat(500) + "\n").repeat(60));

        assertThat(resultat.sortie()).endsWith("(tronque)");
        assertThat(resultat.sortie().length()).isLessThan(11_000);
    }

    // -- la frontiere, et ce qu'elle change --------------------------------

    @Test
    @Timeout(60)
    @DisplayName("⚠️ LA MESURE QUI TRANCHE : le meme script, des deux cotes de la frontiere")
    void lesDeuxCotesDeLaFrontiere() {
        String script = "secret jobportal.cle-api";

        Resultat dansLaJvm = new ExecutionDansLaJvm(nom -> "sk-secret-de-prod")
                .lancer(DemandeExecution.script(script));
        Resultat enBac = lancer(script);

        // A gauche : le code du candidat lit un secret de l'application.
        assertThat(dansLaJvm.codeSortie()).isZero();
        assertThat(dansLaJvm.sortie().strip()).isEqualTo("sk-secret-de-prod");

        // A droite : refus. Et pas seulement parce que la politique
        // refuse — ce processus n'a AUCUN contexte Spring a lire.
        assertThat(enBac.codeSortie()).isEqualTo(77);
        assertThat(enBac.sortie()).isEmpty();
    }

    @Test
    @Timeout(60)
    @DisplayName("le bac a sable refuse le disque et le reseau")
    void lesAutresPortes() {
        assertThat(lancer("lire_fichier \"pom.xml\"").codeSortie()).isEqualTo(77);
        assertThat(lancer("connexion \"127.0.0.1\" 80").codeSortie()).isEqualTo(77);
    }

    @Test
    @Timeout(60)
    @DisplayName("une solution honnete traverse la frontiere sans rien perdre")
    void laSolutionHonnete() {
        Resultat resultat = lancer("""
                ecrire bonjour
                somme 21 21
                ecrire fini
                """);

        assertThat(resultat.reussi()).isTrue();
        assertThat(resultat.sortie().strip().lines())
                .containsExactly("bonjour", "42", "fini");
        assertThat(resultat.millisecondes())
                .as("le cout de la frontiere : un demarrage de JVM")
                .isPositive();
    }

    @Test
    @Timeout(60)
    @DisplayName("le code de sortie du script traverse la frontiere")
    void leCodeDeSortieTraverse() {
        assertThat(lancer("sortie 7").codeSortie()).isEqualTo(7);
        assertThat(lancer("teleporter lune").codeSortie()).isEqualTo(2);
    }
}
