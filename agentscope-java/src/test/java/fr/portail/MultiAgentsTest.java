package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import fr.portail.observabilite.JournalDeMiddleware;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.event.AgentEventType;
import io.agentscope.core.message.Msg;
import io.agentscope.core.model.ToolSchema;
import io.agentscope.core.tool.Toolkit;
import io.agentscope.core.tool.subagent.SubAgentConfig;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

/**
 * L'orchestration multi-agents et le middleware.
 *
 * <p>⚠️ Le premier test fixe un piege d'API qui ne produit AUCUNE erreur :
 * enchainer deux {@code .subAgent(...)} sur une meme registration n'en garde
 * qu'un. L'orchestrateur demarre, il lui manque un specialiste, et rien ne
 * le dit.
 */
class MultiAgentsTest {

    private static ReActAgent specialiste(String nom, Toolkit toolkit,
                                          ModeleFactice modele) {
        return ReActAgent.builder()
                .name(nom)
                .description("specialiste " + nom)
                .sysPrompt("Tu es " + nom + ", et tu ne fais que cela.")
                .model(modele)
                .toolkit(toolkit)
                .maxIters(4)
                .build();
    }

    private static ReActAgent trivial(String nom) {
        return specialiste(nom, new Toolkit(),
                           ModeleFactice.quiRepond("factice:" + nom, "ok"));
    }

    @Test
    @DisplayName("⚠️ LA MESURE : enchainer deux .subAgent(...) en perd un, en silence")
    void enchainerLesSousAgentsEnPerdUn() {
        ReActAgent chercheur = trivial("chercheur");
        ReActAgent redacteur = trivial("redacteur");

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

        assertThat(enchaine.getToolNames())
                .as("un seul sous-agent survit — aucune exception, aucun log")
                .hasSize(1)
                .containsExactly("demander_au_redacteur");

        assertThat(separe.getToolNames())
                .as("un registration()...apply() PAR sous-agent")
                .containsExactlyInAnyOrder("demander_au_chercheur",
                                           "demander_au_redacteur");
    }

    @Test
    @DisplayName("un sous-agent s'appelle avec `message`, pas avec des arguments metier")
    void leParametreEstMessage() {
        Toolkit toolkit = new Toolkit();
        toolkit.registration().subAgent(() -> trivial("chercheur"),
                SubAgentConfig.builder().toolName("demander_au_chercheur")
                        .description("recherche").build()).apply();

        ToolSchema schema = toolkit.getToolSchemas().getFirst();

        // Un sous-agent recoit une CONVERSATION, pas des arguments : c'est
        // bien un agent qu'on appelle, pas une fonction.
        assertThat(proprietes(schema)).containsKeys("message", "session_id");
        assertThat(requis(schema)).containsExactly("message");
    }

    /** Le schema est un `Map<String, Object>` libre : on le lit type. */
    @SuppressWarnings("unchecked")
    private static Map<String, Object> proprietes(ToolSchema schema) {
        return (Map<String, Object>) schema.getParameters().get("properties");
    }

    @SuppressWarnings("unchecked")
    private static List<String> requis(ToolSchema schema) {
        return (List<String>) schema.getParameters().get("required");
    }


    @Test
    @Timeout(120)
    @DisplayName("l'orchestrateur delegue, et ses outils sont des AGENTS")
    void lOrchestrateurDelegue() {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit outilsDuChercheur = new Toolkit();
        outilsDuChercheur.registerTool(catalogue);

        ModeleFactice modeleChercheur = new ModeleFactice("factice:chercheur",
                List.of(new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                                Map.of("motCle", "devops")),
                        new ModeleFactice.Tour.ReponseSelonLHistorique(
                                ModeleFactice::resultatsDOutils)));
        ReActAgent chercheur = specialiste("chercheur", outilsDuChercheur,
                                           modeleChercheur);

        ModeleFactice modeleRedacteur = ModeleFactice.quiRepond(
                "factice:redacteur", "Le marche DevOps est actif.");
        ReActAgent redacteur = specialiste("redacteur", new Toolkit(),
                                           modeleRedacteur);

        Toolkit outilsDuChef = new Toolkit();
        outilsDuChef.registration().subAgent(() -> chercheur,
                SubAgentConfig.builder().toolName("demander_au_chercheur")
                        .description("recherche").build()).apply();
        outilsDuChef.registration().subAgent(() -> redacteur,
                SubAgentConfig.builder().toolName("demander_au_redacteur")
                        .description("redaction").build()).apply();

