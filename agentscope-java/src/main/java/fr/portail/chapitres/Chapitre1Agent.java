package fr.portail.chapitres;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.message.Msg;
import io.agentscope.core.tool.Toolkit;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 1 — Demarrer avec AgentScope Java.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Agent
 * </pre>
 *
 * <p>« Appeler un LLM » et « faire tourner un agent » ne sont pas la meme
 * chose. Ce chapitre pose LA MEME QUESTION aux deux, et compte : appels au
 * modele, outils reellement executes, et exactitude de la reponse.
 *
 * <p>Puis il separe ce qui est CONFIGURATION (stable, partagee) de ce qui est
 * CONTEXTE (propre a chaque echange) — et montre ce que cette separation
 * garantit : deux sessions ne se melangent pas.
 */
public final class Chapitre1Agent {

    private Chapitre1Agent() {
    }

    /** La question dont la reponse est dans le catalogue, pas dans le modele. */
    private static final String QUESTION =
            "Quelles offres Java proposez-vous, et combien de candidatures "
            + "pour la premiere ?";

    public static void main(String[] args) {
        System.out.println("""
                1. UN APPEL AU MODELE N'EST PAS UN AGENT
                """);

        // -- a gauche : un simple appel. Le modele repond de memoire. -------
        CatalogueOffres catalogueGauche = new CatalogueOffres();
        ModeleFactice modeleSeul = ModeleFactice.quiRepond("factice:sans-outils",
                "Nous proposons des postes Java a Paris et a Lille, "
                + "avec une quarantaine de candidatures chacun.");
        ReActAgent sansOutils = ReActAgent.builder()
                .name("conseiller-sans-outils")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modeleSeul)
                .toolkit(new Toolkit())
                .maxIters(5)
                .build();

        Msg reponseSeule = sansOutils.call(QUESTION, contexte("s-gauche")).block();

