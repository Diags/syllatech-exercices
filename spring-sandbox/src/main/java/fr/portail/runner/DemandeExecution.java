package fr.portail.runner;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

/**
 * Le contrat d'entree du runner : ce que l'application lui confie.
 *
 * <p>⚠️ Un contrat ETROIT est une mesure de securite a part entiere. Deux
 * champs, deux contraintes, et rien d'autre ne traverse la frontiere : ni
 * chemin de fichier, ni variable d'environnement, ni drapeau. Tout ce que
 * l'appelant pourrait ajouter serait une surface d'attaque de plus.
 *
 * <p>La taille est bornee ici, cote runner, et non cote appelant : un
 * controle qui vit chez celui qui envoie ne protege personne.
 */
public record DemandeExecution(
        // >>> depart: borner le contrat — un champ vide, ou un code de plus de 20 000 caracteres, doit etre refuse par la VALIDATION, avant qu'aucun processus ne demarre
        //     String langage,
        //     String code) {
        @NotBlank String langage,
        @NotBlank @Size(max = 20_000) String code) {
    // <<<

    public static DemandeExecution script(String code) {
        return new DemandeExecution("jobportal-script", code);
    }
}
