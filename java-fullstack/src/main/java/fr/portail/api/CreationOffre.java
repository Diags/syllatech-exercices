package fr.portail.api;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

/**
 * Ce que l'API accepte en ENTREE, et la validation qui va avec.
 *
 * <p>⚠️ LA VALIDATION EST A LA FRONTIERE, pas dans le service. Une donnee
 * qui n'a jamais ete valide ne doit pas atteindre le metier : c'est la
 * seule facon d'avoir un service dont les preconditions sont vraies par
 * construction.
 *
 * <p>⚠️ Et remarquez qu'il n'y a PAS d'`id` : il est engendre par la base.
 * L'accepter en entree laisserait un client choisir l'identifiant d'une
 * ressource — ou ecraser celle d'un autre.
 */
public record CreationOffre(
        // TODO : valider a la FRONTIERE — un titre non vide et borne, une pile parmi java/devops/front, un salaire plausible. La coherence metier, elle, reste au service
        String titre,
        String pile,
        int salaireEnKiloEuros,
        long entrepriseId) {
}
