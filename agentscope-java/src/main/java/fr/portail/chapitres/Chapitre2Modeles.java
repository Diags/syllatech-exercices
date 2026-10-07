package fr.portail.chapitres;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.message.ContentBlock;
import io.agentscope.core.message.Msg;
import io.agentscope.core.model.Model;
import io.agentscope.core.tool.Toolkit;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.function.Supplier;

/**
 * Chapitre 2 — Modeles et messages.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Modeles
 * </pre>
 *
 * <p>Trois mesures : ce qui change quand on change de fournisseur (une
 * ligne), ce qu'est vraiment une conversation (une suite de blocs types,
 * pas une chaine), et ce que le streaming apporte (le premier evenement
 * arrive avant la reponse).
 */
public final class Chapitre2Modeles {

    private Chapitre2Modeles() {
    }

    private static final String QUESTION = "Quelles offres Java ?";

    public static void main(String[] args) {
        System.out.println("""
                1. LE MODELE EST UNE DEPENDANCE, PAS UNE DECISION D'ARCHITECTURE
                """);

        // Le MEME sysPrompt, les MEMES outils, deux modeles differents.
        Map<String, Supplier<Model>> fournisseurs = new LinkedHashMap<>();
        fournisseurs.put("factice:local", () -> scenario("factice:local"));
        fournisseurs.put("factice:manage", () -> scenario("factice:manage"));

        System.out.printf("   %-24s %-14s %-14s %s%n",
                          "MODELE", "APPELS", "OUTILS EXEC.", "MEMES OFFRES");
        String premiereReponse = null;
        for (Map.Entry<String, Supplier<Model>> entree : fournisseurs.entrySet()) {
            CatalogueOffres catalogue = new CatalogueOffres();
            Toolkit toolkit = new Toolkit();
            toolkit.registerTool(catalogue);
            ModeleFactice modele = (ModeleFactice) entree.getValue().get();

            ReActAgent agent = agent(modele, toolkit);
            Msg reponse = agent.call(QUESTION,
                    Chapitre1Agent.contexte("s-" + entree.getKey())).block();
            String texte = Chapitre1Agent.texte(reponse);
            if (premiereReponse == null) {
                premiereReponse = texte;
            }

            System.out.printf("   %-24s %-14d %-14d %s%n",
                    entree.getKey(), modele.appels(),
                    catalogue.journal().size(),
                    texte.equals(premiereReponse) ? "oui" : "non");
        }

        System.out.println("""

                   La seule ligne qui a change est `.model(…)`. Ni le
                   sysPrompt, ni les outils, ni la boucle : le fournisseur
                   est une dependance, au sens ou une base de donnees en est
                   une.

                   ⚠️ CE QUE CETTE ABSTRACTION NE PROMET PAS. Elle rend le
                   CODE portable, pas le COMPORTEMENT. Deux modeles reels ne
                   decoupent pas les memes appels d'outils, ne respectent pas
                   les consignes avec la meme rigueur, et n'ont ni la meme
                   fenetre de contexte ni le meme prix. Basculer de
                   fournisseur se fait en une ligne ; le REVALIDER est un
                   travail a part entiere, et c'est lui qui coute.
                """);

        System.out.println("""
                2. UNE CONVERSATION EST UNE SUITE DE BLOCS TYPES
                """);
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);
        ModeleFactice modele = scenario("factice:types");
        ReActAgent agent = agent(modele, toolkit);
        RuntimeContext ctx = Chapitre1Agent.contexte("s-types");
        agent.call(QUESTION, ctx).block();

        System.out.printf("   %-6s %-12s %s%n", "RANG", "ROLE", "BLOCS");
        List<Msg> historique = agent.getAgentState(ctx).getContext();
        int rang = 0;
        for (Msg message : historique) {
            System.out.printf("   %-6d %-12s %s%n", ++rang,
                              message.getRole(), typesDeBlocs(message));
        }

