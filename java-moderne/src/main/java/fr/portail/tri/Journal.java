package fr.portail.tri;

import fr.portail.domaine.Dossier;
import fr.portail.domaine.Evenement;
import java.time.LocalDate;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Le journal d'un dossier, écrit pour être lu par un humain.
 *
 * <p>C'est l'application directe du chapitre 6 : une hiérarchie scellée, des
 * {@code record}, et un {@code switch} qui déconstruit chaque cas. Aucun
 * {@code default} — s'il en fallait un, ce serait le signe que la hiérarchie
 * n'est pas si fermée que cela.
 */
public final class Journal {

    private Journal() {
    }

    /** Une ligne de journal par événement, dans l'ordre. */
    public static List<String> lignes(Dossier dossier) {
        return dossier.evenements().stream()
                .map(Journal::decrire)
                .toList();
    }

    /** Le journal complet, prêt à être imprimé. */
    public static String texte(Dossier dossier) {
        return lignes(dossier).stream().collect(Collectors.joining("\n"));
    }

    /**
     * Une phrase française par événement.
     *
     * <p>Les motifs de {@code record} évitent trois lignes par cas : pas de
     * test de type, pas de conversion, pas d'accesseur. Ce que le
     * {@code switch} lie, ce sont directement les composants.
     */
    public static String decrire(Evenement evenement) {
        // TODO : un switch exhaustif sur les quatre cas, avec des motifs de record — sans `default`
        return evenement.toString();
    }

    /**
     * Le dossier est-il clos, et sur quoi ?
     *
     * <p>Un {@code Optional} plutôt qu'un {@code null} : le chapitre 4 mesure
     * la différence entre {@code orElse} et {@code orElseGet}, mais la vraie
     * raison de l'utiliser est ici — la signature dit qu'il peut ne rien y
     * avoir, et le compilateur oblige l'appelant à en tenir compte.
     */
    public static java.util.Optional<Evenement.Issue> issue(Dossier dossier) {
        return dossier.evenements().reversed().stream()
                .filter(e -> e instanceof Evenement.Decision)
                .map(e -> ((Evenement.Decision) e).issue())
                .findFirst();
    }

    /** Le nombre de jours entre le dépôt et la décision, s'il y en a une. */
    public static java.util.OptionalLong delaiEnJours(Dossier dossier) {
        var evenements = dossier.evenements();
        var depot = evenements.getFirst().date();
        return evenements.reversed().stream()
                .filter(e -> e instanceof Evenement.Decision)
                .mapToLong(e -> java.time.temporal.ChronoUnit.DAYS.between(
                        depot, e.date()))
                .findFirst();
    }
}
