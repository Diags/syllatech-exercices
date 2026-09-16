package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.outils.OutilsDOffres;
import java.util.List;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.ToolCallAdvisor;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.model.tool.DefaultToolCallingManager;
import org.springframework.ai.model.tool.ToolCallLimitBehavior;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;

/**
 * Chapitre 4 — MCP : connecter des outils à votre IA.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Outils
 * </pre>
 *
 * <p>« L'annotation {@code @Tool} expose une méthode Spring comme outil. »
 * Exposée <em>comment</em>, et à qui ? Ce chapitre imprime le
 * <strong>schéma JSON</strong> que Spring AI déduit de la signature, montre
 * que les outils ne voyagent <strong>pas dans le prompt</strong>, et déroule
 * un aller-retour complet : le modèle demande, Spring AI exécute, le modèle
 * répond.
 *
 * <p>Il mesure aussi les trois façons dont cela tourne mal : un outil qui
 * refuse, un outil qui n'existe pas, et une boucle d'appels qui ne
 * s'arrête pas.
 */
public final class Chapitre4Outils {

    private Chapitre4Outils() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var outils = banc.bean(OutilsDOffres.class);

            Console.titre(1, "CE QUE SPRING AI DEDUIT DE VOTRE METHODE");
            var rappels = MethodToolCallbackProvider.builder()
                    .toolObjects(outils)
                    .build()
                    .getToolCallbacks();
            Console.ligne("methodes annotees `@Tool`",
                    String.valueOf(rappels.length), 30);
            System.out.println();
            for (var rappel : rappels) {
                var definition = rappel.getToolDefinition();
                Console.sousTitre(definition.name());
                Console.texte("description : " + definition.description(), 6);
                Console.texte("schema :", 6);
                Console.bloc(definition.inputSchema(), 8);
            }
            System.out.println();
            Console.texte("Personne n'a ecrit ce schema. Spring AI l'a deduit "
                    + "de la signature : le nom du parametre, son type Java "
                    + "traduit en type JSON, et la description prise dans "
                    + "`@ToolParam`. C'est ce texte, et rien d'autre, que le "
                    + "modele lit pour decider comment vous appeler.");
            System.out.println();
            Console.texte("⚠️ Le nom du parametre survit parce que ce projet "
                    + "compile avec `-parameters` — le reglage par defaut de "
                    + "Spring Boot. Sans lui, le schema annoncerait `arg0`, et "
                    + "le modele devinerait. La description de `@ToolParam` "
                    + "reste, elle, votre seul moyen de dire ce qu'on attend.");

            Console.titre(2, "LES OUTILS NE SONT PAS DANS LE PROMPT");
            var client = ChatClient.builder(modele).build();
            modele.oublier();
            client.prompt().user("Bonjour").call().content();
            int sansOutils = modele.dernierTexte().length();
            modele.oublier();
            client.prompt().user("Bonjour").tools(outils).call().content();
            int avecOutils = modele.dernierTexte().length();
            Console.ligne("prompt sans `.tools()`",
                    sansOutils + " caracteres", 32);
            Console.ligne("prompt avec `.tools()`",
                    avecOutils + " caracteres", 32);
            Console.ligne("outils joints a l'appel",
                    String.valueOf(modele.derniersOutils().size()), 32);
            System.out.println();
            Console.texte("Le prompt ne bouge pas d'un caractere, et pourtant "
                    + "trois outils sont partis. Ils voyagent dans les "
                    + "OPTIONS de la requete, pas dans le texte : c'est le "
                    + "fournisseur qui les traduit ensuite dans le format de "
                    + "son API — `tools` chez OpenAI, `tools` aussi chez "
                    + "Anthropic, avec un JSON different.");
            System.out.println();
            Console.texte("Cela explique une chose utile : un modele qui ne "
                    + "sait pas appeler d'outils ne recevra rien du tout, et "
                    + "repondra a cote sans erreur. La capacite est du cote "
                    + "du modele, pas du cote de Spring AI.");