        System.out.println("""

                   Ce n'est pas du texte concatene : chaque tour porte des
                   BLOCS TYPES — du texte, un appel d'outil, un resultat
                   d'outil. C'est cette structure qui permet au modele de
                   raisonner sur l'historique, et au framework de savoir quoi
                   executer.

                   ⚠️ Et c'est aussi ce qui fait grossir le contexte. Chaque
                   resultat d'outil y reste : une boucle de dix appels
                   renvoie dix fois le catalogue au modele. Un outil qui rend
                   trop de texte coute donc a CHAQUE tour suivant, pas
                   seulement au sien.
                """);

        System.out.println("""
                3. LA MESURE : LE STREAMING, ET CE QU'IL CHANGE VRAIMENT
                """);

        CatalogueOffres catalogueFlux = new CatalogueOffres();
        Toolkit toolkitFlux = new Toolkit();
        toolkitFlux.registerTool(catalogueFlux);
        ReActAgent agentFlux = agent(scenario("factice:flux"), toolkitFlux);

        long depart = System.nanoTime();
        long[] premier = {-1};
        Map<String, Integer> parType = new LinkedHashMap<>();
        List<AgentEvent> evenements = agentFlux
                .streamEvents(QUESTION, Chapitre1Agent.contexte("s-flux"))
                .doOnNext(evenement -> {
                    if (premier[0] < 0) {
                        premier[0] = (System.nanoTime() - depart) / 1_000_000;
                    }
                    parType.merge(evenement.getType().name(), 1, Integer::sum);
                })
                .collectList()
                .block();
        long total = (System.nanoTime() - depart) / 1_000_000;

        System.out.printf("      evenements emis        : %d%n",
                          evenements == null ? 0 : evenements.size());
        System.out.printf("      premier evenement      : %d ms%n", premier[0]);
        System.out.printf("      reponse complete       : %d ms%n", total);
        System.out.println();
        System.out.printf("   %-30s %s%n", "TYPE D'EVENEMENT", "NOMBRE");
        for (Map.Entry<String, Integer> entree : parType.entrySet()) {
            System.out.printf("   %-30s %d%n", entree.getKey(), entree.getValue());
        }

        System.out.println("""

                   Le flux n'est pas qu'un confort d'affichage : il rend la
                   boucle OBSERVABLE. Les evenements ci-dessus disent quand
                   le modele est appele, quel outil demarre, quel resultat
                   revient — c'est la matiere du chapitre 5, et celle d'une
                   interface qui affiche « je cherche dans le catalogue… »
                   plutot qu'un sablier.

                   ⚠️ HONNETETE DE LA MESURE : le modele de ce projet rend sa
                   reponse d'un coup, donc l'ecart entre le premier evenement
                   et le dernier est ici de quelques millisecondes. Avec un
                   vrai fournisseur, la reponse arrive en fragments sur
                   plusieurs secondes, et c'est la que l'ecart se creuse. Ce
                   que ce chapitre prouve est la STRUCTURE du flux ; le gain
                   de latence ressentie, lui, ne se prouve pas hors ligne.
                """);
    }

    /** Le meme scenario, quel que soit le « fournisseur ». */
    private static ModeleFactice scenario(String nom) {
        return new ModeleFactice(nom, List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Offres Java :\n"
                        + ModeleFactice.resultatsDOutils(messages))));
    }

    /** Le MEME agent, a la ligne `.model(…)` pres. */
    private static ReActAgent agent(Model modele, Toolkit toolkit) {
        return ReActAgent.builder()
                .name("conseiller")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modele)
                .toolkit(toolkit)
                .maxIters(5)
                .build();
    }

    private static String typesDeBlocs(Msg message) {
        List<String> types = message.getContent() == null ? List.of()
                : message.getContent().stream()
                        .map(ContentBlock::getClass)
                        .map(Class::getSimpleName)
                        .toList();
        return types.isEmpty() ? "(aucun)" : String.join(", ", types);
    }
}
