package fr.portail.web;

import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Le controleur : deux routes, et rien d'autre.
 *
 * <p>⚠️ REGARDEZ CE QU'IL NE FAIT PAS. Il ne construit pas d'agent, ne
 * choisit pas de modele, ne connait aucun outil. Il recoit un
 * {@link ReActAgent} par injection, fabrique un {@link RuntimeContext} pour
 * la session en cours, et rend le flux. Tout ce qui precede est de la
 * configuration.
 *
 * <p>Le flux d'evenements de l'agent est deja un {@code Flux} : le mapper
 * sur du Server-Sent Events ne demande donc aucune passerelle, aucun pont,
 * aucun fil d'execution supplementaire.
 */
@RestController
public class AssistantControleur {

    private final ReActAgent agent;

    /**
     * Un seul constructeur : Spring injecte le bean sans {@code @Autowired}.
     */
    public AssistantControleur(ReActAgent agent) {
        this.agent = agent;
    }

    /** La reponse complete, pour un appel ordinaire. */
    @GetMapping(value = "/assistant", produces = MediaType.APPLICATION_JSON_VALUE)
    public Mono<String> repondre(@RequestParam String q,
                                 @RequestParam(defaultValue = "anonyme") String session) {
        return agent.call(q, contexte(session))
                .map(message -> message.getTextContent());
    }

    /**
     * Le MEME agent, en Server-Sent Events.
     *
     * <p>⚠️ Chaque evenement porte son TYPE : l'interface peut afficher
     * « je consulte le catalogue… » au moment ou l'outil demarre, et non
     * apres coup. C'est ce que des logs ne permettent pas.
     */
    @GetMapping(value = "/assistant/flux",
                produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public Flux<ServerSentEvent<String>> flux(
            @RequestParam String q,
            @RequestParam(defaultValue = "anonyme") String session) {
        // TODO : mapper le flux d'evenements de l'agent sur du SSE — le TYPE de l'evenement doit partir dans le champ `event:`, sans quoi le navigateur ne peut rien afficher au bon moment
        return Flux.empty();
    }

    private static ServerSentEvent<String> enSse(AgentEvent evenement) {
        return ServerSentEvent.<String>builder()
                .id(evenement.getId())
                .event(evenement.getType().name())
                .data(evenement.toString())
                .build();
    }

    /**
     * ⚠️ LA SESSION VIENT DE L'UTILISATEUR AUTHENTIFIE, PAS DU CLIENT.
     *
     * <p>Ici, un parametre de requete suffit a la demonstration. En
     * production, `sessionId` et `userId` se lisent dans le `Principal` :
     * accepter un identifiant de session fourni par l'appelant revient a
     * laisser n'importe qui relire la conversation d'un autre.
     */
    private static RuntimeContext contexte(String session) {
        return RuntimeContext.builder()
                .sessionId(session)
                .userId(session)
                .build();
    }
}
