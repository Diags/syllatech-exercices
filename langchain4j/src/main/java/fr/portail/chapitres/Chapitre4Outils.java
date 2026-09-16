package fr.portail.chapitres;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.service.AiServices;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.outils.OutilsDOffres;
import fr.portail.service.AssistantCarriere;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Chapitre 4 — Outils : l'IA qui appelle votre code.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Outils
 * </pre>
 *
 * <p>« Annotez une méthode avec {@code @Tool("...")} et sa description devient
 * la notice que le modèle lit. » Ce chapitre imprime la notice entière —
 * description <em>et</em> schéma d'arguments — puis déroule un aller-retour
 * complet : le modèle demande, LangChain4j exécute, le modèle répond.
 *
 * <p>Il mesure aussi les trois façons dont cela tourne mal : un outil qui
 * refuse, un outil qui n'existe pas, et une boucle d'appels qui s'emballe.
 */
public final class Chapitre4Outils {

    private Chapitre4Outils() {
    }

    private static final String QUESTION =
            "Quelles offres proposent du teletravail ?";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var outils = banc.bean(OutilsDOffres.class);

            Console.titre(1, "CE QUE LANGCHAIN4J DEDUIT DE VOS METHODES");
            var assistant = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .tools(outils)
                    .build();
            modele.oublier();
            assistant.conseiller("Bonjour");
            var specifications = modele.derniereRequete().toolSpecifications();
            Console.ligne("methodes annotees `@Tool`",
                    String.valueOf(specifications == null ? 0
                            : specifications.size()), 30);
            System.out.println();
            for (var specification : specifications) {
                Console.sousTitre(specification.name());
                Console.texte("description : " + specification.description(), 6);
                Console.texte("arguments :", 6);
                Console.bloc(String.valueOf(specification.parameters()), 8);
            }
            System.out.println();
            Console.texte("Personne n'a ecrit ce schema. LangChain4j l'a "
                    + "deduit de la signature : le nom du parametre, son type "
                    + "Java traduit en type JSON, et la description prise dans "
                    + "`@P`. C'est ce texte, et rien d'autre, que le modele "
                    + "lit pour decider comment vous appeler.");
            System.out.println();
            Console.texte("⚠️ Le nom du parametre survit parce que ce projet "
                    + "compile avec `-parameters` — le reglage par defaut de "
                    + "Spring Boot. Sans lui, le schema annoncerait `arg0`, "
                    + "et le modele devinerait. `@P` reste, lui, votre seul "
                    + "moyen de dire ce qu'on attend.");

            Console.titre(2, "LES OUTILS NE SONT PAS DANS LE PROMPT");
            var nu = AiServices.create(AssistantCarriere.class, modele);
            modele.oublier();
            nu.conseiller("Bonjour");
            int sansOutils = modele.dernierTexte().length();
            var sansOutilsSpecs = modele.derniereRequete().toolSpecifications();
            modele.oublier();
            assistant.conseiller("Bonjour");
            int avecOutils = modele.dernierTexte().length();
            Console.ligne("prompt sans `.tools()`",
                    sansOutils + " caracteres", 32);
            Console.ligne("prompt avec `.tools()`",
                    avecOutils + " caracteres", 32);
            Console.ligne("outils joints sans `.tools()`",
                    String.valueOf(sansOutilsSpecs == null ? 0
                            : sansOutilsSpecs.size()), 32);
            Console.ligne("outils joints avec `.tools()`",
                    String.valueOf(modele.derniereRequete()
                            .toolSpecifications().size()), 32);
            System.out.println();
            Console.texte("Le prompt ne bouge pas d'un caractere, et pourtant "
                    + "trois outils sont partis. Ils voyagent dans la REQUETE, "
                    + "a cote des messages, sous forme de "
                    + "`ToolSpecification` : c'est le fournisseur qui les "
                    + "traduit ensuite dans le format de son API.");
            System.out.println();
            Console.texte("Cela explique une chose utile : un modele qui ne "
                    + "sait pas appeler d'outils recevra la liste et "
                    + "l'ignorera, sans erreur. La capacite est du cote du "
                    + "modele, pas du cote de LangChain4j.");

