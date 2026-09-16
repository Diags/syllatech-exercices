package fr.portail.chapitres;

import fr.portail.modele.ModeleFactice;
import fr.portail.observabilite.JournalDeMiddleware;
import fr.portail.outils.CatalogueOffres;
import fr.portail.web.ApplicationPortail;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.state.AgentState;
import io.agentscope.core.state.AgentStateStore;
import io.agentscope.core.state.JsonFileAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * Chapitre 6 — Integrer dans un projet existant.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Integrer
 * </pre>
 *
 * <p>Une VRAIE application Spring Boot demarre ici, sur un port libre, et on
 * l'interroge en HTTP puis en Server-Sent Events. Puis la mesure qui compte
 * pour la production : l'etat d'une conversation survit-il au redemarrage ?
 */
public final class Chapitre6Integrer {

    private Chapitre6Integrer() {
    }

    public static void main(String[] args) throws Exception {
        System.out.println("""
                1. L'AGENT EST UN BEAN, ET LE CONTROLEUR NE SAIT RIEN DE LUI
                """);

        try (ConfigurableApplicationContext contexte = demarrer()) {
            Environment environnement = contexte.getEnvironment();
            String url = "http://localhost:"
                         + environnement.getProperty("local.server.port", "0");
            WebClient client = WebClient.create(url);

            System.out.printf("   Le portail ecoute sur %s%n%n", url);
            System.out.println("""
                       Cote application, l'integration tient en deux
                       declarations :

                          @Bean ReActAgent assistantCarriere(
                                  CatalogueOffres catalogue, …) { … }

                          AssistantControleur(ReActAgent agent) { … }

                       Le controleur recoit l'agent par injection. Il ne
                       construit rien, ne choisit pas de modele, et ne
                       connait aucun outil.
                    """);

            String reponse = client.get()
                    .uri(builder -> builder.path("/assistant")
                            .queryParam("q", "Quelles offres Java ?")
                            .queryParam("session", "awa").build())
                    .retrieve().bodyToMono(String.class)
                    .block(Duration.ofSeconds(30));

            System.out.println("   GET /assistant?q=… →\n");
            for (String ligne : String.valueOf(reponse).split("\\R")) {
                System.out.printf("      %s%n", ligne);
            }

            System.out.printf("%n   beans en jeu : %s%n",
                    List.of(contexte.getBeanNamesForType(ReActAgent.class)));
            System.out.printf("   outils du bean : %s%n",
                    contexte.getBean(ReActAgent.class).getToolkit().getToolNames());

            System.out.println("""

                   ⚠️ Le `CatalogueOffres` est un bean ORDINAIRE, ecrit avant
                   qu'il soit question d'agents. Il n'implemente aucune
                   interface du framework et ne sait pas qu'il est devenu un
                   outil. C'est cela, « integrer sans reecrire ».
                """);

            System.out.println("""
                2. LE FLUX D'EVENEMENTS SE MAPPE SUR SSE, SANS PASSERELLE
                """);
            List<String> sse = client.get()
                    .uri(builder -> builder.path("/assistant/flux")
                            .queryParam("q", "Quelles offres Java ?")
                            .queryParam("session", "bilal").build())
                    .retrieve()
                    .bodyToFlux(String.class)
                    .take(Duration.ofSeconds(20))
                    .collectList()
                    .block(Duration.ofSeconds(30));

            System.out.printf("      fragments SSE recus : %d%n",
                              sse == null ? 0 : sse.size());
            System.out.println("""

                   Le flux de l'agent est deja un `Flux` : le mapper sur des
                   `ServerSentEvent` tient en une ligne, sans fil
                   d'execution supplementaire ni file intermediaire.

                      return agent.streamEvents(q, ctx)
                          .map(evt -> ServerSentEvent.builder(…)
                              .event(evt.getType().name())
                              .data(evt.toString()).build());

                   ⚠️ Et le TYPE de l'evenement part dans le champ `event:`
                   du protocole. Le navigateur peut donc s'abonner a
                   `TOOL_CALL_START` et afficher « je consulte le
                   catalogue… » au bon moment — pas apres coup, et sans
                   analyser une chaine.
                """);
        }

        System.out.println("""
                3. LA MESURE QUI COMPTE EN PRODUCTION : SURVIVRE AU REDEMARRAGE
                """);

        Path magasin = Files.createTempDirectory("portail-etat");
        AgentStateStore surDisque = new JsonFileAgentStateStore(magasin);

        // -- premiere « instance » : on parle a l'agent ---------------------
        ReActAgent avant = agentAvec(surDisque);
        RuntimeContext ctx = RuntimeContext.builder()
                .sessionId("awa").userId("awa").build();
        avant.call("Je cherche un poste Java.", ctx).block();
        avant.saveAgentState(ctx);
        int messagesAvant = avant.getAgentState(ctx).getContext().size();

        // -- redemarrage : un AUTRE agent, le meme magasin ------------------
        ReActAgent apres = agentAvec(surDisque);
        AgentState retrouve = apres.getAgentState("awa", "awa");
        int messagesApres = retrouve.getContext().size();

        // -- et une memoire qui vit dans le processus -----------------------
        ReActAgent volatil = agentAvec(null);
        volatil.call("Je cherche un poste Java.", ctx).block();
        int volatilAvant = volatil.getAgentState(ctx).getContext().size();
        ReActAgent volatilApres = agentAvec(null);
        int volatilApresRedemarrage =
                volatilApres.getAgentState("awa", "awa").getContext().size();

        System.out.printf("   %-30s %-18s %s%n", "MAGASIN D'ETAT",
                          "MESSAGES AVANT", "APRES REDEMARRAGE");
        System.out.printf("   %-30s %-18d %d%n", "sur disque (fichiers JSON)",
                          messagesAvant, messagesApres);
        System.out.printf("   %-30s %-18d %d%n", "en memoire (le DEFAUT)",
                          volatilAvant, volatilApresRedemarrage);
        System.out.printf("%n      sessions retrouvees sur disque : %s%n",
                          surDisque.listSessionIds("awa"));

        System.out.println("""

                   ⚠️ La deuxieme ligne est le defaut. Un agent dont l'etat
                   vit dans la memoire du processus perd toutes les
                   conversations au redemarrage — et, pire, ne peut pas
                   tourner en plusieurs instances : deux repliques derriere
                   un repartiteur repondent alors a la meme personne sans
                   partager son historique.

                   Ce n'est pas un probleme de confort. C'est ce qui decide
                   si l'agent est DEPLOYABLE.

                   ⚠️ CE QUE CE PROJET NE PROUVE PAS. Le magasin utilise ici
                   ecrit des fichiers JSON, parce qu'un cours ne peut pas
                   exiger une base. En production, c'est PostgreSQL ou Redis
                   — pour la concurrence, les transactions et la duree de
                   vie des sessions. Ce qui est demontre est la propriete :
                   l'etat est EXTERNE au processus, et c'est la seule chose
                   qui compte pour le passage a l'echelle.
                """);

        System.out.println("""
                4. LA MIGRATION EST PROGRESSIVE, ET C'EST UN ARGUMENT
                """);
        System.out.println("""
                   Rien de ce qui precede n'a demande de reecrire le portail.
                   L'ordre qui marche :

                      1. brancher l'agent sur UNE route, en lecture seule
                         (mode `EXPLORE` du chapitre 3) ;
                      2. observer — le middleware du chapitre 5 donne les
                         chiffres : appels au modele, outils demandes,
                         echecs ;
                      3. ouvrir les outils d'ecriture un par un, chacun avec
                         sa regle ;
                      4. externaliser l'etat le jour ou l'on passe a deux
                         instances, pas avant.

                   ⚠️ Et la question a poser avant la premiere ligne : « si
                   ce modele repondait n'importe quoi ce soir, qu'est-ce que
                   cela couterait ? » La reponse dicte les permissions, pas
                   l'inverse.
                """);
    }

    private static ConfigurableApplicationContext demarrer() {
        return new SpringApplicationBuilder(ApplicationPortail.class)
                .properties(Map.of("server.port", "0",
                                   "spring.main.banner-mode", "off",
                                   "logging.level.root", "WARN"))
                .run();
    }

    /** Le meme agent, avec ou sans magasin d'etat externe. */
    private static ReActAgent agentAvec(AgentStateStore magasin) {
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(new CatalogueOffres());
        ReActAgent.Builder constructeur = ReActAgent.builder()
                .name("assistant-carriere")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(new ModeleFactice("factice:etat", List.of(
                        new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                                Map.of("motCle", "java")),
                        new ModeleFactice.Tour.Reponse("Voici les offres Java."))))
                .toolkit(toolkit)
                .maxIters(4)
                .middleware(new JournalDeMiddleware());
        if (magasin != null) {
            constructeur.stateStore(magasin);
        }
        return constructeur.build();
    }
}