        // -- a droite : le meme modele, mais un agent OUTILLE ---------------
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);

        ModeleFactice modeleAgent = new ModeleFactice("factice:outille", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.AppelDOutil("compter_candidatures",
                        Map.of("reference", "OFF-101")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Voici ce que dit le portail :\n"
                        + ModeleFactice.resultatsDOutils(messages))));

        ReActAgent agent = ReActAgent.builder()
                .name("conseiller")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modeleAgent)
                .toolkit(toolkit)
                .maxIters(5)
                .build();

        Msg reponseAgent = agent.call(QUESTION, contexte("s-droite")).block();

        System.out.printf("   %-26s %-22s %s%n",
                          "", "un appel au modele", "un agent ReAct");
        System.out.printf("   %-26s %-22d %d%n", "appels au modele",
                          modeleSeul.appels(), modeleAgent.appels());
        System.out.printf("   %-26s %-22d %d%n", "outils EXECUTES",
                          catalogueGauche.journal().size(),
                          catalogue.journal().size());
        System.out.printf("   %-26s %-22s %s%n", "references reelles citees",
                          compterReferences(texte(reponseSeule)),
                          compterReferences(texte(reponseAgent)));

        System.out.println("\n   Ce que le portail a REELLEMENT execute :");
        System.out.printf("      a gauche : %s%n", catalogueGauche.journal());
        System.out.printf("      a droite : %s%n", catalogue.journal());

        System.out.println("\n   La reponse de l'agent :\n");
        for (String ligne : texte(reponseAgent).split("\\R")) {
            System.out.printf("      %s%n", ligne);
        }

        System.out.println("""

                   ⚠️ A gauche, le modele a repondu — vite, et a cote. Les
                   villes sont inventees, le nombre de candidatures aussi :
                   rien dans la reponse ne vient du portail, parce que rien
                   n'a ete consulte. C'est la forme la plus couteuse de
                   l'erreur, parce qu'elle est PLAUSIBLE.

                   A droite, la boucle ReAct a alterne reflexion, appel
                   d'outil et observation jusqu'a pouvoir repondre. Le
                   modele a ete appele trois fois, pas une — et c'est le
                   prix de l'exactitude.

                   Un agent = modele + boucle + outils + memoire. Les trois
                   derniers termes sont ce qu'AgentScope apporte ; le
                   premier reste interchangeable (chapitre 2).
                """);

        System.out.println("""
                2. CONFIGURATION ET CONTEXTE : POURQUOI ILS SONT SEPARES
                """);
        System.out.println("""
                   L'agent se construit UNE FOIS — un nom, un sysPrompt, un
                   modele, un catalogue d'outils. Le RuntimeContext, lui, est
                   construit a CHAQUE echange : session, utilisateur.

                      ReActAgent agent = ReActAgent.builder()      ← une fois
                          .name("conseiller")
                          .sysPrompt(…).model(…).toolkit(…).build();

                      RuntimeContext ctx = RuntimeContext.builder() ← a chaque
                          .sessionId(…).userId(…).build();            echange

                   Ce n'est pas une preference de style. C'est ce qui permet
                   au MEME agent de servir des milliers d'utilisateurs en
                   parallele — et la mesure suivante dit ce qui se passerait
                   sans cela.
                """);

        ModeleFactice memoire = new ModeleFactice("factice:memoire", List.of(
                new ModeleFactice.Tour.Reponse("Bien note : vous cherchez du Java."),
                new ModeleFactice.Tour.ReponseSelonLHistorique(
                        messages -> "historique recu : " + messages.size()
                                    + " message(s)"),
                new ModeleFactice.Tour.ReponseSelonLHistorique(
                        messages -> "historique recu : " + messages.size()
                                    + " message(s)")));

        ReActAgent partage = ReActAgent.builder()
                .name("conseiller-partage")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(memoire)
                .toolkit(new Toolkit())
                .maxIters(3)
                .build();

        RuntimeContext awa = contexte("session-awa");
        RuntimeContext bilal = contexte("session-bilal");

        partage.call("Je cherche un poste Java.", awa).block();
        Msg suiteAwa = partage.call("Et pour la suite ?", awa).block();
        Msg debutBilal = partage.call("Bonjour !", bilal).block();

        System.out.printf("   %-34s %s%n", "SESSION", "CE QUE LE MODELE A RECU");
        System.out.printf("   %-34s %s%n", "awa, deuxieme message",
                          texte(suiteAwa));
        System.out.printf("   %-34s %s%n", "bilal, premier message",
                          texte(debutBilal));

        System.out.println("""

                   ⚠️ Le MEME objet agent, deux contextes, deux memoires. La
                   deuxieme question d'awa arrive avec l'historique de sa
                   session ; le premier message de bilal arrive avec le sien,
                   et il est plus court — il ne voit rien de la conversation
                   d'awa.

                   C'est la propriete qui rend un agent deployable : sans
                   elle, il faudrait une instance par utilisateur, ou bien
                   les conversations fuiraient les unes dans les autres.
                """);

        System.out.println("""
                3. CE QUI RESTE EN JAVA, ET CE QUE CELA CHANGE
                """);
        System.out.printf("      modele                 : %s%n",
                          modeleAgent.getModelName());
        System.out.printf("      outils du catalogue    : %s%n",
                          toolkit.getToolNames());
        System.out.printf("      offres au catalogue    : %d%n",
                          catalogue.nombreDOffres());
        System.out.println("""

                   Les outils sont de vraies methodes Java annotees, dans une
                   classe ordinaire du projet. Pas de service Python a
                   deployer, pas de passerelle a maintenir : l'agent appelle
                   VOTRE code, avec vos types, dans votre JVM.

                   ⚠️ Et c'est bien la boucle qui est le sujet : le chapitre 2
                   remplace le modele sans toucher ni au sysPrompt ni aux
                   outils.
                """);
    }

    static RuntimeContext contexte(String session) {
        return RuntimeContext.builder()
                .sessionId(session)
                .userId("diaguily")
                .build();
    }

    static String texte(Msg message) {
        return message == null ? "(aucune reponse)" : message.getTextContent();
    }

    /** Combien de references OFF-xxx reelles la reponse cite-t-elle ? */
    private static String compterReferences(String reponse) {
        long compte = java.util.regex.Pattern.compile("OFF-\\d{3}")
                .matcher(reponse).results().count();
        return compte == 0 ? "0 (aucune)" : String.valueOf(compte);
    }
}