        ModeleFactice modeleChef = new ModeleFactice("factice:chef", List.of(
                new ModeleFactice.Tour.AppelDOutil("demander_au_chercheur",
                        Map.of("message", "Quelles offres devops ?")),
                new ModeleFactice.Tour.AppelDOutil("demander_au_redacteur",
                        Map.of("message", "Redige la synthese.")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(
                        ModeleFactice::resultatsDOutils)));

        ReActAgent chef = ReActAgent.builder()
                .name("chef-de-projet")
                .sysPrompt("Tu delegues aux specialistes, et tu composes.")
                .model(modeleChef)
                .toolkit(outilsDuChef)
                .maxIters(6)
                .build();

        Msg reponse = chef.call("Analyse le marche DevOps, puis redige.",
                RuntimeContext.builder().sessionId("s-equipe").userId("awa")
                        .build()).block();

        // ⚠️ L'orchestrateur n'a AUCUN outil metier : il ne sait pas chercher
        // une offre, il sait a qui le demander.
        assertThat(outilsDuChef.getToolNames())
                .containsExactlyInAnyOrder("demander_au_chercheur",
                                           "demander_au_redacteur");
        assertThat(outilsDuChef.getToolNames())
                .doesNotContain("rechercher_offres", "supprimer_offre");

        // Et le redacteur n'a aucun outil : il ne PEUT pas aller chercher
        // lui-meme. Ce n'est pas une consigne, c'est une capacite absente.
        assertThat(redacteur.getToolkit().getToolNames()).isEmpty();

        assertThat(catalogue.journal())
                .as("seul le chercheur a touche au catalogue")
                .containsExactly("rechercher_offres(devops)");
        assertThat(reponse).isNotNull();
        assertThat(reponse.getTextContent()).contains("OFF-102");

        assertThat(modeleChercheur.appels()).isPositive();
        assertThat(modeleRedacteur.appels()).isPositive();
        assertThat(modeleChef.appels() + modeleChercheur.appels()
                   + modeleRedacteur.appels())
                .as("⚠️ decouper coute des appels : c'est le prix de la fiabilite")
                .isGreaterThan(modeleChef.appels());
    }

    @Test
    @Timeout(120)
    @DisplayName("le middleware voit chaque appel au modele et chaque action")
    void leMiddlewareVoitToutePLaBoucle() {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);
        JournalDeMiddleware journal = new JournalDeMiddleware();

        ModeleFactice modele = new ModeleFactice("factice:trace", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "devops")),
                new ModeleFactice.Tour.AppelDOutil("compter_candidatures",
                        Map.of("reference", "OFF-102")),
                new ModeleFactice.Tour.Reponse("Voila.")));

        ReActAgent agent = ReActAgent.builder()
                .name("surveille")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modele)
                .toolkit(toolkit)
                .maxIters(5)
                .middleware(journal)
                .build();

        List<AgentEvent> evenements = agent
                .streamEvents("Analyse.", RuntimeContext.builder()
                        .sessionId("s-trace").userId("awa").build())
                .take(Duration.ofSeconds(20))
                .collectList()
                .block();

        assertThat(journal.appelsAuModele()).isEqualTo(3);
        assertThat(journal.phasesDAction()).isEqualTo(2);
        assertThat(journal.outilsDemandes())
                .containsExactly("rechercher_offres", "compter_candidatures");

        // ⚠️ Le journal NOMME l'outil et COMPTE ses arguments — il n'en
        // recopie pas le contenu. Journaliser `call.args()` ecrirait dans les
        // logs ce que l'utilisateur a tape : un salaire, une adresse, un nom.
        assertThat(journal.lignes())
                .allSatisfy(ligne -> assertThat(ligne)
                        .doesNotContain("devops")
                        .doesNotContain("OFF-102"));

        assertThat(evenements).isNotNull();
        assertThat(evenements.stream().map(AgentEvent::getType).toList())
                .contains(AgentEventType.AGENT_START,
                          AgentEventType.MODEL_CALL_START,
                          AgentEventType.TOOL_CALL_START,
                          AgentEventType.TOOL_RESULT_END,
                          AgentEventType.AGENT_END);
    }
}
