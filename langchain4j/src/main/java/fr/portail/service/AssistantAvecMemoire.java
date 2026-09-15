package fr.portail.service;

import dev.langchain4j.service.MemoryId;
import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;

/**
 * Le même assistant, mais qui se souvient — et par utilisateur.
 *
 * <p>⚠️ <strong>Pourquoi cette interface est séparée de
 * {@link AssistantCarriere}.</strong> Un seul paramètre {@code @MemoryId}
 * suffit à rendre le {@code ChatMemoryProvider} obligatoire pour TOUT le
 * service : {@code AiServices.create(...)} refuse alors de construire le
 * proxy, avec le message « please configure the ChatMemoryProvider ».
 * L'échec est immédiat et clair — c'est le bon comportement — mais il
 * contamine les méthodes qui n'ont rien demandé. Le chapitre 5 le mesure.
 */
public interface AssistantAvecMemoire {

    @SystemMessage("Tu es un conseiller carriere pour un portail d'emploi.")
    String discuter(@MemoryId String utilisateur, @UserMessage String question);
}
