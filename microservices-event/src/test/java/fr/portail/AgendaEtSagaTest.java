package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.commun.Banc;
import fr.portail.domaine.Agenda;
import fr.portail.domaine.Messages.AnnulerCandidature;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.CreneauRefuse;
import fr.portail.domaine.Messages.CreneauReserve;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.PlanifierEntretien;
import fr.portail.domaine.Messages.RelacherCreneau;
import fr.portail.domaine.Messages.ReserverCreneau;
import fr.portail.saga.SagaDeCandidature;
import org.axonframework.test.aggregate.AggregateTestFixture;
import org.axonframework.test.saga.SagaTestFixture;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * L'agenda et la saga : la coordination, et sa compensation.
 *
 * <p>La {@code SagaTestFixture} suit la même logique que celle des agrégats,
 * inversée : on décrit des <em>événements publiés</em>, et on affirme les
 * <em>commandes envoyées</em>. C'est exactement ce que le cours résume par
 * « on vérifie qu'un événement entrant déclenche bien les bonnes commandes
 * sortantes, compensations comprises ».
 */
class AgendaEtSagaTest {

    @Test
    @DisplayName("l'agenda se cree a la premiere reservation")
    void lAgendaSeCree() {
        new AggregateTestFixture<>(Agenda.class)
                .givenNoPriorActivity()
                .when(new ReserverCreneau("agenda-2026", "c-1"))
                .expectEvents(new CreneauReserve("agenda-2026", "c-1",
                        "creneau-1"));
    }

    @Test
    @DisplayName("reserver deux fois pour le meme candidat ne fait rien de plus")
    void laReservationEstIdempotente() {
        new AggregateTestFixture<>(Agenda.class)
                .given(new CreneauReserve("agenda-2026", "c-1", "creneau-1"))
                .when(new ReserverCreneau("agenda-2026", "c-1"))
                .expectSuccessfulHandlerExecution()
                .expectNoEvents();
    }

    /**
     * ⚠️ Le refus est un ÉVÉNEMENT, pas une exception.
     *
     * <p>Une exception ne serait vue que de l'appelant direct — et la saga,
     * qui attend une réponse, resterait vivante pour toujours.
     */
    @Test
    @DisplayName("l'agenda plein publie un refus, et ne leve pas d'exception")
    void leRefusEstUnEvenement() {
        new AggregateTestFixture<>(Agenda.class)
                .given(new CreneauReserve("agenda-2026", "c-1", "creneau-1"),
                        new CreneauReserve("agenda-2026", "c-2", "creneau-2"))
                .when(new ReserverCreneau("agenda-2026", "c-3"))
                .expectSuccessfulHandlerExecution()
                .expectEvents(new CreneauRefuse("agenda-2026", "c-3",
                        "plus aucun creneau disponible"));
    }

    @Test
    @DisplayName("relacher un creneau non reserve ne produit rien")
    void relacherCeQuiNExistePasNeFaitRien() {
        new AggregateTestFixture<>(Agenda.class)
                .given(new CreneauReserve("agenda-2026", "c-1", "creneau-1"))
                .when(new RelacherCreneau("agenda-2026", "c-2"))
                .expectSuccessfulHandlerExecution()
                .expectNoEvents();
    }

    @Test
    @DisplayName("la saga demande un creneau des qu'une candidature est deposee")
    void laSagaDemandeUnCreneau() {
        var fixture = new SagaTestFixture<>(SagaDeCandidature.class);
        fixture.givenNoPriorActivity()
                .whenAggregate("c-1")
                .publishes(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .expectActiveSagas(1)
                .expectDispatchedCommands(new ReserverCreneau("agenda-2026",
                        "c-1"));
    }

    @Test
    @DisplayName("le creneau obtenu fait planifier l'entretien")
    void leCreneauObtenuPlanifie() {
        var fixture = new SagaTestFixture<>(SagaDeCandidature.class);
        fixture.givenAggregate("c-1")
                .published(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .whenAggregate("c-1")
                .publishes(new CreneauReserve("agenda-2026", "c-1",
                        "creneau-1"))
                .expectDispatchedCommands(new PlanifierEntretien("c-1",
                        "creneau-1"));
    }

    /**
     * ⚠️ La compensation, figée.
     *
     * <p>Aucun <em>rollback</em> n'est possible : la candidature est déjà
     * écrite. La saga envoie donc l'action inverse, et c'est elle qui produit
     * le fait « annulée ».
     */
    @Test
    @DisplayName("un creneau refuse declenche la compensation")
    void leRefusDeclencheLaCompensation() {
        var fixture = new SagaTestFixture<>(SagaDeCandidature.class);
        fixture.givenAggregate("c-1")
                .published(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .whenAggregate("c-1")
                .publishes(new CreneauRefuse("agenda-2026", "c-1",
                        "plus aucun creneau disponible"))
                .expectDispatchedCommands(new AnnulerCandidature("c-1",
                        "aucun creneau disponible"));
    }

    @Test
    @DisplayName("bout en bout : trois candidatures, deux creneaux, une annulee")
    void boutEnBout() {
        try (var banc = Banc.demarrerAvecSaga()) {
            SagaDeCandidature.viderLeJournal();
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-2", "Karim", "OFF-021"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-3", "Lea", "OFF-033"));

            assertThat(banc.vue().parId("c-1"))
                    .as("la projection doit alimenter le modele de lecture")
                    .isNotNull();
            assertThat(banc.vue().parId("c-1").statut()).isEqualTo("ENTRETIEN");
            assertThat(banc.vue().parId("c-2").statut()).isEqualTo("ENTRETIEN");
            assertThat(banc.vue().parId("c-3").statut())
                    .as("la troisieme n'a pas eu de creneau : elle est compensee")
                    .isEqualTo("ANNULEE");
            assertThat(SagaDeCandidature.journal())
                    .contains("-> AnnulerCandidature (compensation)");
        }
    }
}
