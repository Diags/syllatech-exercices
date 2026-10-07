package fr.portail.domaine;

import java.util.EnumSet;
import java.util.Set;

/**
 * Un candidat.
 *
 * <p>Un {@code record} : le compilateur écrit {@code equals}, {@code hashCode}
 * et {@code toString} à partir des composants, et les trois restent cohérents
 * quand on ajoute un champ. Le chapitre 2 les compare à une classe écrite à
 * la main ; le chapitre 3 montre ce qu'une classe <em>muable</em> fait à un
 * {@code HashMap}.
 *
 * <p>Le bloc compact valide à la construction. Un record n'est pas une
 * structure sans règles : c'est un porteur de données <strong>valides</strong>,
 * et l'endroit pour l'exiger est ici, une fois, plutôt que partout où on
 * l'utilise.
 */
public record Candidat(String nom, String courriel, int anneesExperience,
                       Set<Competence> competences) {

    public Candidat {
        if (nom == null || nom.isBlank()) {
            throw new IllegalArgumentException("un candidat a un nom");
        }
        if (courriel == null || !courriel.contains("@")) {
            throw new IllegalArgumentException(
                    "courriel invalide : " + courriel);
        }
        if (anneesExperience < 0) {
            throw new IllegalArgumentException(
                    "experience negative : " + anneesExperience);
        }
        // Copie defensive. Sans elle, l'appelant garde une reference sur
        // l'ensemble et peut le modifier APRES la construction — le record
        // serait alors muable par la bande, et son hashCode changerait.
        competences = competences == null || competences.isEmpty()
                ? Set.of()
                : Set.copyOf(competences);
    }

    public static Candidat de(String nom, int annees, Competence... competences) {
        var courriel = nom.toLowerCase(java.util.Locale.ROOT)
                .replace(' ', '.') + "@exemple.test";
        return new Candidat(nom, courriel, annees,
                competences.length == 0 ? Set.of()
                        : EnumSet.copyOf(java.util.List.of(competences)));
    }

    public boolean maitrise(Competence competence) {
        return competences.contains(competence);
    }

    /** Le prénom, ou le nom entier s'il n'y a pas d'espace. */
    public String prenom() {
        int espace = nom.indexOf(' ');
        return espace < 0 ? nom : nom.substring(0, espace);
    }
}