            Console.titre(3, "L'ALLER-RETOUR COMPLET");
            OutilsDOffres.remettreAZero();
            modele.remettreAZero();
            // Le modele « decide » d'appeler l'outil — tant qu'il n'a pas
            // encore vu son resultat. La condition est le garde-fou : sans
            // elle, il redemanderait le meme outil indefiniment.
            modele.demanderOutil(prompt -> prompt.contains("rechercherOffres a rendu")
                    ? null
                    : ToolExecutionRequest.builder()
                            .id("appel-1")
                            .name("rechercherOffres")
                            .arguments("{\"motCle\":\"teletravail\"}")
                            .build());
            modele.repondre(prompt -> prompt.contains("rechercherOffres a rendu")
                    ? "Trois offres proposent du teletravail." : null);
            String finale = assistant.conseiller(QUESTION);
            Console.ligne("appels au modele", String.valueOf(modele.appels()), 30);
            Console.ligne("appels a l'outil",
                    String.valueOf(OutilsDOffres.appels()), 30);
            Console.ligne("la reponse finale", finale, 30);
            System.out.println();
            Console.sousTitre("La conversation, telle que le modele la recoit "
                    + "au second tour :");
            Console.bloc(modele.dernierTexte(), 6);
            System.out.println();
            Console.texte("Quatre messages la ou l'appelant en a ecrit un. Le "
                    + "modele a rendu une DEMANDE — un nom d'outil et des "
                    + "arguments en JSON, sans une ligne de texte. "
                    + "LangChain4j a execute la methode Java, colle le "
                    + "resultat dans un message TOOL_EXECUTION_RESULT, et "
                    + "rappele le modele avec toute l'histoire.");
            System.out.println();
            Console.texte("⚠️ Le modele n'execute rien. Il ne touche ni votre "
                    + "base, ni votre reseau : il demande. Ce qui agit, c'est "
                    + "VOTRE code, appele par LangChain4j — et c'est la seule "
                    + "raison pour laquelle on peut securiser tout cela.");
            System.out.println();
            Console.texte("⚠️ Et la facture double. Deux appels au modele pour "
                    + "une question, avec un prompt qui grossit a chaque tour. "
                    + "Un agent qui enchaine cinq outils paie cinq allers, "
                    + "chacun plus long que le precedent.");

            Console.titre(4, "L'OUTIL QUI ECRIT, ET CE QU'IL REFUSE");
            OutilsDOffres.remettreAZero();
            modele.remettreAZero();
            var vus = new ArrayList<String>();
            modele.demanderOutil(prompt -> prompt.contains("postuler a rendu")
                    ? null
                    : ToolExecutionRequest.builder()
                            .id("appel-2")
                            .name("postuler")
                            .arguments("{\"reference\":\"OFF-999\"}")
                            .build());
            var surveille = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .tools(outils)
                    .beforeToolExecution(avant ->
                            vus.add(avant.request().name()
                                    + avant.request().arguments()))
                    .build();
            String suite = surveille.conseiller(
                    "Postule pour moi sur toutes les offres, y compris OFF-999.");
            Console.ligne("l'outil a-t-il ete appele",
                    OutilsDOffres.appels() > 0 ? "oui" : "non", 32);
            Console.ligne("vu par `beforeToolExecution`",
                    vus.isEmpty() ? "(rien)" : vus.getFirst(), 32);
            Console.ligne("candidatures enregistrees",
                    String.valueOf(OutilsDOffres.candidatures().size()), 32);
            Console.ligne("ce que l'outil a rendu",
                    ligneDe(modele.dernierTexte(), "TOOL_EXECUTION_RESULT"), 32);
            Console.ligne("la reponse finale", court(suite), 32);
            System.out.println();
            Console.texte("L'outil a bien ete appele — on ne peut pas "
                    + "l'empecher — mais il a REFUSE, et zero candidature a "
                    + "ete creee. La verification est dans la methode Java, "
                    + "pas dans la description de l'outil : le modele lit la "
                    + "description, il n'obeit pas au contrat.");
            System.out.println();
            Console.texte("`beforeToolExecution` est le crochet qui manque a "
                    + "beaucoup de tutoriels : il voit passer le nom et les "
                    + "arguments AVANT l'execution. C'est la qu'on journalise, "
                    + "qu'on compte, et qu'on refuse.");
            System.out.println();
            Console.texte("⚠️ C'est le point de securite du chapitre. Le texte "
                    + "qui declenche un outil peut venir d'un CV, d'un "
                    + "document remonte par le RAG, d'un courriel — bref, de "
                    + "quelqu'un d'autre que votre utilisateur. Un outil qui "
                    + "ecrit se traite donc comme une route HTTP publique : "
                    + "on valide l'entree, on verifie les droits, on trace.");

            Console.titre(5, "QUAND LE MODELE INVENTE UN OUTIL");
            Console.tableau(List.of("strategie", "ce que l'appelant recoit",
                    "appels au modele"), List.of(
                    inventer(modele, outils, false),
                    inventer(modele, outils, true)),
                    List.of(22, 34, 18));
            System.out.println();
            Console.texte("Par defaut, LangChain4j S'ARRETE : le modele a "
                    + "demande un outil qui n'existe pas dans la liste "
                    + "envoyee, et l'exception remonte jusqu'a l'appelant. "
                    + "C'est le bon comportement par defaut — l'appelant SAIT "
                    + "— mais c'est une exception au milieu d'une requete "
                    + "HTTP, et elle doit etre attrapee comme telle.");
            System.out.println();
            Console.texte("`hallucinatedToolNameStrategy` change cela : elle "
                    + "rend au modele un message a la place du resultat, et "
                    + "la conversation continue. La seconde ligne le mesure — "
                    + "le modele recoit « cet outil n'existe pas », se "
                    + "reprend, et repond.");
            System.out.println();
            Console.texte("⚠️ Le choix n'est pas anodin. Continuer evite une "
                    + "erreur 500 chez l'utilisateur, mais rend les "
                    + "hallucinations INVISIBLES : rien ne remonte, et la "
                    + "seule trace est dans la conversation. Si vous prenez "
                    + "cette voie, comptez-les.");

