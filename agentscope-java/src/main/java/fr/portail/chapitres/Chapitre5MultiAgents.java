package fr.portail.chapitres;

import fr.portail.modele.ModeleFactice;
import fr.portail.observabilite.JournalDeMiddleware;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.message.Msg;
import io.agentscope.core.tool.Toolkit;
import io.agentscope.core.tool.subagent.SubAgentConfig;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 5 — Multi-agents et evenements.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5MultiAgents
 * </pre>
 *
 * <p>Un orchestrateur, deux specialistes, et la mesure qui compte : ce que
 * chaque agent VOIT. Puis un middleware, qui intercepte chaque appel au
 * modele et chaque action — le pendant d'un aspect en AOP.
 */
public final class Chapitre5MultiAgents {

    private Chapitre5MultiAgents() {
    }

    private static final String TACHE =
            "Analyse le marche DevOps, puis redige la synthese.";

    public static void main(String[] args) {
        System.out.println("""
                1. UN AGENT QUI FAIT TOUT, ET DEUX QUI SE PARTAGENT LE TRAVAIL
                """);

        // -- a gauche : le monolithe. Un prompt, tous les outils. ----------
        CatalogueOffres catalogueSeul = new CatalogueOffres();
        Toolkit toutEnUn = new Toolkit();
        toutEnUn.registerTool(catalogueSeul);
        ModeleFactice modeleSeul = new ModeleFactice("factice:monolithe", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "devops")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Synthese : " + premiereLigne(
                                ModeleFactice.resultatsDOutils(messages)))));
        ReActAgent monolithe = ReActAgent.builder()
                .name("tout-en-un")
                .sysPrompt("Tu cherches les offres, tu analyses le marche, tu "
                           + "rediges la synthese, tu verifies les chiffres, "
                           + "tu adaptes le ton au destinataire, et tu "
                           + "n'inventes jamais rien.")
                .model(modeleSeul)
                .toolkit(toutEnUn)
                .maxIters(5)
                .build();
        monolithe.call(TACHE, Chapitre1Agent.contexte("s-mono")).block();

        // -- a droite : un orchestrateur et deux specialistes --------------
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit outilsDuChercheur = new Toolkit();
        outilsDuChercheur.registerTool(catalogue);

        ModeleFactice modeleChercheur = new ModeleFactice("factice:chercheur",
                List.of(new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                                Map.of("motCle", "devops")),
                        new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                                ModeleFactice.resultatsDOutils(messages))));
        ReActAgent chercheur = ReActAgent.builder()
                .name("chercheur")
                .description("Trouve les offres du portail par mot-cle.")
                .sysPrompt("Tu cherches des offres, et tu ne fais que cela.")
                .model(modeleChercheur)
                .toolkit(outilsDuChercheur)
                .maxIters(4)
                .build();

        ModeleFactice modeleRedacteur = new ModeleFactice("factice:redacteur",
                List.of(new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Le marche DevOps est actif sur Paris et Bordeaux.")));
        ReActAgent redacteur = ReActAgent.builder()
                .name("redacteur")
                .description("Redige une synthese a partir de donnees fournies.")
                .sysPrompt("Tu rediges, et tu ne cherches rien.")
                .model(modeleRedacteur)
                .toolkit(new Toolkit())
                .maxIters(2)
                .build();

        // L'orchestrateur ne recoit AUCUN outil metier : il recoit des AGENTS.
        //
        // ⚠️ UN `registration()` PAR SOUS-AGENT. Enchainer deux appels a
        // `.subAgent(...)` sur la meme registration n'en garde qu'UN, sans
        // erreur ni avertissement : la section 2 le mesure.
        Toolkit outilsDeLOrchestrateur = new Toolkit();
        outilsDeLOrchestrateur.registration()
                .subAgent(() -> chercheur, SubAgentConfig.builder()
                        .toolName("demander_au_chercheur")
                        .description("Confie une recherche d'offres au chercheur.")
                        .forwardEvents(true)
                        .build())
                .apply();
        outilsDeLOrchestrateur.registration()
                .subAgent(() -> redacteur, SubAgentConfig.builder()
                        .toolName("demander_au_redacteur")
                        .description("Confie une redaction au redacteur.")
                        .forwardEvents(true)
                        .build())
                .apply();

        ModeleFactice modeleChef = new ModeleFactice("factice:chef", List.of(
                // Le parametre d'un sous-agent s'appelle `message` : un
                // sous-agent recoit une CONVERSATION, pas des arguments.
                new ModeleFactice.Tour.AppelDOutil("demander_au_chercheur",
                        Map.of("message", "Quelles offres devops ?")),
                new ModeleFactice.Tour.AppelDOutil("demander_au_redacteur",
                        Map.of("message", "Redige la synthese du marche devops.")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Synthese : " + derniereLigne(
                                ModeleFactice.resultatsDOutils(messages)))));

        ReActAgent chefDeProjet = ReActAgent.builder()
                .name("chef-de-projet")
                .sysPrompt("Tu delegues aux specialistes, et tu composes.")
                .model(modeleChef)
                .toolkit(outilsDeLOrchestrateur)
                .maxIters(6)
                .build();

        Msg reponse = chefDeProjet
                .call(TACHE, Chapitre1Agent.contexte("s-equipe")).block();

        System.out.printf("   %-24s %-12s %-14s %s%n",
                          "AGENT", "OUTILS", "CONSIGNE", "APPELS AU MODELE");
        System.out.printf("   %-24s %-12d %-14d %d%n", "tout-en-un",
                toutEnUn.getToolNames().size(),
                monolithe.getSysPrompt().length(), modeleSeul.appels());
        System.out.printf("   %-24s %-12d %-14d %d%n", "chef-de-projet",
                outilsDeLOrchestrateur.getToolNames().size(),
                chefDeProjet.getSysPrompt().length(), modeleChef.appels());
        System.out.printf("   %-24s %-12d %-14d %d%n", "  ├─ chercheur",
                outilsDuChercheur.getToolNames().size(),
                chercheur.getSysPrompt().length(), modeleChercheur.appels());
        System.out.printf("   %-24s %-12d %-14d %d%n", "  └─ redacteur",
                0, redacteur.getSysPrompt().length(), modeleRedacteur.appels());

        System.out.printf("%n   outils de l'orchestrateur : %s%n",
                          outilsDeLOrchestrateur.getToolNames());
        System.out.printf("   reponse finale            : %s%n",
                          premiereLigne(Chapitre1Agent.texte(reponse)));

        System.out.println("""

                   ⚠️ REGARDEZ LA COLONNE « OUTILS » DE L'ORCHESTRATEUR :
                   ses deux outils sont des AGENTS, pas des methodes metier.
                   Il ne sait pas chercher une offre ; il sait a qui le
                   demander. Et le redacteur n'a aucun outil du tout — il ne
                   PEUT donc pas aller chercher lui-meme, ce qui est la
                   garantie recherchee : ce n'est pas une consigne qu'on
                   espere respectee, c'est une capacite qu'il n'a pas.

                   La consigne de chaque specialiste tient en une ligne, la
                   ou celle du monolithe enumere cinq metiers. C'est la
                   separation des responsabilites, appliquee aux agents : un
                   prompt court se relit, se teste, et se corrige.

                   ⚠️ CE QUE CE DECOUPAGE COUTE. Plus d'agents, c'est plus
                   d'appels au modele — donc plus de latence et plus de
                   jetons. Le monolithe a repondu en %d appels, l'equipe en
                   %d au total. Decouper se justifie par la FIABILITE, pas
                   par la performance.
                """.formatted(modeleSeul.appels(),
                              modeleChef.appels() + modeleChercheur.appels()
                              + modeleRedacteur.appels()));

        System.out.println("""
                2. UN SOUS-AGENT EST UN OUTIL — ET SON ENREGISTREMENT A UN PIEGE
                """);
        System.out.println("""
                   Un sous-agent est expose comme un OUTIL. L'orchestrateur
                   ne lit pas la memoire du chercheur : il l'appelle, et
                   recoit un resultat — exactement comme pour
                   `rechercher_offres`. Ce qui a ete decrit au chapitre 3
                   vaut donc ici aussi : memes permissions, memes
                   evenements, meme journalisation. Il n'y a pas deux
                   mecanismes a apprendre.

                   ⚠️ Mais regardez COMMENT on les enregistre. Le style
                   fluide invite a enchainer :
                """);

        Toolkit enchaine = new Toolkit();
        enchaine.registration()
                .subAgent(() -> chercheur, SubAgentConfig.builder()
                        .toolName("demander_au_chercheur").build())
                .subAgent(() -> redacteur, SubAgentConfig.builder()
                        .toolName("demander_au_redacteur").build())
                .apply();

        Toolkit separe = new Toolkit();
        separe.registration().subAgent(() -> chercheur, SubAgentConfig.builder()
                .toolName("demander_au_chercheur").build()).apply();
        separe.registration().subAgent(() -> redacteur, SubAgentConfig.builder()
                .toolName("demander_au_redacteur").build()).apply();

        System.out.printf("   %-42s %-10s %s%n",
                          "FACON D'ENREGISTRER", "OUTILS", "LESQUELS");
        System.out.printf("   %-42s %-10d %s%n",
                "registration().subAgent(a).subAgent(b).apply()",
                enchaine.getToolNames().size(), enchaine.getToolNames());
        System.out.printf("   %-42s %-10d %s%n",
                "un registration().apply() par sous-agent",
                separe.getToolNames().size(), separe.getToolNames());

        System.out.println("""

                   ⚠️ Le premier sous-agent a DISPARU. Aucune exception,
                   aucun avertissement : l'orchestrateur demarre, et il lui
                   manque simplement un specialiste. Il repondra — moins
                   bien — et rien dans les journaux ne dira pourquoi.

                   La regle a retenir tient en une ligne : UN
                   `registration()...apply()` PAR SOUS-AGENT. Et le test qui
                   l'attrape se resume a verifier `getToolNames()` apres la
                   construction, ce qui coute trois lignes.

                   ⚠️ Notez aussi le parametre d'appel : `message`, pas
                   `task`. Un sous-agent recoit une CONVERSATION, et rend une
                   reponse — avec, en option, un `session_id` pour poursuivre
                   un echange anterieur. C'est bien un agent qu'on appelle,
                   pas une fonction.
                """);

        System.out.println("""
                3. LA MESURE : UN MIDDLEWARE VOIT PASSER TOUTE LA BOUCLE
                """);
        CatalogueOffres catalogueTrace = new CatalogueOffres();
        Toolkit toolkitTrace = new Toolkit();
        toolkitTrace.registerTool(catalogueTrace);
        JournalDeMiddleware journal = new JournalDeMiddleware();

        ModeleFactice modeleTrace = new ModeleFactice("factice:trace", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "devops")),
                new ModeleFactice.Tour.AppelDOutil("compter_candidatures",
                        Map.of("reference", "OFF-102")),
                new ModeleFactice.Tour.Reponse("Voila.")));

        ReActAgent surveille = ReActAgent.builder()
                .name("surveille")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modeleTrace)
                .toolkit(toolkitTrace)
                .maxIters(5)
                .middleware(journal)
                .build();

        RuntimeContext ctx = Chapitre1Agent.contexte("s-trace");
        List<AgentEvent> evenements = surveille.streamEvents(TACHE, ctx)
                .take(Duration.ofSeconds(10))
                .collectList()
                .block();

        System.out.printf("   %-28s %s%n", "CE QUE LE MIDDLEWARE A VU", "NOMBRE");
        System.out.printf("   %-28s %d%n", "appels au modele",
                          journal.appelsAuModele());
        System.out.printf("   %-28s %d%n", "phases d'action",
                          journal.phasesDAction());
        System.out.printf("   %-28s %d%n", "appels d'outils annonces",
                          journal.outilsDemandes().size());
        System.out.printf("   %-28s %s%n", "outils, dans l'ordre",
                          journal.outilsDemandes());
        System.out.printf("   %-28s %d%n", "evenements emis",
                          evenements == null ? 0 : evenements.size());

        System.out.println("""

                   Le middleware est un point d'interception UNIQUE : il
                   voit chaque appel au modele et chaque action, sans que le
                   code metier en sache rien. C'est la que se posent la
                   journalisation, les metriques, le comptage de jetons et
                   les gardes-fous transversaux.

                   ⚠️ Et c'est aussi la que se pose la question de la
                   DONNEE SENSIBLE. Un middleware qui journalise
                   `call.args()` ecrit dans vos journaux ce que
                   l'utilisateur a tape — un salaire, une adresse, un nom.
                   Journaliser le NOM de l'outil et la TAILLE des arguments
                   suffit presque toujours, et ne cree pas une seconde base
                   de donnees personnelles a proteger.
                """);

        System.out.println("""
                4. CE QUE LE FLUX D'EVENEMENTS PERMET, ET QUE LES LOGS NE PERMETTENT PAS
                """);
        Map<String, Integer> parType = new LinkedHashMap<>();
        if (evenements != null) {
            for (AgentEvent evenement : evenements) {
                parType.merge(evenement.getType().name(), 1, Integer::sum);
            }
        }
        System.out.printf("   %-30s %s%n", "TYPE", "NOMBRE");
        for (Map.Entry<String, Integer> entree : parType.entrySet()) {
            System.out.printf("   %-30s %d%n", entree.getKey(), entree.getValue());
        }

        System.out.println("""

                   Ces evenements sont TYPES, pas des chaines a analyser :
                   une interface peut afficher « je consulte le catalogue… »
                   au bon moment, et un tableau de bord compter les appels
                   d'outils sans lire un fichier de logs.

                   C'est ce flux que le chapitre 6 branche sur du SSE, et
                   qui arrive tel quel dans le navigateur.
                """);
    }

    static String premiereLigne(String texte) {
        int fin = texte.indexOf('\n');
        return fin < 0 ? texte : texte.substring(0, fin);
    }

    private static String derniereLigne(String texte) {
        int debut = texte.lastIndexOf('\n');
        return debut < 0 ? texte : texte.substring(debut + 1);
    }
}
