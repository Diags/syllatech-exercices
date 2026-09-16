package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.observabilite.Disjoncteur;
import fr.portail.observabilite.Mesures;
import fr.portail.runner.Resultat;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Ce qu'on regarde en production, et ce qu'on ne doit surtout pas compter.
 *
 * <p>Le compteur specifique d'un bac a sable est le REFUS DE PRIVILEGE : il
 * transforme « quelqu'un a peut-etre essaye » en une serie temporelle sur
 * laquelle on met une alerte. Les autres sont d'exploitation ordinaire.
 */
class ObservabiliteTest {

    private static Resultat ok(long millisecondes) {
        return new Resultat("bonjour", "", 0, false, millisecondes);
    }

    private static Resultat refus() {
        return new Resultat("", "refus de privilege", Mesures.CODE_REFUS,
                            false, 40);
    }

    private static Resultat delai() {
        return new Resultat("", "delai depasse", -1, true, 3_000);
    }

    private static Resultat panne() {
        return new Resultat("", "le bac a sable n'a pas demarre", -2, false, 8);
    }

    private static Resultat planteParLeCandidat() {
        return new Resultat("", "verbe inconnu", 2, false, 90);
    }

    // -- les quatre compteurs ---------------------------------------------

    @Test
    @DisplayName("les quatre compteurs distinguent quatre incidents differents")
    void lesQuatreCompteurs() {
        Mesures mesures = new Mesures(new SimpleMeterRegistry());
        List.of(ok(100), ok(200), refus(), refus(), delai(), panne(),
                planteParLeCandidat()).forEach(mesures::enregistrer);

        assertThat(mesures.executions()).isEqualTo(7);
        assertThat(mesures.refusDePrivilege()).isEqualTo(2);
        assertThat(mesures.delaisDepasses()).isEqualTo(1);
        assertThat(mesures.echecsDeDemarrage()).isEqualTo(1);
    }

    @Test
    @DisplayName("⚠️ un echec du CANDIDAT n'est ni un refus ni une panne")
    void leCandidatFautifNEstPasUnIncident() {
        Mesures mesures = new Mesures(new SimpleMeterRegistry());
        for (int i = 0; i < 50; i++) {
            mesures.enregistrer(planteParLeCandidat());
        }

        // Cinquante solutions fausses : c'est une journee normale de
        // recrutement, pas un incident.
        assertThat(mesures.executions()).isEqualTo(50);
        assertThat(mesures.refusDePrivilege()).isZero();
        assertThat(mesures.echecsDeDemarrage()).isZero();
        assertThat(mesures.delaisDepasses()).isZero();
    }

    @Test
    @DisplayName("le taux de delai depasse est une proportion, pas un compte")
    void leTaux() {
        Mesures mesures = new Mesures(new SimpleMeterRegistry());
        List.of(ok(10), ok(10), ok(10), delai()).forEach(mesures::enregistrer);

        assertThat(mesures.tauxDeDelaiDepasse()).isEqualTo(0.25);
        assertThat(new Mesures(new SimpleMeterRegistry()).tauxDeDelaiDepasse())
                .as("aucune execution : le taux vaut 0, pas NaN")
                .isZero();
    }

    @Test
    @DisplayName("la duree moyenne vient d'un vrai Timer Micrometer")
    void laDureeMoyenne() {
        Mesures mesures = new Mesures(new SimpleMeterRegistry());
        List.of(ok(100), ok(300)).forEach(mesures::enregistrer);

        assertThat(mesures.dureeMoyenneEnMillisecondes())
                .isCloseTo(200.0, org.assertj.core.data.Offset.offset(1.0));
    }

    // -- le disjoncteur ----------------------------------------------------

    @Test
    @DisplayName("au troisieme echec de demarrage, le circuit s'ouvre")
    void leCircuitSOuvre() {
        Disjoncteur disjoncteur = new Disjoncteur(3);
        List<Disjoncteur.Etat> etats = new ArrayList<>();
        List<Resultat> reponses = new ArrayList<>();

        for (int appel = 1; appel <= 5; appel++) {
            reponses.add(disjoncteur.appeler(
                    ObservabiliteTest::panne,
                    () -> new Resultat("", "bac a sable indisponible", -9,
                                       false, 0),
                    r -> r.codeSortie() == -2));
            etats.add(disjoncteur.etat());
        }

        assertThat(etats).containsExactly(
                Disjoncteur.Etat.FERME, Disjoncteur.Etat.FERME,
                Disjoncteur.Etat.OUVERT, Disjoncteur.Etat.OUVERT,
                Disjoncteur.Etat.OUVERT);

        // ⚠️ La mesure : les deux derniers appels n'ont PAS attendu le
        // delai du bac a sable. Ils ont rendu le repli, en zero milliseconde.
        assertThat(reponses.get(4).erreurs()).isEqualTo("bac a sable indisponible");
        assertThat(reponses.get(4).millisecondes()).isZero();
        assertThat(reponses.get(0).millisecondes()).isEqualTo(8);
    }

    @Test
    @DisplayName("⚠️ le disjoncteur NE compte PAS les echecs du candidat")
    void leDisjoncteurIgnoreLeTraficSain() {
        Disjoncteur disjoncteur = new Disjoncteur(3);

        // Vingt solutions fausses d'affilee. Si le predicat de panne etait
        // « codeSortie != 0 », le circuit s'ouvrirait ici — et le service
        // refuserait du trafic parfaitement sain. C'est l'erreur de
        // reglage la plus frequente.
        for (int i = 0; i < 20; i++) {
            disjoncteur.appeler(ObservabiliteTest::planteParLeCandidat,
                                ObservabiliteTest::panne,
                                r -> r.codeSortie() == -2);
        }

        assertThat(disjoncteur.etat()).isEqualTo(Disjoncteur.Etat.FERME);
        assertThat(disjoncteur.echecsConsecutifs()).isZero();
    }

    @Test
    @DisplayName("un succes remet le compteur a zero : ce sont des echecs CONSECUTIFS")
    void leCompteurEstConsecutif() {
        Disjoncteur disjoncteur = new Disjoncteur(3);
        disjoncteur.appeler(ObservabiliteTest::panne, ObservabiliteTest::panne,
                            r -> r.codeSortie() == -2);
        disjoncteur.appeler(ObservabiliteTest::panne, ObservabiliteTest::panne,
                            r -> r.codeSortie() == -2);
        assertThat(disjoncteur.echecsConsecutifs()).isEqualTo(2);

        disjoncteur.appeler(() -> ok(50), ObservabiliteTest::panne,
                            r -> r.codeSortie() == -2);
        assertThat(disjoncteur.echecsConsecutifs()).isZero();
        assertThat(disjoncteur.etat()).isEqualTo(Disjoncteur.Etat.FERME);
    }

    @Test
    @DisplayName("la fenetre demi-ouverte referme le circuit")
    void laFenetreDemiOuverte() {
        Disjoncteur disjoncteur = new Disjoncteur(1);
        disjoncteur.appeler(ObservabiliteTest::panne, ObservabiliteTest::panne,
                            r -> r.codeSortie() == -2);
        assertThat(disjoncteur.etat()).isEqualTo(Disjoncteur.Etat.OUVERT);

        disjoncteur.reessayer();
        assertThat(disjoncteur.etat()).isEqualTo(Disjoncteur.Etat.FERME);
        assertThat(disjoncteur.echecsConsecutifs()).isZero();
    }
}