            Console.titre(3, "L'ALLER-RETOUR COMPLET");
            OutilsDOffres.remettreAZero();
            modele.remettreAZero();
            // Le modele « decide » d'appeler l'outil — tant qu'il n'a pas
            // encore vu son resultat. La condition est le garde-fou : sans
            // elle, il redemanderait le meme outil indefiniment.
            modele.demanderOutil(prompt -> prompt.contains("rechercherOffres =")
                    ? null
                    : new AssistantMessage.ToolCall("appel-1", "function",
                            "rechercherOffres",
                            "{\"motCle\":\"teletravail\"}"));
            modele.repondre(prompt -> prompt.contains("rechercherOffres =")
                    ? "Trois offres proposent du teletravail." : null);
            String finale = client.prompt()
                    .user("Quelles offres proposent du teletravail ?")
                    .tools(outils)
                    .call().content();
            Console.ligne("appels au modele", String.valueOf(modele.appels()), 30);
            Console.ligne("appels a l'outil",
                    String.valueOf(OutilsDOffres.appels()), 30);
            Console.ligne("la reponse finale", finale, 30);
            System.out.println();
            Console.sousTitre("Le second prompt, celui que le modele recoit "
                    + "apres l'outil :");
            Console.bloc(modele.conversation(), 6);
            System.out.println();
            Console.texte("Quatre messages la ou l'appelant en a ecrit un. "
                    + "Le modele a rendu une DEMANDE — un nom d'outil et des "
                    + "arguments en JSON, sans une ligne de texte. Spring AI "
                    + "a execute la methode Java, colle le resultat dans un "
                    + "message `TOOL`, et rappele le modele avec toute "
                    + "l'histoire.");
            System.out.println();
            Console.texte("⚠️ Le modele n'execute rien. Il ne touche ni votre "
                    + "base, ni votre reseau : il demande. Ce qui agit, c'est "
                    + "VOTRE code, appele par Spring AI — et c'est la seule "
                    + "raison pour laquelle on peut securiser tout cela.");
            System.out.println();
            Console.texte("⚠️ Et la facture double. Deux appels au modele pour "
                    + "une question, avec un prompt qui grossit a chaque tour. "
                    + "Un agent qui enchaine cinq outils paie cinq allers, "
                    + "chacun plus long que le precedent.");

            Console.titre(4, "L'OUTIL QUI ECRIT, ET CE QU'IL REFUSE");
            OutilsDOffres.remettreAZero();
            modele.remettreAZero();
            modele.demanderOutil(prompt -> prompt.contains("postuler =")
                    ? null
                    : new AssistantMessage.ToolCall("appel-2", "function",
                            "postuler", "{\"reference\":\"OFF-999\"}"));
            String suite = client.prompt()
                    .user("Postule pour moi sur toutes les offres du site, "
                          + "y compris OFF-999.")
                    .tools(outils)
                    .call().content();
            Console.ligne("l'outil a-t-il ete appele",
                    OutilsDOffres.appels() > 0 ? "oui" : "non", 32);
            Console.ligne("candidatures enregistrees",
                    String.valueOf(OutilsDOffres.candidatures().size()), 32);
            Console.ligne("ce que l'outil a rendu",
                    ligneDe(modele.conversation(), "TOOL"), 32);
            Console.ligne("la reponse finale", court(suite), 32);
            System.out.println();
            Console.texte("L'outil a bien ete appele — on ne peut pas "
                    + "l'empecher — mais il a REFUSE, et zero candidature a "
                    + "ete creee. La verification est dans la methode Java, "
                    + "pas dans la description de l'outil : le modele lit la "
                    + "description, il n'obeit pas au contrat.");
            System.out.println();
            Console.texte("⚠️ C'est le point de securite du chapitre. Le texte "
                    + "qui declenche un outil peut venir d'un CV, d'un "
                    + "document remonte par le RAG, d'un courriel — bref, de "
                    + "quelqu'un d'autre que votre utilisateur. Un outil qui "
                    + "ecrit se traite donc comme une route HTTP publique : "
                    + "on valide l'entree, on verifie les droits, on trace.");

