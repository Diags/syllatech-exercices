package fr.portail.chapitres;

import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.service.AiServices;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.service.AssistantCarriere;

/**
 * Chapitre 1 — Démarrer avec LangChain4j et Spring Boot.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Demarrer
 * </pre>
 *
 * <p>« Aucune classe d'implémentation n'apparaît dans votre code :
 * LangChain4j génère un proxy dynamique derrière l'interface. » Ce chapitre
 * ouvre la boîte : le modèle de ce projet <strong>retient</strong> chaque
 * requête, et chaque section imprime ce que le proxy a réellement fabriqué.
 *
 * <p>C'est la seule façon de voir ce que {@code @SystemMessage} ajoute, et ce
 * que le reste du cours ajoutera par-dessus.
 */
public final class Chapitre1Demarrer {

    private Chapitre1Demarrer() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);

            Console.titre(1, "CE QU'UNE INTERFACE ANNOTEE FABRIQUE");
            var assistant = AiServices.create(AssistantCarriere.class, modele);
            modele.oublier();
            String reponse = assistant.conseiller(
                    "Donne 3 conseils pour decrocher un poste de developpeur Java");
            Console.sousTitre("Les messages envoyes au modele :");
            for (var message : modele.derniersMessages()) {
                Console.texte("[" + message.type() + "]", 5);
                Console.bloc(ModeleFactice.contenu(message), 9);
            }
            Console.sousTitre("La reponse :");
            Console.bloc(reponse, 6);
            System.out.println();
            Console.texte("Deux messages, et un seul vient de l'appelant. Le "
                    + "message SYSTEM a ete pose par `@SystemMessage`, une "
                    + "fois, sur la signature — il part avec CHAQUE requete, "
                    + "et c'est ce qui donne a l'assistant sa personnalite "
                    + "sans qu'on ait a la repeter.");
            System.out.println();
            Console.texte("C'est aussi ce qu'on paie : le message systeme est "
                    + "facture a chaque appel. Un prompt systeme de mille "
                    + "mots multiplie par un million d'appels, c'est un "
                    + "million de fois mille mots.");

            Console.titre(2, "LE PROXY, EN CHAIR ET EN OS");
            Console.ligne("le type declare",
                    AssistantCarriere.class.getSimpleName(), 26);
            Console.ligne("la classe obtenue",
                    assistant.getClass().getSimpleName().isBlank()
                            ? assistant.getClass().getName()
                            : assistant.getClass().getSimpleName(), 26);
            Console.ligne("est-ce un proxy JDK",
                    java.lang.reflect.Proxy.isProxyClass(assistant.getClass())
                            ? "oui" : "non", 26);
            Console.ligne("interfaces implementees",
                    String.valueOf(assistant.getClass().getInterfaces().length), 26);
            System.out.println();
            Console.texte("Aucune classe n'a ete ecrite, et pourtant un objet "
                    + "existe. C'est un `java.lang.reflect.Proxy` : chaque "
                    + "appel de methode passe par un gestionnaire qui lit vos "
                    + "annotations, construit les messages, appelle le "
                    + "modele, et convertit la reponse. Exactement le "
                    + "mecanisme d'un repository Spring Data.");
            System.out.println();
            Console.texte("⚠️ Ce que cela implique : vos annotations sont lues "
                    + "A L'EXECUTION. Une faute de frappe dans un "
                    + "`{{variable}}` ne fait pas echouer la compilation — "
                    + "elle fait echouer le premier appel, ou pire, elle "
                    + "envoie le texte du template au modele.");

            Console.titre(3, "LE MEME CODE, UN AUTRE MODELE");
            var autre = new ModeleFactice();
            autre.repondre(texte -> texte.contains("conseils")
                    ? "Reponse d'un second modele, avec un autre style." : null);
            var assistantBis = AiServices.create(AssistantCarriere.class, autre);
            Console.ligne("le meme appel, sur le second modele",
                    assistantBis.conseiller("Donne 3 conseils").lines()
                            .findFirst().orElse(""), 40);
            System.out.println();
            Console.texte("Le code de l'appel n'a pas change d'un caractere. "
                    + "C'est ce que le cours appelle « le contrat unique » : "
                    + "`ChatModel` est une interface, et passer d'OpenAI a "
                    + "Ollama ou a un modele maison revient a changer l'objet "
                    + "passe a `AiServices` — une dependance et une "
                    + "propriete, pas une ligne de votre code.");
            System.out.println();
            Console.texte("⚠️ Ce que l'abstraction ne transporte PAS : les "
                    + "options propres a chaque fournisseur, les limites de "
                    + "contexte, la facon dont chaque modele obeit a un "
                    + "prompt systeme, et surtout ce qu'il sait faire — le "
                    + "chapitre 2 montre qu'une seule capacite declaree change "
                    + "tout le prompt.");

            Console.titre(4, "CE QUE LE MODELE EST, VU DE LANGCHAIN4J");
            Console.ligne("l'interface implementee",
                    ChatModel.class.getSimpleName(), 30);
            Console.ligne("methodes a ecrire", "une seule : `doChat`", 30);
            Console.ligne("capacites declarees",
                    modele.supportedCapabilities().isEmpty() ? "aucune"
                            : String.valueOf(modele.supportedCapabilities()), 30);
            Console.ligne("appels au modele depuis le debut",
                    String.valueOf(modele.appels()), 34);
            System.out.println();
            Console.texte("⚠️ `doChat`, et non `chat`. Les deux existent sur "
                    + "l'interface, et l'exemple du chapitre 6 du cours "
                    + "redefinit `chat(ChatRequest)`. Or `chat` est la "
                    + "methode ENVELOPPE : c'est elle qui previent les "
                    + "`ChatModelListener` avant et apres l'appel. La "
                    + "redefinir desactive toute l'observabilite du "
                    + "chapitre 6, sans erreur et sans message. Le chapitre 6 "
                    + "de ce projet le mesure.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Ce qu'un type de retour `record` ajoute au prompt — "
                    + "et les DEUX facons dont LangChain4j impose un format, "
                    + "selon ce que le modele declare savoir faire.");
            System.out.println();
        }
    }
}
