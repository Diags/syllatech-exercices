package fr.portail.tri;

import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.domaine.Offre;
import java.util.Comparator;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.stream.Collectors;

/**
 * Le tri des candidatures — l'endroit où ce projet <em>fait</em> quelque
 * chose plutôt que de le mesurer.
 *
 * <p>Tout y est écrit en pipelines de {@code Stream}, parce que c'est le
 * style que le chapitre 4 décrit et qu'un exemple qui prêche le déclaratif
 * en écrivant des boucles n'enseigne rien. Les tests de
 * {@code SelectionTest} fixent le comportement attendu de chaque méthode :
 * sur la branche {@code depart}, ils échouent, et les faire passer
 * <strong>est</strong> l'exercice.
 */
public final class Selection {

    private Selection() {
    }

    /** Le poids d'une année d'expérience au-delà du minimum exigé. */
    private static final int POINTS_PAR_ANNEE = 3;

    /** Le poids d'une compétence exigée que le candidat possède. */
    private static final int POINTS_PAR_COMPETENCE = 10;

    /**
     * Les candidats qui satisfont l'offre, du plus expérimenté au moins.
     *
     * <p>À expérience égale, l'ordre est alphabétique : un tri qui dépend de
     * l'ordre d'arrivée rend les tests irreproductibles, et c'est la première
     * chose qu'on regrette.
     */
    public static List<Candidat> retenus(List<Candidat> vivier, Offre offre) {
        // >>> depart: filtrer le vivier avec `offre.convient`, puis trier par experience decroissante et nom croissant
        //     return List.of();
        return vivier.stream()
                .filter(offre::convient)
                .sorted(Comparator.comparingInt(Candidat::anneesExperience).reversed()
                        .thenComparing(Candidat::nom))
                .toList();
        // <<<
    }

    /**
     * Un score, pour départager ceux qui satisfont tous la même offre.
     *
     * <p>Volontairement simple et entier : un score en virgule flottante
     * introduirait des égalités qui n'en sont pas, et un tri instable par
     * dessus.
     */
    public static int score(Candidat candidat, Offre offre) {
        // >>> depart: compter POINTS_PAR_COMPETENCE par competence exigee possedee, plus POINTS_PAR_ANNEE par annee au-dela du minimum
        //     return 0;
        int surCompetences = (int) offre.requises().stream()
                .filter(candidat::maitrise)
                .count() * POINTS_PAR_COMPETENCE;
        int annees = Math.max(0,
                candidat.anneesExperience() - offre.experienceMinimale());
        return surCompetences + annees * POINTS_PAR_ANNEE;
        // <<<
    }

    /**
     * Les {@code combien} meilleurs noms pour cette offre.
     *
     * <p>⚠️ {@code sorted} avant {@code limit} : le chapitre 4 mesure que
     * cette chaîne consomme <strong>toute</strong> la source. C'est
     * inévitable ici — on ne peut pas connaître les trois meilleurs sans
     * avoir vu tout le monde — et c'est exactement pourquoi le compteur du
     * chapitre 4 affiche 100 et non 3.
     */
    public static List<String> classement(List<Candidat> vivier, Offre offre,
                                          int combien) {
        // >>> depart: trier le vivier par score decroissant, garder les `combien` premiers, rendre leurs noms
        //     return List.of();
        return vivier.stream()
                .sorted(Comparator.comparingInt((Candidat c) -> score(c, offre))
                        .reversed()
                        .thenComparing(Candidat::nom))
                .limit(combien)
                .map(Candidat::nom)
                .toList();
        // <<<
    }

    /**
     * Combien de candidats du vivier maîtrisent chaque compétence.
     *
     * <p>Un {@link TreeMap}, et non le {@code HashMap} que {@code groupingBy}
     * donne par défaut : le chapitre 3 montre que l'ordre d'un {@code HashMap}
     * n'est ni alphabétique ni stable d'une version de Java à l'autre. Quand
     * le résultat est affiché ou comparé, l'ordre doit être dit.
     */
    public static Map<String, Long> parCompetence(List<Candidat> vivier) {
        // >>> depart: aplatir les competences du vivier et les compter, dans une TreeMap indexee par libelle
        //     return Map.of();
        return vivier.stream()
                .flatMap(c -> c.competences().stream())
                .collect(Collectors.groupingBy(Competence::libelle,
                        TreeMap::new, Collectors.counting()));
        // <<<
    }

    /**
     * Ce qui manque à chaque candidat écarté, prêt à être écrit dans un
     * courriel de refus.
     */
    public static Map<String, String> motifsDeRefus(List<Candidat> vivier,
                                                    Offre offre) {
        return vivier.stream()
                .filter(c -> !offre.convient(c))
                .collect(Collectors.toMap(Candidat::nom,
                        c -> motif(c, offre),
                        (premier, second) -> premier,
                        TreeMap::new));
    }

    private static String motif(Candidat candidat, Offre offre) {
        var manquantes = offre.manquantes(candidat);
        if (candidat.anneesExperience() < offre.experienceMinimale()) {
            int manque = offre.experienceMinimale() - candidat.anneesExperience();
            return manquantes.isEmpty()
                    ? manque + " an(s) d'experience de moins que demande"
                    : manque + " an(s) de moins, et " + libelles(manquantes);
        }
        return libelles(manquantes);
    }

    private static String libelles(java.util.Set<Competence> competences) {
        return competences.stream()
                .map(Competence::libelle)
                .sorted()
                .collect(Collectors.joining(", "));
    }
}
