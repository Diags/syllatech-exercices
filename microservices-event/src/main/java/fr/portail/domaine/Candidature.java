package fr.portail.domaine;

import static org.axonframework.modelling.command.AggregateLifecycle.apply;

import fr.portail.domaine.Messages.AnnulerCandidature;
import fr.portail.domaine.Messages.CandidatureAnnulee;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DecisionPrononcee;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.EntretienPlanifie;
import fr.portail.domaine.Messages.PlanifierEntretien;
import org.axonframework.commandhandling.CommandHandler;
import org.axonframework.eventsourcing.EventSourcingHandler;
import org.axonframework.modelling.command.AggregateIdentifier;

/**
 * L'agrégat : la frontière de cohérence du portail.
 *
 * <p>Deux rôles, et il ne faut jamais les mélanger :
 *
 * <ul>
 *   <li>un {@code @CommandHandler} <strong>décide</strong>. Il lit l'état
 *       courant, vérifie les invariants, et <em>émet</em> un événement — ou
 *       refuse. C'est le seul endroit où l'on a le droit de dire non.</li>
 *   <li>un {@code @EventSourcingHandler} <strong>applique</strong>. Il ne
 *       valide rien, ne refuse rien, ne lève jamais : l'événement s'est déjà
 *       produit. Il met à jour l'état, un point c'est tout.</li>
 * </ul>
 *
 * <p>⚠️ <strong>Pourquoi un {@code EventSourcingHandler} ne doit jamais
 * valider.</strong> Il est rejoué à chaque chargement de l'agrégat, sur des
 * événements vieux de deux ans. Une règle métier ajoutée aujourd'hui y ferait
 * échouer le rejeu d'une candidature parfaitement valide à l'époque — et
 * l'agrégat deviendrait impossible à charger. Les règles vivent dans les
 * command handlers, jamais dans les event handlers.
 *
 * <p>⚠️ <strong>Le constructeur sans argument est obligatoire.</strong> Axon
 * instancie l'agrégat vide, puis rejoue ses événements. Le supprimer produit
 * une erreur à l'exécution, au premier chargement.
 */
public class Candidature {

    @AggregateIdentifier
    private String candidatureId;

    private String candidat;
    private String offre;
    private boolean entretienPlanifie;
    private boolean close;

    /** Exigé par Axon : l'agrégat est créé vide, puis rejoué. */
    protected Candidature() {
    }

    @CommandHandler
    public Candidature(DeposerCandidature commande) {
        if (commande.candidat() == null || commande.candidat().isBlank()) {
            throw new IllegalArgumentException(
                    "une candidature sans candidat n'a pas de sens");
        }
        apply(new CandidatureDeposee(commande.candidatureId(),
                commande.candidat(), commande.offre()));
    }

    @CommandHandler
    public void traiter(PlanifierEntretien commande) {
        // TODO : refuser de planifier un entretien sur une candidature deja close
        // sans cette regle, on planifie un entretien sur une candidature annulee
        apply(new EntretienPlanifie(candidatureId, commande.creneau()));
    }

    @CommandHandler
    public void traiter(Decider commande) {
        if (close) {
            throw new IllegalStateException("decision deja prononcee");
        }
        // TODO : refuser de decider tant qu'aucun entretien n'a ete planifie
        // c'est l'invariant qui justifie l'existence de cet agregat
        apply(new DecisionPrononcee(candidatureId, commande.retenu(),
                commande.motif()));
    }

    @CommandHandler
    public void traiter(AnnulerCandidature commande) {
        // TODO : rendre l'annulation IDEMPOTENTE — annuler deux fois ne doit produire qu'un seul evenement
        // une compensation est rejouee : elle doit supporter de l'etre
        apply(new CandidatureAnnulee(candidatureId, commande.motif()));
    }

    // ── application des faits : aucune validation, jamais ────────────────

    @EventSourcingHandler
    void on(CandidatureDeposee fait) {
        this.candidatureId = fait.candidatureId();
        this.candidat = fait.candidat();
        this.offre = fait.offre();
    }

    @EventSourcingHandler
    void on(EntretienPlanifie fait) {
        this.entretienPlanifie = true;
    }

    @EventSourcingHandler
    void on(DecisionPrononcee fait) {
        this.close = true;
    }

    @EventSourcingHandler
    void on(CandidatureAnnulee fait) {
        this.close = true;
    }

    public String candidat() {
        return candidat;
    }

    public String offre() {
        return offre;
    }

    public boolean entretienPlanifie() {
        return entretienPlanifie;
    }

    public boolean close() {
        return close;
    }
}
