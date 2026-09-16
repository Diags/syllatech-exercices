package fr.portail.securite;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Une route publique qui tombe en panne — pour voir ce que le client reçoit.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Elle lève une
 * exception que rien ne traite : ni le service, ni le
 * {@code @RestControllerAdvice}. C'est le cas d'une panne imprévue, celle
 * qu'on n'a pas anticipée.
 *
 * <p>La route est dans {@code /api/public/**}, donc ouverte. On s'attend
 * donc à un <strong>500</strong>. Le chapitre 5 mesure ce que le client
 * reçoit réellement, et ce n'est pas 500 : quand Spring MVC ne sait pas
 * traiter une exception, il fait une nouvelle passe vers {@code /error} — et
 * cette passe retraverse la chaîne de filtres. {@code /error} n'étant cité
 * nulle part dans {@link SecurityConfig}, c'est
 * {@code anyRequest().authenticated()} qui répond.
 *
 * <p>Conséquence pratique : une panne de votre base se présente au client
 * comme un problème d'authentification. C'est une heure de recherche dans la
 * mauvaise direction, et elle arrive à tout le monde une fois.
 */
@RestController
@RequestMapping("/api/public")
public class RoutePanne {

    @GetMapping("/panne")
    Map<String, Object> panne() {
        throw new IllegalStateException("la base de donnees ne repond pas");
    }
}
