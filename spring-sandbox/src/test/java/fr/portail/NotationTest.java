package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.application.Note;
import fr.portail.application.ServiceEvaluation;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * La notation — et surtout ce qu'elle refuse de faire.
 *
 * <p>⚠️ Tout le travail du bac a sable s'annule sur une ligne de commodite :
 * evaluer la sortie du candidat « pour etre souple » lui rend l'execution
 * qu'on venait de lui retirer, et cette fois DANS le processus qui detient
 * la base et les secrets. Ces tests fixent cette limite.
 */
class NotationTest {

    private static final List<String> ATTENDUS =
            List.of("bonjour", "42", "fini");

    @Test
    @DisplayName("la comparaison est positionnelle, ligne a ligne")
    void laComparaisonEstPositionnelle() {
        assertThat(ServiceEvaluation.comparer("bonjour\n42\nfini\n", ATTENDUS))
                .isEqualTo(3);
        assertThat(ServiceEvaluation.comparer("bonjour\n41\nfini\n", ATTENDUS))
                .isEqualTo(2);
        assertThat(ServiceEvaluation.comparer("", ATTENDUS)).isZero();
    }

    @Test
    @DisplayName("l'ordre compte : les bonnes lignes au mauvais rang ne valent rien")
    void lOrdreCompte() {
        assertThat(ServiceEvaluation.comparer("fini\n42\nbonjour\n", ATTENDUS))
                .as("seul « 42 » est au bon rang")
                .isEqualTo(1);
    }

    @Test
    @DisplayName("les espaces de bord sont pardonnes, le reste non")
    void lesEspacesDeBord() {
        assertThat(ServiceEvaluation.comparer("  bonjour \n 42\nfini", ATTENDUS))
                .isEqualTo(3);
        assertThat(ServiceEvaluation.comparer("Bonjour\n42\nfini", ATTENDUS))
                .as("la casse n'est pas pardonnee")
                .isEqualTo(2);
    }

    @Test
    @DisplayName("⚠️ LA MESURE : la comparaison N'EVALUE RIEN")
    void laComparaisonNEvaluePas() {
        // Un candidat qui rend l'EXPRESSION au lieu du RESULTAT echoue, et
        // c'est voulu. La tentation serait d'« etre souple » et d'evaluer
        // « 21+21 » pour le compter juste.
        assertThat(ServiceEvaluation.comparer("bonjour\n21+21\nfini", ATTENDUS))
                .as("« 21+21 » n'est pas « 42 » : rien n'est evalue")
                .isEqualTo(2);

        // Et la charge qui explique pourquoi : si la notation passait la
        // sortie a un moteur d'expression ou de modeles, CECI s'executerait
        // dans la JVM de l'application.
        String charge = "${T(java.lang.Runtime).getRuntime().exec('id')}";
        assertThat(ServiceEvaluation.comparer("bonjour\n" + charge + "\nfini",
                                              ATTENDUS))
                .as("la charge est comparee comme une chaine, et c'est tout")
                .isEqualTo(2);
    }

    @Test
    @DisplayName("une sortie enorme est plafonnee avant d'etre comparee")
    void laSortieEnormeEstPlafonnee() {
        String enorme = "bonjour\n42\nfini\n" + "A".repeat(200_000);
        assertThat(ServiceEvaluation.comparer(enorme, ATTENDUS)).isEqualTo(3);
    }

    @Test
    @DisplayName("plus de lignes que d'assertions ne donne pas plus de points")
    void pasDePointsEnTrop() {
        String bavard = "bonjour\n42\nfini\nbonjour\n42\nfini";
        assertThat(ServiceEvaluation.comparer(bavard, ATTENDUS))
                .isEqualTo(ATTENDUS.size());
    }

    // -- la note, et la decision metier -----------------------------------

    @Test
    @DisplayName("une solution juste est admise")
    void laSolutionJuste() {
        Note note = new Note(1, 3, 3, false, false);
        assertThat(note.admise()).isTrue();
        assertThat(note.ecartee()).isFalse();
        assertThat(note.mention()).isEqualTo("3/3");
    }

    @Test
    @DisplayName("⚠️ une tentative d'acces est ECARTEE, pas notee — meme avec des points")
    void laTentativeDAccesEstEcartee() {
        // Le candidat a bien ecrit « bonjour » avant de tenter de lire
        // /etc/passwd. La comparaison a donc trouve une ligne juste. Ce
        // n'est pas une note : c'est une decision metier, et elle se prend
        // dans l'application — le runner, lui, ne rend qu'un code 77.
        Note note = new Note(1, 1, 3, false, true);

        assertThat(note.ecartee()).isTrue();
        assertThat(note.admise()).isFalse();
        assertThat(note.mention()).isEqualTo("ecartee — tentative d'acces refusee");
    }

    @Test
    @DisplayName("un delai depasse ecarte aussi, et le dit autrement")
    void leDelaiDepasseEcarte() {
        Note note = new Note(1, 3, 3, true, false);
        assertThat(note.ecartee()).isTrue();
        assertThat(note.admise())
                .as("meme avec 3/3 : on ne sait pas ce que la boucle cachait")
                .isFalse();
        assertThat(note.mention()).isEqualTo("ecartee — delai depasse");
    }

    @Test
    @DisplayName("le refus l'emporte sur le delai dans la mention")
    void leRefusLEmporte() {
        assertThat(new Note(1, 0, 3, true, true).mention())
                .isEqualTo("ecartee — tentative d'acces refusee");
    }

    @Test
    @DisplayName("une solution incomplete est notee, pas ecartee")
    void laSolutionIncomplete() {
        Note note = new Note(1, 2, 3, false, false);
        assertThat(note.ecartee()).isFalse();
        assertThat(note.admise()).isFalse();
        assertThat(note.mention()).isEqualTo("2/3");
    }
}
