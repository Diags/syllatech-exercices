package fr.portail.api;

import jakarta.validation.constraints.NotBlank;

/** Ce que React envoie a POST /api/auth/connexion. */
public record DemandeConnexion(@NotBlank String identifiant,
                               @NotBlank String motDePasse) {
}
