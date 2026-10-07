package fr.portail.offre.dto;

import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;

/**
 * Ce qu'un client a le droit d'envoyer pour créer une offre.
 *
 * <p>Remarquez ce qui n'y est <strong>pas</strong> : ni {@code id}, ni
 * {@code salaireReel}. Un client qui les enverrait ne les verrait pas
 * appliqués — non pas parce qu'on les ignore quelque part dans le service,
 * mais parce qu'ils n'existent pas dans le contrat. C'est la protection la
 * plus solide : celle qu'on ne peut pas oublier.
 *
 * <p>Les annotations sont le contrôle à la frontière. Le chapitre 3 vérifie
 * qu'une donnée invalide n'atteint jamais le service — avec un compteur, pas
 * avec une affirmation.
 */
// TODO : annoter les quatre composants avec les contraintes de Bean Validation et leurs messages
public record CreerOffreDto(String titre, int salaireMin,
                            String contactEmail, String entreprise) {
}
