package fr.portail.domaine;

import static org.axonframework.modelling.command.AggregateLifecycle.apply;

import fr.portail.domaine.Messages.CreneauRefuse;
import fr.portail.domaine.Messages.CreneauRelache;
import fr.portail.domaine.Messages.CreneauReserve;
import fr.portail.domaine.Messages.RelacherCreneau;
import fr.portail.domaine.Messages.ReserverCreneau;
import java.util.ArrayList;
import java.util.List;
import org.axonframework.commandhandling.CommandHandler;
import org.axonframework.eventsourcing.EventSourcingHandler;
import org.axonframework.modelling.command.AggregateCreationPolicy;
import org.axonframework.modelling.command.AggregateIdentifier;
import org.axonframework.modelling.command.CreationPolicy;

/**
 * Le second agrégat : l'agenda des entretiens, et ses créneaux.
 *
 * <p>Il existe pour une raison précise : <strong>une saga a besoin de deux
 * agrégats</strong>. Tant qu'il n'y en a qu'un, la cohérence tient dans une
 * seule transaction et le pattern Saga ne sert à rien. Dès qu'il y en a deux —
 * et, en microservices, deux bases —, la transaction distribuée devient
 * impossible et la compensation devient la seule issue.
 *
 * <p>⚠️ Notez ce que cet agrégat refuse : une réservation de trop. C'est un
 * invariant, donc il vit ici, et pas dans une projection. Une projection est
 * en retard par construction : deux candidats pourraient y lire « il reste un
 * créneau » en même temps.
 */
public class Agenda {

    /** Le nombre de créneaux ouverts, volontairement petit. */
    public static final int CRENEAUX = 2;

    @AggregateIdentifier
    private String agendaId;

    private final List<String> reserves = new ArrayList<>();

    protected Agenda() {
    }

    /**
     * L'agenda se crée tout seul, à la première réservation.
     *
     * <p>⚠️ <strong>{@code CREATE_IF_MISSING} résout un vrai problème.</strong>
     * Un agrégat « registre » comme celui-ci n'a pas de commande de création
     * naturelle : personne ne « crée l'agenda 2026 », il existe parce qu'on
     * s'en sert. Sans cette politique, la première {@code ReserverCreneau}
     * échoue en {@code AggregateNotFoundException} — et l'erreur arrive dans
     * le fil de la saga, donc loin de l'appelant, avec une trace que
     * personne ne lit.
     *
     * <p>C'est la solution d'Axon 4.3+ ; avant, il fallait un constructeur
     * annoté {@code @CommandHandler} et une commande d'ouverture rien que
     * pour cela.
     */
    @CommandHandler
    @CreationPolicy(AggregateCreationPolicy.CREATE_IF_MISSING)
    public void traiter(ReserverCreneau commande) {
        this.agendaId = commande.agendaId();
        if (reserves.contains(commande.candidatureId())) {
            // Idempotence : la meme reservation deux fois n'en fait qu'une.
            return;
        }
        // TODO : publier un EVENEMENT de refus quand il n'y a plus de creneau — pas une exception
        // une exception ne serait vue que de l'appelant : la saga resterait bloquee
        apply(new CreneauReserve(agendaId, commande.candidatureId(),
                "creneau-" + (reserves.size() + 1)));
    }

    @CommandHandler
    public void traiter(RelacherCreneau commande) {
        if (!reserves.contains(commande.candidatureId())) {
            return;
        }
        apply(new CreneauRelache(agendaId, commande.candidatureId()));
    }

    @EventSourcingHandler
    void on(CreneauReserve fait) {
        this.agendaId = fait.agendaId();
        reserves.add(fait.candidatureId());
    }

    @EventSourcingHandler
    void on(CreneauRefuse fait) {
        this.agendaId = fait.agendaId();
    }

    @EventSourcingHandler
    void on(CreneauRelache fait) {
        this.agendaId = fait.agendaId();
        reserves.remove(fait.candidatureId());
    }

    public int reserves() {
        return reserves.size();
    }
}
