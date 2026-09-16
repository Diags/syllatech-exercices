package fr.portail.saga;

import fr.portail.domaine.Messages.AnnulerCandidature;
import fr.portail.domaine.Messages.CandidatureAnnulee;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.CreneauRefuse;
import fr.portail.domaine.Messages.CreneauReserve;
import fr.portail.domaine.Messages.PlanifierEntretien;
import fr.portail.domaine.Messages.ReserverCreneau;
import java.io.Serializable;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import org.axonframework.commandhandling.gateway.CommandGateway;
import org.axonframework.modelling.saga.EndSaga;
import org.axonframework.modelling.saga.SagaEventHandler;
import org.axonframework.modelling.saga.StartSaga;

/**
 * La saga : une transaction distribuée qu'on ne peut pas faire.
 *
 * <p>Déposer une candidature touche deux agrégats — la candidature et
 * l'agenda — donc, en microservices, deux bases. Aucune transaction ACID ne
 * peut les englober. La saga remplace le <em>rollback</em> par une
 * <strong>compensation</strong> : à chaque action correspond une action
 * inverse.
 *
 * <p>Le déroulé, en trois temps :
 *
 * <ol>
 *   <li>{@code CandidatureDeposee} démarre la saga, qui demande un créneau ;</li>
 *   <li>{@code CreneauReserve} → l'entretien est planifié, la saga se
 *       termine ;</li>
 *   <li>{@code CreneauRefuse} → la saga <strong>compense</strong> : elle
 *       annule la candidature, puis se termine.</li>
 * </ol>
 *
 * <p>⚠️ <strong>L'{@code associationProperty} est ce qui relie les
 * événements à la bonne instance.</strong> Elle nomme un <em>accesseur</em>
 * de l'événement — {@code candidatureId()} ici. Se tromper de nom ne produit
 * aucune erreur de compilation : la saga ne reçoit simplement jamais
 * l'événement, et elle reste vivante pour toujours. Le chapitre 5 le mesure.
 *
 * <p>⚠️ Cette classe garde une trace de ce qu'elle a fait ({@link #journal})
 * pour que les chapitres l'impriment. Une vraie saga n'a pas de champ
 * statique : son état est sérialisé par Axon entre deux événements.
 */
public class SagaDeCandidature implements Serializable {

    /** Ce que les sagas ont fait, pour que les chapitres puissent le lire. */
    private static final List<String> JOURNAL = new CopyOnWriteArrayList<>();

    public static List<String> journal() {
        return List.copyOf(JOURNAL);
    }

    public static void viderLeJournal() {
        JOURNAL.clear();
    }

    /**
     * La passerelle de commandes, injectée par Axon au chargement.
     *
     * <p>⚠️ <strong>{@code @Inject} n'est pas décoratif.</strong> Axon
     * n'injecte que les champs portant {@code jakarta.inject.Inject},
     * {@code javax.inject.Inject} ou l'{@code @Autowired} de Spring. Sans
     * l'une d'elles, le champ reste {@code null} et la saga échoue au
     * premier événement — dans un <em>autre</em> fil d'exécution, donc avec
     * une trace qui n'arrive jamais jusqu'à l'appelant.
     *
     * <p>{@code transient} parce qu'une saga est <em>sérialisée</em> entre
     * deux événements : son état est persisté, et une passerelle ne se
     * sérialise pas.
     */
    @jakarta.inject.Inject
    private transient CommandGateway passerelle;

    private String candidatureId;

    @StartSaga
    @SagaEventHandler(associationProperty = "candidatureId")
    public void on(CandidatureDeposee fait) {
        this.candidatureId = fait.candidatureId();
        JOURNAL.add("saga demarree pour " + fait.candidatureId());
        // ⚠️ Les evenements de l'AGENDA portent eux aussi un
        // `candidatureId()` — ce n'est pas un hasard, c'est ce qui permet a
        // cette saga de les suivre sans rien declarer de plus. Si l'agenda
        // ne publiait qu'un `agendaId`, il faudrait appeler
        // `SagaLifecycle.associateWith("agendaId", ...)` ici, sans quoi la
        // saga ne verrait jamais la reponse et resterait vivante pour
        // toujours.
        JOURNAL.add("-> ReserverCreneau");
        passerelle.sendAndWait(new ReserverCreneau("agenda-2026",
                fait.candidatureId()));
    }

    @SagaEventHandler(associationProperty = "candidatureId")
    public void on(CreneauReserve fait) {
        JOURNAL.add("creneau obtenu : " + fait.creneau());
        JOURNAL.add("-> PlanifierEntretien");
        passerelle.sendAndWait(new PlanifierEntretien(candidatureId,
                fait.creneau()));
    }

    /**
     * La compensation : on défait ce qui a été fait.
     *
     * <p>Aucun <em>rollback</em> n'est possible — la candidature est déjà
     * écrite dans son propre journal. On envoie donc l'action inverse, et
     * c'est elle qui produit le fait « annulée ».
     */
    @SagaEventHandler(associationProperty = "candidatureId")
    public void on(CreneauRefuse fait) {
        JOURNAL.add("creneau REFUSE : " + fait.motif());
        // >>> depart: compenser — envoyer l'action inverse, puisqu'aucun rollback n'est possible
        //     JOURNAL.add("-> (rien : la candidature reste deposee)");
        JOURNAL.add("-> AnnulerCandidature (compensation)");
        passerelle.sendAndWait(new AnnulerCandidature(candidatureId,
                "aucun creneau disponible"));
        // <<<
    }

    @EndSaga
    @SagaEventHandler(associationProperty = "candidatureId")
    public void on(CandidatureAnnulee fait) {
        JOURNAL.add("saga terminee (compensee) pour " + fait.candidatureId());
    }

    @EndSaga
    @SagaEventHandler(associationProperty = "candidatureId")
    public void on(fr.portail.domaine.Messages.EntretienPlanifie fait) {
        JOURNAL.add("saga terminee (succes) pour " + fait.candidatureId());
    }
}
