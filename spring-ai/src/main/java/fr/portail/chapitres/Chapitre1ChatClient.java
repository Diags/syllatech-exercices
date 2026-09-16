package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import java.util.List;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatModel;

/**
 * Chapitre 1 — Démarrer avec Spring AI et ChatClient.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1ChatClient
 * </pre>
 *
 * <p>« {@code ChatClient} est l'interface centrale — pensez à
 * {@code RestClient}, mais pour les modèles d'IA. » Ce chapitre ouvre la
 * boîte : le modèle de ce projet <strong>retient</strong> ce qu'on lui
 * envoie, et chaque section imprime le prompt exact que {@code ChatClient} a
 * fabriqué.
 *
 * <p>C'est la seule façon de voir ce que {@code defaultSystem()} ajoute, et
 * ce que le reste du cours ajoutera par-dessus.
 */
public final class Chapitre1ChatClient {

    private Chapitre1ChatClient() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);

            Console.titre(1, "CE QUE LE MODELE RECOIT VRAIMENT");
            var client = ChatClient.builder(modele)
                    .defaultSystem("Tu es un assistant carriere pour un "
                            + "portail d'emploi. Reponds en francais, en "
                            + "trois points au maximum.")
                    .build();
            modele.oublier();
            String reponse = client.prompt()
                    .user("Donne 3 conseils pour decrocher un poste de "
                          + "developpeur Java")
                    .call()
                    .content();
            Console.sousTitre("Les messages envoyes au modele :");
            for (var message : modele.derniersMessages()) {
                Console.texte("[" + message.getMessageType() + "]", 5);
                Console.bloc(message.getText(), 9);
            }
            Console.sousTitre("La reponse :");
            for (var ligne : reponse.lines().toList()) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.texte("Deux messages, et un seul vient de l'appelant. Le "
                    + "message SYSTEME a ete pose par `defaultSystem()`, une "
                    + "fois, a la construction du client — il part avec "
                    + "CHAQUE requete, et c'est ce qui donne a l'assistant sa "
                    + "personnalite sans qu'on ait a la repeter.");
            System.out.println();
            Console.texte("C'est aussi ce qu'on paie : le message systeme est "
                    + "facture a chaque appel. Un prompt systeme de mille "
                    + "mots multiplie par un million d'appels, c'est un "
                    + "million de fois mille mots.");

            Console.titre(2, "LE MEME CODE, UN AUTRE MODELE");
            var autre = new ModeleFactice();
            autre.repondre(texte -> texte.contains("conseils")
                    ? "Reponse d'un second modele, avec un autre style." : null);
            var clientBis = ChatClient.builder(autre)
                    .defaultSystem("Tu es un assistant carriere.")
                    .build();
            Console.ligne("le meme appel, sur le second modele",
                    clientBis.prompt().user("Donne 3 conseils").call()
                            .content().lines().findFirst().orElse(""), 40);
            System.out.println();
            Console.texte("Le code de l'appel n'a pas change d'un caractere. "
                    + "C'est ce que le cours appelle « l'abstraction "
                    + "unifiee » : `ChatClient` parle a un `ChatModel`, et "
                    + "passer d'OpenAI a Anthropic ou a un modele local "
                    + "revient a changer le bean — une dependance et une "
                    + "propriete, pas une ligne de votre code.");
            System.out.println();
            Console.texte("⚠️ Ce que l'abstraction ne transporte PAS : les "
                    + "options propres a chaque fournisseur, les limites de "
                    + "contexte, la facon dont chaque modele obeit a un "
                    + "prompt systeme. Le code compile ; les reponses "
                    + "changent.");

            Console.titre(3, "CE QUE LE CLIENT AJOUTE, ET CE QU'IL N'AJOUTE PAS");
            modele.oublier();
            var nu = ChatClient.builder(modele).build();
            nu.prompt().user("Bonjour").call().content();
            Console.ligne("sans defaultSystem, messages envoyes",
                    String.valueOf(modele.derniersMessages().size()), 40);
            modele.oublier();
            client.prompt().user("Bonjour").call().content();
            Console.ligne("avec defaultSystem, messages envoyes",
                    String.valueOf(modele.derniersMessages().size()), 40);
            System.out.println();
            Console.texte("Un contre deux. `ChatClient` n'ajoute rien de son "
                    + "propre chef : tout ce qui part vient de ce que vous "
                    + "avez declare. Les chapitres suivants ajouteront des "
                    + "instructions de format, un contexte de documents et un "
                    + "historique — et chaque fois, ce compteur montera.");

            Console.titre(4, "LA REPONSE EN FLUX");
            modele.oublier();
            var morceaux = new java.util.ArrayList<String>();
            client.prompt().user("Donne 3 conseils").stream().content()
                    .doOnNext(morceaux::add).blockLast();
            int appelsDuFlux = modele.appels();
            String recolle = String.join("", morceaux);
            modele.oublier();
            String dUnSeulCoup = client.prompt().user("Donne 3 conseils")
                    .call().content();
            Console.ligne("appels au modele pour tout le flux",
                    String.valueOf(appelsDuFlux), 38);
            Console.ligne("morceaux recus", String.valueOf(morceaux.size()), 38);
            Console.ligne("premier morceau",
                    "« " + morceaux.getFirst() + " »", 38);
            Console.ligne("texte recolle = texte d'un coup",
                    recolle.equals(dUnSeulCoup) ? "oui" : "NON", 38);
            System.out.println();
            Console.texte("Le modele de ce projet decoupe sa reponse mot a "
                    + "mot, comme un vrai fournisseur. L'interet est la : "
                    + "l'utilisateur voit le texte arriver au lieu "
                    + "d'attendre la fin, et le premier mot s'affiche "
                    + "pendant que le reste se calcule.");
            System.out.println();
            Console.texte("⚠️ Il a fallu ecrire `stream()` pour cela. "
                    + "L'implementation par defaut de `ChatModel` ne se "
                    + "rabat PAS sur `call()` : elle leve "
                    + "`UnsupportedOperationException`. Un modele qui ne "
                    + "sait pas diffuser doit donc le dire, et l'appelant "
                    + "doit le savoir.");
            System.out.println();
            Console.texte("Ce que le flux ne change pas : le cout, la latence "
                    + "totale, et le fait que la reponse complete n'existe "
                    + "qu'a la fin. `.stream()` ameliore le RESSENTI, pas la "
                    + "mesure.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Ce que `entity()` colle a la fin de votre prompt "
                    + "pour obtenir un objet Java — et ce qui se passe quand "
                    + "le modele n'obeit pas.");
            System.out.println();
        }
    }
}
