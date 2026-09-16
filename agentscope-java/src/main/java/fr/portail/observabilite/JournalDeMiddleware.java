package fr.portail.observabilite;

import io.agentscope.core.agent.Agent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.message.ToolUseBlock;
import io.agentscope.core.middleware.ActingInput;
import io.agentscope.core.middleware.MiddlewareBase;
import io.agentscope.core.middleware.ModelCallInput;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Function;
import reactor.core.publisher.Flux;

/**
 * Un middleware : le point d'interception unique de la boucle.
 *
 * <p>C'est le pendant d'un aspect en AOP. Le code metier ne sait rien de
 * cette classe, et pourtant elle voit passer chaque appel au modele et
 * chaque phase d'action.
 *
 * <p>⚠️ CE QU'UN MIDDLEWARE NE DOIT PAS JOURNALISER. La tentation est
 * d'ecrire les arguments d'outil tels quels — c'est la ligne d'exemple de
 * toutes les documentations. Or ces arguments viennent de l'utilisateur :
 * un salaire, une adresse, un nom. Journaliser le NOM de l'outil et la
 * TAILLE des arguments suffit presque toujours, et ne cree pas une seconde
 * base de donnees personnelles a proteger.
 *
 * <p>Ce journal suit donc cette regle : il compte, il nomme, il ne recopie
 * pas.
 */
public final class JournalDeMiddleware implements MiddlewareBase {

    private final AtomicInteger appelsAuModele = new AtomicInteger();
    private final AtomicInteger phasesDAction = new AtomicInteger();
    private final List<String> outilsDemandes = new CopyOnWriteArrayList<>();
    private final List<String> lignes = new CopyOnWriteArrayList<>();

    @Override
    public Flux<AgentEvent> onModelCall(
            Agent agent, RuntimeContext contexte, ModelCallInput entree,
            Function<ModelCallInput, Flux<AgentEvent>> suite) {
        int rang = appelsAuModele.incrementAndGet();
        lignes.add("modele #" + rang + " — " + entree.messages().size()
                   + " message(s), " + entree.tools().size() + " outil(s)");
        return suite.apply(entree);
    }

    @Override
    public Flux<AgentEvent> onActing(
            Agent agent, RuntimeContext contexte, ActingInput entree,
            Function<ActingInput, Flux<AgentEvent>> suite) {
        // >>> depart: journaliser chaque action — le NOM de l'outil et la TAILLE de ses arguments, JAMAIS leur contenu : ils viennent de l'utilisateur
        //     for (ToolUseBlock appel : entree.toolCalls()) {
        //         outilsDemandes.add(appel.getName());
        //     }
        phasesDAction.incrementAndGet();
        for (ToolUseBlock appel : entree.toolCalls()) {
            outilsDemandes.add(appel.getName());
            // ⚠️ Le NOM, et la TAILLE des arguments. Jamais leur contenu.
            lignes.add("outil « " + appel.getName() + " » — "
                       + tailleDesArguments(appel) + " argument(s)");
        }
        // <<<
        return suite.apply(entree);
    }

    private static int tailleDesArguments(ToolUseBlock appel) {
        return appel.getInput() == null ? 0 : appel.getInput().size();
    }

    public int appelsAuModele() {
        return appelsAuModele.get();
    }

    public int phasesDAction() {
        return phasesDAction.get();
    }

    public List<String> outilsDemandes() {
        return List.copyOf(outilsDemandes);
    }

    /** Le journal, tel qu'il partirait dans votre systeme de logs. */
    public List<String> lignes() {
        return List.copyOf(lignes);
    }
}
