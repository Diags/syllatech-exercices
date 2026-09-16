package fr.portail.web;

import fr.portail.cles.Cles;
import fr.portail.jeton.ServiceDeJetons;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Le portail joue son propre serveur d'autorisation — juste assez pour que
 * le chapitre 5 soit mesurable hors ligne.
 *
 * <p>Deux points, et ce sont exactement ceux qu'un KeyCloak publie :
 *
 * <ul>
 *   <li>{@code /.well-known/openid-configuration} — le document de
 *       découverte. C'est lui que Spring lit au démarrage quand on ne lui
 *       donne qu'un {@code issuer-uri} ;</li>
 *   <li>{@code /oauth2/jwks} — les clés <strong>publiques</strong>, au format
 *       JWKS. Le resource server les télécharge et les garde en cache.</li>
 * </ul>
 *
 * <p>{@link #lecturesDuJwks} compte les téléchargements : le chapitre 5
 * envoie cent requêtes authentifiées et montre que le compteur ne bouge pas —
 * la validation d'un JWT ne parle à personne.
 */
@RestController
public class Decouverte {

    private static final AtomicInteger LECTURES_JWKS = new AtomicInteger();

    private final Cles cles;

    Decouverte(Cles cles) {
        this.cles = cles;
    }

    public static int lecturesDuJwks() {
        return LECTURES_JWKS.get();
    }

    public static void remettreAZero() {
        LECTURES_JWKS.set(0);
    }

    @GetMapping("/.well-known/openid-configuration")
    Map<String, Object> decouverte() {
        String emetteur = ServiceDeJetons.EMETTEUR;
        return Map.of(
                "issuer", emetteur,
                "jwks_uri", emetteur + "/oauth2/jwks",
                "authorization_endpoint", emetteur + "/oauth2/authorize",
                "token_endpoint", emetteur + "/oauth2/token",
                "response_types_supported", List.of("code"),
                "subject_types_supported", List.of("public"),
                "id_token_signing_alg_values_supported", List.of("RS256"),
                // ⚠️ S256 seulement : `plain` est une methode PKCE ou le
                // « secret » voyage en clair au premier appel, ce qui lui
                // retire tout interet. La lister reviendrait a la permettre.
                "code_challenge_methods_supported", List.of("S256"));
    }

    /**
     * Les clés publiques. Aucune clé privée n'en sort — c'est vérifiable dans
     * la sortie du chapitre 4, qui affiche le document en entier.
     */
    @GetMapping("/oauth2/jwks")
    Map<String, Object> jwks() {
        LECTURES_JWKS.incrementAndGet();
        return new com.nimbusds.jose.jwk.JWKSet(cles.jwk().toPublicJWK())
                .toJSONObject();
    }
}
