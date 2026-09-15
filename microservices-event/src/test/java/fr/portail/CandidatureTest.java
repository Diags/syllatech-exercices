package fr.portail;

import fr.portail.domaine.Candidature;
import fr.portail.domaine.Messages.AnnulerCandidature;
import fr.portail.domaine.Messages.CandidatureAnnulee;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DecisionPrononcee;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.EntretienPlanifie;
import fr.portail.domaine.Messages.PlanifierEntretien;
import org.axonframework.test.aggregate.AggregateTestFixture;
import org.axonframework.test.aggregate.FixtureConfiguration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * L'agrégat, testé comme une fonction pure.
 *
 * <p>Aucune base, aucun bus, aucun conteneur : le triplet
 * <em>given / when / expect</em> décrit un scénario métier et le vérifie en
 * quelques millisecondes. C'est ce que le chapitre 6 du cours annonce, et
 * c'est ce que l'event sourcing rend possible — un agrégat n'est rien d'autre
 * qu'une fonction du passé vers des faits.
 */
class CandidatureTest {

    private FixtureConfiguration<Candidature> fixture;

    @BeforeEach
    void preparer() {
        fixture = new AggregateTestFixture<>(Candidature.class);
    }

    @Test
    @DisplayName("deposer une candidature produit le fait correspondant")
    void leDepotProduitUnFait() {
        fixture.givenNoPriorActivity()
                .when(new DeposerCandidature("c-1", "Awa", "OFF-014"))
                .expectSuccessfulHandlerExecution()
                .expectEvents(new CandidatureDeposee("c-1", "Awa", "OFF-014"));
    }

    @Test
    @DisplayName("une candidature sans candidat est refusee, et n'ecrit rien")
    void leDepotSansCandidatEstRefuse() {
        fixture.givenNoPriorActivity()
                .when(new DeposerCandidature("c-1", "  ", "OFF-014"))
                .expectException(IllegalArgumentException.class)
                .expectNoEvents();
    }

    @Test
    @DisplayName("planifier un entretien apres un depot")
    void lEntretienSePlanifie() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .when(new PlanifierEntretien("c-1", "mardi 14h"))
                .expectEvents(new EntretienPlanifie("c-1", "mardi 14h"));
    }

    /**
     * ⚠️ L'invariant qui justifie l'existence de l'agrégat.
     *
     * <p>Une projection ne pourrait pas le tenir : elle est en retard par
     * construction, et deux lecteurs y verraient le même état périmé au même
     * instant.
     */
    @Test
    @DisplayName("decider sans entretien planifie est refuse")
    void pasDeDecisionSansEntretien() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .when(new Decider("c-1", true, "excellent profil"))
                .expectException(IllegalStateException.class)
                .expectNoEvents();
    }

    @Test
    @DisplayName("decider apres un entretien produit la decision")
    void laDecisionApresEntretien() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                        new EntretienPlanifie("c-1", "mardi 14h"))
                .when(new Decider("c-1", true, "excellent profil"))
                .expectEvents(new DecisionPrononcee("c-1", true,
                        "excellent profil"));
    }

    @Test
    @DisplayName("on ne decide pas deux fois")
    void uneSeuleDecision() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                        new EntretienPlanifie("c-1", "mardi 14h"),
                        new DecisionPrononcee("c-1", true, "retenue"))
                .when(new Decider("c-1", false, "finalement non"))
                .expectException(IllegalStateException.class);
    }

    @Test
    @DisplayName("on ne planifie pas d'entretien sur une candidature close")
    void pasDEntretienApresCloture() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                        new CandidatureAnnulee("c-1", "plus de creneau"))
                .when(new PlanifierEntretien("c-1", "mardi 14h"))
                .expectException(IllegalStateException.class);
    }

    /**
     * ⚠️ L'idempotence de la compensation, figée.
     *
     * <p>Un bus en <em>at-least-once</em> rejoue : annuler deux fois doit
     * produire un seul fait, sinon la saga écrit deux annulations pour une
     * candidature.
     */
    @Test
    @DisplayName("annuler une candidature deja annulee ne produit rien")
    void lAnnulationEstIdempotente() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                        new CandidatureAnnulee("c-1", "plus de creneau"))
                .when(new AnnulerCandidature("c-1", "plus de creneau"))
                .expectSuccessfulHandlerExecution()
                .expectNoEvents();
    }

    @Test
    @DisplayName("annuler une candidature ouverte produit le fait")
    void lAnnulationProduitUnFait() {
        fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .when(new AnnulerCandidature("c-1", "plus de creneau"))
                .expectEvents(new CandidatureAnnulee("c-1", "plus de creneau"));
    }
}
