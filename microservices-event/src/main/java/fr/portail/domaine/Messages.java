package fr.portail.domaine;

import org.axonframework.modelling.command.TargetAggregateIdentifier;

/**
 * Les commandes et les événements du portail, au même endroit.
 *
 * <p>Ce n'est pas un détail de rangement : c'est la distinction centrale du
 * chapitre 1. Une <strong>commande</strong> est une intention, écrite à
 * l'impératif, et elle <em>peut être refusée</em>. Un <strong>événement</strong>
 * est un fait accompli, écrit au participe passé, et il ne se discute plus —
 * il est déjà dans le journal.
 *
 * <p>Les noms suivent cette règle sans exception :
 * {@code DeposerCandidature} se refuse, {@code CandidatureDeposee} non.
 *
 * <p>⚠️ <strong>{@code @TargetAggregateIdentifier} n'est pas décoratif.</strong>
 * C'est par lui qu'Axon sait vers <em>quelle instance</em> router la commande.
 * Sans lui, le bus ne sait pas quel flux d'événements charger, et l'envoi
 * échoue à l'exécution — jamais à la compilation. Le chapitre 2 le mesure.
 */
public final class Messages {

    private Messages() {
    }

    // ── les commandes : des intentions, qui peuvent echouer ──────────────

    /** Déposer une candidature sur une offre. */
    public record DeposerCandidature(String candidatureId, String candidat,
                                     String offre) {
    }

    /** Planifier l'entretien, une fois un créneau obtenu. */
    public record PlanifierEntretien(
            @TargetAggregateIdentifier String candidatureId,
            String creneau) {
    }

    /** Prononcer la décision finale. */
    public record Decider(@TargetAggregateIdentifier String candidatureId,
                          boolean retenu, String motif) {
    }

    /** Annuler la candidature — la compensation de la saga. */
    public record AnnulerCandidature(
            @TargetAggregateIdentifier String candidatureId, String motif) {
    }

    /** Réserver un créneau d'entretien dans l'agenda. */
    public record ReserverCreneau(@TargetAggregateIdentifier String agendaId,
                                  String candidatureId) {
    }

    /** Relâcher un créneau réservé — l'autre compensation. */
    public record RelacherCreneau(@TargetAggregateIdentifier String agendaId,
                                  String candidatureId) {
    }

    // ── les evenements : des faits, qui ne se discutent plus ─────────────

    public record CandidatureDeposee(String candidatureId, String candidat,
                                     String offre) {
    }

    public record EntretienPlanifie(String candidatureId, String creneau) {
    }

    public record DecisionPrononcee(String candidatureId, boolean retenu,
                                    String motif) {
    }

    public record CandidatureAnnulee(String candidatureId, String motif) {
    }

    public record CreneauReserve(String agendaId, String candidatureId,
                                 String creneau) {
    }

    public record CreneauRefuse(String agendaId, String candidatureId,
                                String motif) {
    }

    public record CreneauRelache(String agendaId, String candidatureId) {
    }
}