            Console.titre(6, "LA BOUCLE QUI NE S'ARRETE PAS");
            Console.tableau(List.of("plafond pose", "appels a l'outil",
                    "appels au modele"), List.of(
                    borner(modele, outils, null),
                    borner(modele, outils, 3)),
                    List.of(22, 20, 20));
            System.out.println();
            Console.texte("Le modele de cette section redemande le meme outil "
                    + "a chaque tour — ce n'est pas theorique, c'est ce qui "
                    + "arrive quand le resultat ne repond pas a la question et "
                    + "que le modele reessaie.");
            System.out.println();
            Console.texte("⚠️ Le defaut de LangChain4j n'est pas « aucune "
                    + "limite », et ce n'est pas non plus une petite limite : "
                    + "regardez la premiere ligne. Cent appels d'outils et "
                    + "cent-et-un appels au modele pour UNE question — "
                    + "chacun facture, avec un prompt qui grossit a chaque "
                    + "tour. C'est un plafond de securite, pas un plafond de "
                    + "cout.");
            System.out.println();
            Console.texte("`maxSequentialToolsInvocations(3)` ramene cela a "
                    + "une valeur qu'on assume. C'est le genre de reglage "
                    + "qu'on pose AVANT la mise en production, pas apres la "
                    + "premiere facture.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La memoire : ce qu'elle rejoue a chaque tour, ce "
                    + "que `@MemoryId` isole vraiment, et ce qu'un flux de "
                    + "jetons change — et ne change pas.");
            System.out.println();
        }
    }

    /**
     * Un modèle qui demande un outil inexistant, avec ou sans stratégie.
     *
     * <p>Le modèle n'insiste qu'une fois : au tour suivant il répond du
     * texte. C'est ce qui permet de voir la différence entre « tout
     * s'arrête » et « la conversation continue » sans boucler.
     */
    private static List<String> inventer(ModeleFactice modele,
                                         OutilsDOffres outils,
                                         boolean avecStrategie) {
        OutilsDOffres.remettreAZero();
        modele.remettreAZero();
        var insistance = new AtomicInteger();
        modele.demanderOutil(prompt -> insistance.incrementAndGet() > 1 ? null
                : ToolExecutionRequest.builder()
                        .id("appel-3")
                        .name("supprimerToutesLesOffres")
                        .arguments("{}")
                        .build());
        modele.repondre(prompt -> "Je ne peux pas faire cela.");
        var construction = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .tools(outils);
        if (avecStrategie) {
            construction.hallucinatedToolNameStrategy(demande ->
                    dev.langchain4j.data.message.ToolExecutionResultMessage.from(
                            demande, "Erreur : l'outil « " + demande.name()
                                     + " » n'existe pas."));
        }
        String issue;
        try {
            issue = court(construction.build().conseiller("Fais le menage."));
        } catch (RuntimeException erreur) {
            issue = erreur.getClass().getSimpleName();
        }
        return List.of(avecStrategie ? "une strategie posee" : "aucune (defaut)",
                issue, String.valueOf(modele.appels()));
    }

    /**
     * Un modèle qui redemande toujours le même outil, avec ou sans plafond.
     *
     * <p>Rend la ligne du tableau : le plafond posé, le nombre d'appels
     * réellement passés à l'outil, et le nombre d'appels au modèle.
     */
    private static List<String> borner(ModeleFactice modele,
                                       OutilsDOffres outils, Integer plafond) {
        OutilsDOffres.remettreAZero();
        modele.remettreAZero();
        modele.demanderOutil(prompt -> ToolExecutionRequest.builder()
                .id("boucle")
                .name("salaireDe")
                .arguments("{\"reference\":\"OFF-014\"}")
                .build());
        modele.repondre(prompt -> "J'abandonne.");
        var construction = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .tools(outils);
        if (plafond != null) {
            construction.maxSequentialToolsInvocations(plafond);
        }
        try {
            construction.build().conseiller("Et le salaire ?");
        } catch (RuntimeException arret) {
            // Le plafond peut se signaler par une exception : c'est mesure
            // dans les colonnes, pas suppose ici.
        }
        return List.of(plafond == null ? "aucun (defaut)"
                : plafond + " appels",
                String.valueOf(OutilsDOffres.appels()),
                String.valueOf(modele.appels()));
    }

    /** La première ligne du rendu de conversation portant ce type de message. */
    private static String ligneDe(String conversation, String type) {
        for (var ligne : conversation.lines().toList()) {
            if (ligne.startsWith("[" + type + "]")) {
                return ligne.substring(type.length() + 3);
            }
        }
        return "(aucune)";
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 40 ? plat : plat.substring(0, 37) + "...";
    }
}