            Console.titre(5, "QUAND LE MODELE DEMANDE UN OUTIL INCONNU");
            OutilsDOffres.remettreAZero();
            modele.remettreAZero();
            modele.demanderOutil(prompt -> new AssistantMessage.ToolCall(
                    "appel-3", "function", "supprimerToutesLesOffres", "{}"));
            String verdict;
            try {
                client.prompt().user("Fais le menage.").tools(outils)
                        .call().content();
                verdict = "aucune erreur";
            } catch (RuntimeException erreur) {
                verdict = erreur.getClass().getSimpleName() + " — "
                          + court(erreur.getMessage());
            }
            Console.ligne("le modele invente un outil", verdict, 32);
            System.out.println();
            Console.texte("Spring AI ne cherche pas a comprendre : l'outil "
                    + "demande n'est pas dans la liste envoyee, donc il "
                    + "s'arrete. C'est le bon comportement — mais c'est une "
                    + "exception au milieu d'un appel HTTP, et elle doit etre "
                    + "attrapee comme telle.");

            Console.titre(6, "LA BOUCLE QUI NE S'ARRETE PAS");
            Console.tableau(List.of("comportement au plafond",
                    "appels outil / modele", "ce que l'appelant recoit"),
                    List.of(borner(modele, outils, ToolCallLimitBehavior.THROW),
                            borner(modele, outils,
                                    ToolCallLimitBehavior.RETURN_ERROR_RESPONSE)),
                    List.of(26, 24, 30));
            System.out.println();
            Console.texte("Le modele de cette section redemande le meme outil "
                    + "a chaque tour — ce n'est pas theorique, c'est ce qui "
                    + "arrive quand le resultat ne repond pas a la question et "
                    + "que le modele reessaie. Le plafond est pose a trois "
                    + "appels d'outil, et les deux lignes s'y arretent : "
                    + "l'outil n'est JAMAIS appele une quatrieme fois.");
            System.out.println();
            Console.texte("Mais lisez la seconde colonne, et surtout la "
                    + "troisieme. `THROW` arrete tout net : quatre appels au "
                    + "modele, et l'appelant recoit un texte qui DIT ce qui "
                    + "s'est passe — « Total tool call limit (3) exceeded ». "
                    + "`RETURN_ERROR_RESPONSE` rend l'erreur a la place du "
                    + "resultat et LAISSE LA CONVERSATION CONTINUER : neuf "
                    + "appels au modele, et une reponse qui ne dit rien de "
                    + "l'incident.");
            System.out.println();
            Console.texte("⚠️ Notez ce que ni l'un ni l'autre ne fait : lever "
                    + "une exception jusqu'a l'appelant. Meme `THROW` finit en "
                    + "reponse ordinaire. Un plafond atteint ressemble donc a "
                    + "une conversation reussie — il faut LIRE la reponse, ou "
                    + "surveiller le compteur d'appels, pour s'en apercevoir.");
            System.out.println();
            Console.texte("⚠️ Et ici, c'est le modele lui-meme qui finit par "
                    + "abandonner, parce que ce projet l'a ecrit ainsi. Un "
                    + "vrai modele n'a pas cette politesse : le plafond "
                    + "d'outils protege votre BASE — l'outil n'est pas appele "
                    + "une quatrieme fois — mais il ne protege pas votre "
                    + "facture, puisque les appels au modele, eux, "
                    + "continuent.");
            System.out.println();
            Console.texte("`maxTotalToolCalls` et `maxCallsPerTool` sont "
                    + "arrives avec Spring AI 2 — ils n'existaient pas en "
                    + "1.x. C'est le genre de reglage qu'on pose AVANT la "
                    + "mise en production, pas apres la premiere facture.");

