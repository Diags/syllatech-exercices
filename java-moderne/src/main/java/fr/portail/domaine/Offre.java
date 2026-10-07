package fr.portail.domaine;

import java.util.EnumSet;
import java.util.List;
import java.util.Set;

/** Une offre d'emploi publiée par le portail. */
public record Offre(String reference, String intitule, String ville,
                    int experienceMinimale, int salaire,
                    Set<Competence> requises) {

    public Offre {
        if (reference == null || reference.isBlank()) {
            throw new IllegalArgumentException("une offre a une reference");
        }
        requises = requises == null ? Set.of() : Set.copyOf(requises);
    }

    public static Offre de(String reference, String intitule, String ville,
                           int experienceMinimale, int salaire,
                           Competence... requises) {
        return new Offre(reference, intitule, ville, experienceMinimale,
                salaire,
                requises.length == 0 ? Set.of()
                        : EnumSet.copyOf(List.of(requises)));
    }

    /** Les compétences exigées que ce candidat n'a pas. */
    public Set<Competence> manquantes(Candidat candidat) {
        var manque = EnumSet.noneOf(Competence.class);
        for (var c : requises) {
            if (!candidat.maitrise(c)) {
                manque.add(c);
            }
        }
        return manque;
    }

    public boolean convient(Candidat candidat) {
        return candidat.anneesExperience() >= experienceMinimale
                && manquantes(candidat).isEmpty();
    }
}
