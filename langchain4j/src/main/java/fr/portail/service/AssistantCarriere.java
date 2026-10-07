package fr.portail.service;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;

/**
 * L'assistant du portail — une interface, zéro implémentation.
 *
 * <p>C'est la signature de LangChain4j : on décrit le service, le framework
 * en fabrique un proxy dynamique à l'exécution. Le même réflexe qu'un
 * repository Spring Data.
 *
 * <p>Ce que le chapitre 1 mesure ici : les <strong>deux</strong> messages que
 * ces annotations produisent, et le fait que {@code @SystemMessage} repart à
 * chaque appel.
 */
public interface AssistantCarriere {

    // >>> depart: poser le cadre de l'assistant — un @SystemMessage qui dit sa personnalite et sa langue
    @SystemMessage("Tu es un conseiller carriere bienveillant pour un portail "
                   + "d'emploi. Reponds en francais, en trois points au "
                   + "maximum.")
    // <<<
    String conseiller(@UserMessage String question);

    /**
     * Un template à variables, rempli par {@code @V}.
     *
     * <p>⚠️ Les accolades sont <strong>doubles</strong> en LangChain4j
     * ({@code {{poste}}}), là où Spring AI en utilise une seule. Le chapitre 2
     * montre ce que cela change quand les données elles-mêmes contiennent des
     * accolades.
     */
    @SystemMessage("Tu es un conseiller carriere pour un portail d'emploi.")
    @UserMessage("Donne un conseil a quelqu'un qui vise le poste de {{poste}} "
                 + "dans la ville de {{ville}}.")
    String conseilCible(@V("poste") String poste, @V("ville") String ville);
}
