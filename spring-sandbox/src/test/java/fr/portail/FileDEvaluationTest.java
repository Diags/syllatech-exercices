package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.application.FileDEvaluation;
import fr.portail.application.Note;
import fr.portail.application.ServiceEvaluation;
import fr.portail.commun.Banc;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

/**
 * La file d'evaluation, contre un VRAI runner.
 *
 * <p>⚠️ Ce que la file apporte n'est pas le confort du candidat : c'est la
 * BORNE sur le nombre d'evaluations simultanees. Le bac a sable protege de
 * ce qu'UNE soumission fait ; la file protege de leur NOMBRE.
 */
class FileDEvaluationTest {

    private static final List<String> ATTENDUS =
            List.of("bonjour", "42", "fini");

    private static final String JUSTE = """
            ecrire bonjour
            somme 21 21
            ecrire fini
            """;

    private static final String QUI_BOUCLE = """
            ecrire bonjour
            boucle
            """;

    @Test
    @Timeout(180)
    @DisplayName("⚠️ LA MESURE : accepter coute des millisecondes, evaluer coute le delai")
    void accepterEstImmediat() throws Exception {
        try (Banc banc = Banc.durci(4, 48)) {
            ServiceEvaluation service =
                    new ServiceEvaluation(banc.url(), banc.mesures());

            long depart = System.nanoTime();
            service.evaluer(1, QUI_BOUCLE, ATTENDUS);
            long bloquant = (System.nanoTime() - depart) / 1_000_000;

            try (FileDEvaluation file = new FileDEvaluation(service, 2)) {
                long depuis = System.nanoTime();
                FileDEvaluation.Suivi suivi = file.soumettre(2, QUI_BOUCLE, ATTENDUS);
                long enFile = (System.nanoTime() - depuis) / 1_000_000;

                assertThat(suivi.etat()).isEqualTo(FileDEvaluation.Etat.EN_ATTENTE);
                assertThat(suivi.note()).isNull();
                assertThat(bloquant)
                        .as("l'appel bloquant paie le delai dur en entier")
                        .isGreaterThan(3_000);
                assertThat(enFile)
                        .as("la mise en file rend la main tout de suite")
                        .isLessThan(500);

                assertThat(file.attendreLaFin(60)).isTrue();
                FileDEvaluation.Suivi termine = file.consulter(2);
                assertThat(termine.etat()).isEqualTo(FileDEvaluation.Etat.TERMINEE);
                assertThat(termine.note().ecartee()).isTrue();
                assertThat(termine.note().mention()).isEqualTo("ecartee — delai depasse");
            }
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("la file traite toutes les soumissions acceptees, sans en perdre")
    void aucuneSoumissionPerdue() throws Exception {
        try (Banc banc = Banc.durci(4, 48)) {
            ServiceEvaluation service =
                    new ServiceEvaluation(banc.url(), banc.mesures());

            try (FileDEvaluation file = new FileDEvaluation(service, 2)) {
                for (long candidature = 1; candidature <= 4; candidature++) {
                    file.soumettre(candidature, JUSTE, ATTENDUS);
                }
                assertThat(file.acceptees()).isEqualTo(4);

                assertThat(file.attendreLaFin(120)).isTrue();
                for (long candidature = 1; candidature <= 4; candidature++) {
                    FileDEvaluation.Suivi suivi = file.consulter(candidature);
                    assertThat(suivi.etat())
                            .isEqualTo(FileDEvaluation.Etat.TERMINEE);
                    Note note = suivi.note();
                    assertThat(note.admise())
                            .as("candidature " + candidature + " : " + note.mention())
                            .isTrue();
                }
            }

            // ⚠️ Et la borne se lit dans les mesures : quatre soumissions,
            // quatre executions — mais jamais plus de DEUX processus a la
            // fois, parce que la file a deux ouvriers.
            assertThat(banc.mesures().executions()).isEqualTo(4);
        }
    }

    @Test
    @Timeout(180)
    @DisplayName("une candidature inconnue n'existe pas, elle ne s'invente pas")
    void laCandidatureInconnue() throws Exception {
        try (Banc banc = Banc.durci(4, 48)) {
            ServiceEvaluation service = new ServiceEvaluation(banc.url(), null);
            try (FileDEvaluation file = new FileDEvaluation(service, 1)) {
                assertThat(file.consulter(999)).isNull();
                assertThat(file.acceptees()).isZero();
            }
        }
    }
}
