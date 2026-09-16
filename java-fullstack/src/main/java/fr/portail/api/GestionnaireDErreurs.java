package fr.portail.api;

import java.net.URI;
import java.util.NoSuchElementException;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Les erreurs, normalisees — en {@code application/problem+json} (RFC 9457).
 *
 * <p>⚠️ SANS CELA, UNE API REND TROIS FORMATS D'ERREUR DIFFERENTS : celui de
 * Spring, celui de la validation, et le message brut d'une exception.
 * Cote React, chaque cas demande alors son propre traitement — et le jour
 * ou un format change, l'affichage casse sans qu'un test le voie.
 *
 * <p>⚠️ Et le detail qui compte pour la securite : le message d'exception
 * n'est PAS recopie tel quel. Une trace de base de donnees dans une reponse
 * HTTP dit a un attaquant le nom de vos tables.
 */
@RestControllerAdvice
public class GestionnaireDErreurs {

    @ExceptionHandler(NoSuchElementException.class)
    public ProblemDetail introuvable(NoSuchElementException erreur) {
        ProblemDetail probleme = ProblemDetail.forStatusAndDetail(
                HttpStatus.NOT_FOUND, erreur.getMessage());
        probleme.setTitle("Ressource introuvable");
        probleme.setType(URI.create("https://syllatech.pages.dev/erreurs/introuvable"));
        return probleme;
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ProblemDetail invalide(MethodArgumentNotValidException erreur) {
        ProblemDetail probleme = ProblemDetail.forStatus(HttpStatus.BAD_REQUEST);
        probleme.setTitle("Requete invalide");
        probleme.setType(URI.create("https://syllatech.pages.dev/erreurs/validation"));
        // ⚠️ Champ par champ : le front peut alors afficher l'erreur SOUS le
        // champ fautif, au lieu d'une banniere generique.
        probleme.setProperty("champs", erreur.getBindingResult()
                .getFieldErrors().stream()
                .collect(java.util.stream.Collectors.toMap(
                        org.springframework.validation.FieldError::getField,
                        champ -> champ.getDefaultMessage() == null
                                ? "invalide" : champ.getDefaultMessage(),
                        (premier, second) -> premier)));
        return probleme;
    }
}
