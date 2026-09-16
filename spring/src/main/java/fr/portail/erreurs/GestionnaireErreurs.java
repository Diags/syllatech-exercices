package fr.portail.erreurs;

import java.net.URI;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * Une seule forme d'erreur pour toute l'API.
 *
 * <p>Sans cette classe, une {@link EntrepriseInconnue} ressortirait en 500
 * avec une trace — le client apprendrait le nom de nos classes et rien
 * d'utile. Elle est traduite ici, une fois, et toutes les routes en
 * bénéficient : c'est ce que le cours appelle « pas de try/catch dispersés ».
 *
 * <p>Le format est celui de la <strong>RFC 9457</strong>, que Spring
 * implémente sous le nom {@link ProblemDetail}.
 *
 * <p>⚠️ <strong>Deux choses que « Spring le fait tout seul » ne couvre
 * pas.</strong> Le chapitre 3 les mesure :
 *
 * <ol>
 *   <li>tant que {@code spring.mvc.problemdetails.enabled} vaut {@code false}
 *       — et c'est le défaut — un échec de validation rend un 400 au
 *       <strong>corps vide</strong>, pas un {@code ProblemDetail} ;</li>
 *   <li>même une fois la propriété posée, le {@code ProblemDetail} produit
 *       dit « Invalid request content. » et <strong>ne nomme aucun
 *       champ</strong>. Le client sait que sa requête est mauvaise, pas
 *       pourquoi.</li>
 * </ol>
 *
 * <p>D'où {@link #handleMethodArgumentNotValid} ci-dessous : il ajoute une
 * propriété {@code champs} au document, sans rien changer à sa forme. C'est
 * la seule façon d'obtenir ce que le support de cours décrit.
 */
@RestControllerAdvice
public class GestionnaireErreurs extends ResponseEntityExceptionHandler {

    /** L'espace de noms des types d'erreur du portail. */
    public static final String BASE = "https://portail.exemple.test/erreurs/";

    @ExceptionHandler(EntrepriseInconnue.class)
    ProblemDetail entrepriseInconnue(EntrepriseInconnue erreur) {
        // TODO : rendre un ProblemDetail 422, avec un titre, un type sous BASE, et le nom en propriete
        return ProblemDetail.forStatus(HttpStatus.INTERNAL_SERVER_ERROR);
    }

    @ExceptionHandler(PanneMetier.class)
    ProblemDetail panneMetier(PanneMetier erreur) {
        var probleme = ProblemDetail.forStatusAndDetail(
                HttpStatus.SERVICE_UNAVAILABLE, erreur.getMessage());
        probleme.setTitle("Service indisponible");
        probleme.setType(URI.create(BASE + "panne-metier"));
        return probleme;
    }

    /**
     * Ajoute au {@code ProblemDetail} de validation le détail des champs.
     *
     * <p>Spring construit déjà le document ; on ne le remplace pas, on
     * l'enrichit. Remplacer ferait perdre {@code instance}, {@code status} et
     * la cohérence avec les autres erreurs que Spring produit seul.
     */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(
            MethodArgumentNotValidException erreur, HttpHeaders entetes,
            HttpStatusCode code, WebRequest requete) {
        var reponse = super.handleMethodArgumentNotValid(
                erreur, entetes, code, requete);
        if (reponse == null || !(reponse.getBody() instanceof ProblemDetail probleme)) {
            return reponse;
        }
        Map<String, String> champs = new LinkedHashMap<>();
        for (var faute : erreur.getBindingResult().getFieldErrors()) {
            // Le premier message par champ suffit : en afficher trois pour un
            // meme champ n'aide ni l'humain ni le programme qui les lit.
            champs.putIfAbsent(faute.getField(), faute.getDefaultMessage());
        }
        probleme.setTitle("Requete invalide");
        probleme.setType(URI.create(BASE + "requete-invalide"));
        probleme.setProperty("champs", champs);
        return reponse;
    }
}
