package fr.portail.securite;

import fr.portail.api.DemandeConnexion;
import fr.portail.api.Jetons;
import jakarta.validation.Valid;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ProblemDetail;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/** Les deux routes publiques : se connecter, et rafraichir. */
@RestController
@RequestMapping("/api/auth")
public class AuthControleur {

    private final ServiceAuthentification service;

    public AuthControleur(ServiceAuthentification service) {
        this.service = service;
    }

    @PostMapping("/connexion")
    public Jetons connexion(@RequestBody @Valid DemandeConnexion demande) {
        return service.connecter(demande);
    }

    @PostMapping("/rafraichir")
    public Jetons rafraichir(@RequestBody Map<String, String> corps) {
        return service.rafraichir(corps.get("refreshToken"));
    }

    /**
     * ⚠️ 401, ET UN MESSAGE GENERIQUE. Le service leve la meme exception pour
     * un compte inconnu et un mot de passe faux ; ce gestionnaire ne doit
     * surtout pas la detailler.
     */
    @ExceptionHandler(BadCredentialsException.class)
    public ProblemDetail refus(BadCredentialsException erreur) {
        ProblemDetail probleme = ProblemDetail.forStatusAndDetail(
                HttpStatus.UNAUTHORIZED, "identifiants invalides");
        probleme.setTitle("Authentification refusee");
        return probleme;
    }
}