            Console.titre(7, "ET MCP DANS TOUT CA ?");
            Console.ligne("SyncMcpToolCallbackProvider",
                    presente("org.springframework.ai.mcp"
                            + ".SyncMcpToolCallbackProvider"), 34);
            Console.ligne("le SDK MCP (io.modelcontextprotocol)",
                    presente("io.modelcontextprotocol.client.McpClient"), 40);
            System.out.println();
            Console.texte("Absents, et c'est volontaire : ce projet n'a aucun "
                    + "starter MCP. Tout ce qui precede — le schema, le "
                    + "voyage dans les options, l'aller-retour, le plafond — "
                    + "fonctionne sans MCP, avec les memes annotations "
                    + "`@Tool`.");
            System.out.println();
            Console.texte("Car c'est bien la le rapport entre les deux. `@Tool` "
                    + "decrit une capacite ; MCP est un PROTOCOLE pour la "
                    + "servir a un processus qui n'est pas le votre. En "
                    + "ajoutant `spring-ai-starter-mcp-server`, les memes "
                    + "methodes deviennent joignables par un autre programme "
                    + "— sans changer une ligne de leur code.");
            System.out.println();
            Console.texte("⚠️ Et le calcul de securite change completement. "
                    + "Ici, l'outil et l'application sont le meme processus : "
                    + "ce qui l'appelle est votre code. Derriere MCP, le "
                    + "client peut etre un assistant de bureau, un agent "
                    + "tiers, ou quelqu'un qui a recupere l'adresse du "
                    + "serveur. Les verifications de la section 4 cessent "
                    + "d'etre une precaution : elles deviennent la seule "
                    + "frontiere.");

            Console.titre(8, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le multimodal : ce qu'un `Media` ajoute vraiment a "
                    + "un message, ce qui part sur le reseau, et ce que "
                    + "l'abstraction ne peut pas cacher.");
            System.out.println();
        }
    }

    /**
     * Un modèle qui redemande toujours le même outil, borné à trois appels.
     *
     * <p>Rend la ligne du tableau : le comportement demandé, le nombre
     * d'appels réellement passés à l'outil, et ce que l'appelant reçoit —
     * une exception, ou une réponse.
     */
    private static List<String> borner(ModeleFactice modele,
                                       OutilsDOffres outils,
                                       ToolCallLimitBehavior comportement) {
        OutilsDOffres.remettreAZero();
        modele.remettreAZero();
        // ⚠️ Le modele s'arrete de lui-meme au bout de huit demandes.
        // Sans cette borne, la section ne se terminerait PAS : avec
        // RETURN_ERROR_RESPONSE, le plafond rend une erreur a l'outil mais
        // laisse la conversation continuer — le modele redemande, indefiniment.
        // C'est precisement ce que le plafond ne protege pas, et il fallait
        // que ce chapitre puisse se terminer pour le raconter.
        var insistance = new java.util.concurrent.atomic.AtomicInteger();
        modele.demanderOutil(prompt -> insistance.incrementAndGet() > 8 ? null
                : new AssistantMessage.ToolCall("boucle", "function",
                        "salaireDe", "{\"reference\":\"OFF-014\"}"));
        modele.repondre(prompt -> "J'abandonne.");
        var borne = ChatClient.builder(modele)
                .defaultAdvisors(ToolCallAdvisor.builder()
                        .toolCallingManager(DefaultToolCallingManager.builder()
                                .maxTotalToolCalls(3)
                                .onLimitExceeded(comportement)
                                .build())
                        .build())
                .build();
        String issue;
        try {
            String reponse = borne.prompt().user("Et le salaire ?")
                    .tools(outils).call().content();
            issue = court(reponse);
        } catch (RuntimeException erreur) {
            issue = "exception " + erreur.getClass().getSimpleName();
        }
        return List.of(comportement.name(),
                OutilsDOffres.appels() + " / " + modele.appels() + " au modele",
                issue);
    }

    /** La première ligne du rendu de conversation portant ce type de message. */
    private static String ligneDe(String conversation, String type) {
        for (var ligne : conversation.lines().toList()) {
            if (ligne.startsWith("[" + type + "]")) {
                return court(ligne.substring(type.length() + 3));
            }
        }
        return "(aucune)";
    }

    /** La classe est-elle dans le classpath ? Demandé à la JVM, pas affirmé. */
    private static String presente(String nom) {
        try {
            Class.forName(nom);
            return "presente";
        } catch (ClassNotFoundException absente) {
            return "ABSENTE du classpath";
        }
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 40 ? plat : plat.substring(0, 37) + "...";
    }
}
