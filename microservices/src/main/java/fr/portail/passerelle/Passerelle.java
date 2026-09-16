package fr.portail.passerelle;

import static org.springframework.cloud.gateway.server.mvc.filter.BeforeFilterFunctions.rewritePath;
import static org.springframework.cloud.gateway.server.mvc.filter.CircuitBreakerFilterFunctions.circuitBreaker;
import static org.springframework.cloud.gateway.server.mvc.filter.LoadBalancerFilterFunctions.lb;
import static org.springframework.cloud.gateway.server.mvc.handler.GatewayRouterFunctions.route;
import static org.springframework.cloud.gateway.server.mvc.handler.HandlerFunctions.http;

import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.function.RequestPredicates;
import org.springframework.web.servlet.function.RouterFunction;
import org.springframework.web.servlet.function.ServerRequest;
import org.springframework.web.servlet.function.ServerResponse;

/**
 * La passerelle du portail — une vraie Spring Cloud Gateway.
 *
 * <p>Une seule porte d'entrée : le client appelle {@code /api/offres}, la
 * passerelle réécrit le chemin, demande une instance vivante à
 * l'équilibrage de charge, et relaie la requête.
 *
 * <p>La route porte un <strong>circuit breaker</strong> : au-delà d'un taux
 * d'échec, le circuit s'ouvre et les appels basculent immédiatement vers la
 * route de repli, sans même atteindre le service en difficulté.
 *
 * <p>⚠️ <strong>Les routes sont écrites en Java, pas en YAML.</strong> Le
 * cours les déclare dans {@code application.yml} sous
 * {@code spring.cloud.gateway.routes}. Ce chemin existe toujours, mais il a
 * changé de nom avec la scission de la passerelle en
 * {@code gateway-server-webmvc} et {@code gateway-server-webflux}. Les écrire
 * ici les rend visibles, et évite de dépendre d'un préfixe de propriété qui
 * bouge d'une version à l'autre.
 */
@SpringBootApplication
@RestController
public class Passerelle {

    /** Le nombre de fois où le repli a répondu — mesuré par le chapitre 3. */
    private static final AtomicInteger REPLIS = new AtomicInteger();

    public static int replis() {
        return REPLIS.get();
    }

    public static void remettreAZero() {
        REPLIS.set(0);
        REFUS.set(0);
    }

    /**
     * La route du portail : {@code /api/offres} → {@code offres-service}.
     *
     * <p>Trois éléments, et chacun compte :
     *
     * <ul>
     *   <li>{@code lb("offres-service")} demande une instance à l'annuaire —
     *       c'est le {@code lb://} du cours ;</li>
     *   <li>{@code rewritePath} transforme {@code /api/offres} en
     *       {@code /offres}, parce que le service ne connaît pas le préfixe
     *       public ;</li>
     *   <li>{@code circuitBreaker} pose le disjoncteur et nomme la route de
     *       repli.</li>
     * </ul>
     */
    @Bean
    public RouterFunction<ServerResponse> routeDesOffres() {
        // ⚠️ L'ordre de `filter(...)` compte : le disjoncteur doit envelopper
        // l'equilibrage, sinon il compterait des echecs qui n'ont jamais
        // atteint le reseau. `lb(...)` et `circuitBreaker(...)` sont tous
        // deux des `HandlerFilterFunction` ; `rewritePath(...)`, lui, ne
        // touche qu'a la requete et passe par `before(...)`.
        return route("offres")
                .route(RequestPredicates.path("/api/offres"), http())
                // TODO : reecrire le chemin public /api/offres vers /offres, que le service expose
                // sans cela, le service recoit /api/offres et rend 404
                .filter(lb("offres-service"))
                .filter(circuitBreaker("offresCB", "/repli/offres"))
                .build();
    }

    /**
     * La même route, mais qui considère un 500 comme un échec.
     *
     * <p>⚠️ <strong>C'est la découverte du chapitre 3, et elle surprend tout
     * le monde.</strong> Par défaut, un disjoncteur de passerelle ne compte
     * que les <em>exceptions</em> — connexion refusée, délai dépassé, aucune
     * instance disponible. Un service qui répond proprement
     * <strong>500</strong> n'ouvre donc <em>jamais</em> le circuit : du point
     * de vue de la passerelle, l'appel a réussi, c'est la réponse qui est
     * mauvaise.
     *
     * <p>{@code setStatusCodes(...)} change cela. C'est presque toujours ce
     * qu'on veut, et c'est presque jamais ce qui est écrit dans les
     * tutoriels.
     */
    @Bean
    public RouterFunction<ServerResponse> routeStricte() {
        return route("offres-strict")
                .route(RequestPredicates.path("/api/strict/offres"), http())
                .before(rewritePath("/api/strict/offres", "/offres"))
                .filter(lb("offres-service"))
                // TODO : compter les reponses 5xx comme des echecs, sinon le circuit ne s'ouvrira jamais
                .filter(circuitBreaker(config -> config
                        .setId("offresStrictCB")
                        .setFallbackPath("/repli/offres")))
                .build();
    }

    /**
     * La route protégée : un jeton, et un identifiant de corrélation.
     *
     * <p>Deux responsabilités que la passerelle centralise, et c'est tout
     * l'intérêt d'une porte d'entrée unique :
     *
     * <ul>
     *   <li>elle <strong>refuse</strong> ce qui n'a pas de jeton, avant que
     *       la requête n'atteigne le moindre service ;</li>
     *   <li>elle <strong>pose</strong> un identifiant de corrélation, que
     *       tous les services en aval retrouveront dans leurs journaux.</li>
     * </ul>
     *
     * <p>⚠️ La vérification du jeton est volontairement rudimentaire : ce
     * projet n'ajoute pas Spring Security, parce que ce que le chapitre 6
     * mesure est l'<em>emplacement</em> du contrôle, pas l'algorithme de
     * signature. En production, c'est un vrai JWT validé contre un JWKS —
     * et c'est le cours Spring Security qui l'enseigne.
     */
    @Bean
    public RouterFunction<ServerResponse> routeProtegee() {
        return route("offres-protegees")
                .route(RequestPredicates.path("/api/prive/entetes"), http())
                .before(rewritePath("/api/prive/entetes", "/entetes"))
                .filter((requete, suivant) -> {
                    // TODO : refuser en 401 une requete sans jeton « Bearer », AVANT d'atteindre le service
                    // sans ce controle, la passerelle relaie tout
                    return suivant.handle(requete);
                })
                // ⚠️ Pose APRES le controle : un identifiant de correlation
                // n'a de sens que sur une requete acceptee.
                .before(request -> ServerRequest.from(request)
                        .header("X-Request-Id", java.util.UUID.randomUUID()
                                .toString().substring(0, 8))
                        .build())
                .filter(lb("offres-service"))
                .build();
    }

    /** Les requêtes refusées faute de jeton — mesurées par le chapitre 6. */
    private static final AtomicInteger REFUS = new AtomicInteger();

    public static int refus() {
        return REFUS.get();
    }

    /**
     * La réponse dégradée.
     *
     * <p>⚠️ C'est tout l'intérêt du circuit breaker : le client reçoit
     * <em>quelque chose</em>, tout de suite, au lieu d'attendre puis de
     * recevoir une erreur. Une liste vide et un message honnête valent mieux
     * qu'un 500 après trente secondes.
     */
    @GetMapping("/repli/offres")
    public Map<String, Object> repli() {
        REPLIS.incrementAndGet();
        return Map.of("source", "repli",
                "message", "Le service des offres est indisponible.",
                "offres", List.of());
    }
}
