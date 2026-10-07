package fr.portail.service;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.TokenStream;
import dev.langchain4j.service.UserMessage;

/**
 * Le même assistant, mais qui rend un flux.
 *
 * <p>Le type de retour suffit à tout changer : un {@link TokenStream} au lieu
 * d'un {@code String}, et {@code AiServices} exige alors un
 * {@code streamingChatModel(...)}. L'appelant, lui, ne reçoit plus une valeur
 * mais s'abonne — {@code onPartialResponse}, {@code onCompleteResponse},
 * {@code onError}, puis {@code start()}.
 *
 * <p>⚠️ {@code start()} n'est pas décoratif : sans lui, rien ne part. C'est
 * l'oubli le plus banal du streaming, et il ne produit aucune erreur — juste
 * un silence.
 */
public interface AssistantEnFlux {

    @SystemMessage("Tu es un conseiller carriere pour un portail d'emploi.")
    TokenStream conseiller(@UserMessage String question);
}
