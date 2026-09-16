package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.commun.Banc;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.PlanifierEntretien;
import fr.portail.projection.VueDesCandidatures;
import java.util.ArrayList;
import java.util.List;
import org.axonframework.eventhandling.DomainEventMessage;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * CQRS et event sourcing : le journal, les projections, les snapshots.
 *
 * <p>Ces tests démarrent un vrai banc Axon — bus, magasin, projections — et
 * vérifient les propriétés que les chapitres 3 et 4 impriment : un modèle de
 * lecture se jette et se reconstruit, un agrégat se recalcule par rejeu, et un
 * snapshot raccourcit ce rejeu sans effacer un seul événement.
 */
class CqrsEtEventSourcingTest {

    @Test
    @DisplayName("une commande refusee n'ecrit rien dans le journal")
    void leRefusNEcritRien() {
        try (var banc = Banc.demarrer()) {
            try {
                banc.passerelle().sendAndWait(
                        new DeposerCandidature("c-1", " ", "OFF-014"));
            } catch (RuntimeException attendue) {
                // c'est le cas mesure
            }
            assertThat(journal(banc)).isEmpty();
        }
    }

    @Test
    @DisplayName("chaque agregat a son propre flux d'evenements")
    void chaqueAgregatSonFlux() {
        try (var banc = Banc.demarrer()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-2", "Karim", "OFF-021"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-1", "mardi 14h"));

            assertThat(flux(banc, "c-1")).hasSize(2);
            assertThat(flux(banc, "c-2")).hasSize(1);
            assertThat(journal(banc)).hasSize(3);
        }
    }

    @Test
    @DisplayName("les deux projections se nourrissent du meme journal")
    void deuxProjectionsUnJournal() {
        try (var banc = Banc.demarrer()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-2", "Karim", "OFF-014"));

            assertThat(banc.vue().taille()).isEqualTo(2);
            assertThat(banc.compteur().compteIdempotent("OFF-014")).isEqualTo(2);
        }
    }

    /**
     * ⚠️ La propriété qui rend CQRS confortable.
     *
     * <p>Un modèle de lecture n'est jamais une donnée de référence : c'est un
     * cache, jetable et reconstructible. C'est ce qui permet de lui changer
     * de forme sans migration.
     */
    @Test
    @DisplayName("une projection jetee se reconstruit a l'identique")
    void laProjectionSeReconstruit() {
        try (var banc = Banc.demarrer()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-1", "mardi 14h"));
            banc.passerelle().sendAndWait(
                    new Decider("c-1", true, "excellent profil"));
            var avant = banc.vue().toutes();

            banc.vue().vider();
            assertThat(banc.vue().taille()).isZero();
            rejouer(banc, banc.vue());

            assertThat(banc.vue().toutes()).isEqualTo(avant);
            assertThat(banc.vue().parId("c-1"))
                    .as("la projection doit alimenter le modele de lecture")
                    .isNotNull();
            assertThat(banc.vue().parId("c-1").statut()).isEqualTo("RETENUE");
        }
    }

    @Test
    @DisplayName("une projection creee apres coup connait tout le passe")
    void uneProjectionNeuveConnaitLePasse() {
        try (var banc = Banc.demarrer()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-1", "mardi 14h"));

            var neuve = new VueDesCandidatures();
            assertThat(neuve.taille()).isZero();
            rejouer(banc, neuve);

            assertThat(neuve.parId("c-1"))
                    .as("la projection doit alimenter le modele de lecture")
                    .isNotNull();
            assertThat(neuve.parId("c-1").statut()).isEqualTo("ENTRETIEN");
            assertThat(neuve.parId("c-1").creneau()).isEqualTo("mardi 14h");
        }
    }

    @Test
    @DisplayName("un snapshot raccourcit le rejeu sans effacer d'evenement")
    void leSnapshotRaccourcitLeRejeu() {
        try (var banc = Banc.demarrer(3)) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            for (int tour = 1; tour <= 6; tour++) {
                banc.passerelle().sendAndWait(
                        new PlanifierEntretien("c-1", "creneau " + tour));
            }
            attendreUnSnapshot(banc, "c-1");

            assertThat(flux(banc, "c-1"))
                    .as("le journal garde TOUS ses evenements")
                    .hasSize(7);
            assertThat(banc.moteur().readSnapshot("c-1"))
                    .as("un snapshot a bien ete pris")
                    .isPresent();
            long depart = banc.moteur().readSnapshot("c-1")
                    .map(photo -> photo.getSequenceNumber() + 1).orElse(0L);
            assertThat(depart)
                    .as("le rejeu repart apres la photo")
                    .isGreaterThan(1);
        }
    }

    @Test
    @DisplayName("sans seuil atteint, aucun snapshot n'est pris")
    void pasDeSnapshotSansSeuil() {
        try (var banc = Banc.demarrer(50)) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-1", "mardi 14h"));

            assertThat(banc.moteur().readSnapshot("c-1")).isEmpty();
        }
    }

    @Test
    @DisplayName("les evenements portent un traceId commun")
    void leTraceIdEstPropage() {
        try (var banc = Banc.demarrerAvecSaga()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));

            var traces = journal(banc).stream()
                    .map(message -> message.getMetaData().get("traceId"))
                    .distinct().toList();
            assertThat(journal(banc)).hasSizeGreaterThan(1);
            assertThat(traces)
                    .as("une seule commande entrante : un seul traceId")
                    .hasSize(1);
        }
    }

    private static List<DomainEventMessage<?>> journal(Banc banc) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(null, false).forEach(message -> {
            if (message instanceof DomainEventMessage<?> domaine) {
                tout.add(domaine);
            }
        });
        return tout;
    }

    private static List<DomainEventMessage<?>> flux(Banc banc, String id) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(id, 0).asStream().forEach(tout::add);
        return tout;
    }

    private static void rejouer(Banc banc, VueDesCandidatures vue) {
        for (var message : journal(banc)) {
            switch (message.getPayload()) {
                case CandidatureDeposee depot -> vue.on(depot);
                case fr.portail.domaine.Messages.EntretienPlanifie planifie ->
                        vue.on(planifie);
                case fr.portail.domaine.Messages.DecisionPrononcee decision ->
                        vue.on(decision);
                case fr.portail.domaine.Messages.CandidatureAnnulee annulation ->
                        vue.on(annulation);
                default -> { }
            }
        }
    }

    private static void attendreUnSnapshot(Banc banc, String id) {
        for (int essai = 0; essai < 50; essai++) {
            if (banc.moteur().readSnapshot(id).isPresent()) {
                return;
            }
            try {
                Thread.sleep(20);
            } catch (InterruptedException interrompu) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
}
