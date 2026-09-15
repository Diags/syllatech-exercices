package fr.portail.service;

import dev.langchain4j.service.SystemMessage;
import dev.langchain4j.service.UserMessage;
import dev.langchain4j.service.V;
import java.util.List;

/**
 * Un {@code AiService} à sortie typée — l'exemple exact du chapitre 2.
 *
 * <p>Le type de retour n'est pas une commodité : c'est lui qui déclenche tout
 * le mécanisme de sortie structurée. LangChain4j en déduit un schéma, impose
 * le format au modèle, puis désérialise la réponse.
 *
 * <p>⚠️ <strong>Et il l'impose de deux façons différentes.</strong> Si le
 * modèle déclare savoir faire {@code RESPONSE_FORMAT_JSON_SCHEMA}, le schéma
 * voyage dans la requête et le prompt reste intact ; sinon, LangChain4j écrit
 * les instructions <em>en toutes lettres à la fin du message utilisateur</em>.
 * Le chapitre 2 imprime les deux, côte à côte.
 */
public interface AnalyseurCV {

    /** Ce que l'on veut obtenir du modèle : un objet, pas du texte. */
    record Analyse(List<String> competences, int score, String resume) {
    }

    @SystemMessage("Tu analyses des CV pour un portail d'emploi.")
    @UserMessage("""
            Analyse ce CV pour le poste {{poste}} :
            {{cv}}""")
    Analyse analyser(@V("poste") String poste, @V("cv") String contenuCv);
}
