package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import fr.portail.web.ApplicationPortail;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.state.AgentStateStore;
import io.agentscope.core.state.JsonFileAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * L'agent comme bean Spring, interroge par de VRAIES requetes HTTP et SSE,
 * puis la mesure qui decide si l'agent est deployable : son etat survit-il
 * au redemarrage ?
 */
@SpringBootTest(classes = ApplicationPortail.class,
                webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
                properties = {"spring.main.banner-mode=off",
                              "logging.level.root=WARN"})
class IntegrationSpringTest {

    @Autowired
    private Environment environnement;

    @Autowired
    private ReActAgent agent;

    @Autowired
    private CatalogueOffres catalogue;

    private WebClient client;

    @BeforeEach
    void ouvrirLeClient() {
        client = WebClient.create("http://localhost:"
                + environnement.getProperty("local.server.port"));
    }

    @Test
    @DisplayName("l'agent est un bean, et il a recu les outils du catalogue")
    void lAgentEstUnBean() {
        assertThat(agent).isNotNull();
        assertThat(agent.getToolkit().getToolNames())
                .containsExactlyInAnyOrder("rechercher_offres",
                                           "compter_candidatures",
                                           "supprimer_offre");
        // ⚠️ Le catalogue est un bean ORDINAIRE : il n'implemente aucune
        // interface du framework et ne sait pas qu'il est devenu un outil.
        assertThat(catalogue).isNotNull();
        assertThat(catalogue.nombreDOffres()).isEqualTo(6);
    }

    @Test
    @Timeout(120)
    @DisplayName("GET /assistant traverse la boucle et rend une reponse fondee")
    void laRouteOrdinaire() {
        String reponse = client.get()
                .uri(b -> b.path("/assistant")
                        .queryParam("q", "Quelles offres Java ?")
                        .queryParam("session", "test-ordinaire").build())
                .retrieve().bodyToMono(String.class)
                .block(Duration.ofSeconds(60));

        assertThat(reponse)
                .as("la reponse cite les references reelles du portail")
                .contains("OFF-101", "OFF-103");
        assertThat(catalogue.journal())
                .anySatisfy(ligne -> assertThat(ligne)
                        .startsWith("rechercher_offres"));
    }

    @Test
    @Timeout(120)
    @DisplayName("GET /assistant/flux rend de VRAIS Server-Sent Events types")
    void laRouteEnSse() {
        List<String> fragments = client.get()
                .uri(b -> b.path("/assistant/flux")
                        .queryParam("q", "Quelles offres Java ?")
                        .queryParam("session", "test-sse").build())
                .retrieve().bodyToFlux(String.class)
                .take(Duration.ofSeconds(30))
                .collectList()
                .block(Duration.ofSeconds(60));

        assertThat(fragments).isNotNull().isNotEmpty();
        // Le flux de l'agent est deja un `Flux` : aucune passerelle, aucun
        // fil d'execution supplementaire.
        assertThat(fragments.size())
                .as("plusieurs evenements, pas une seule reponse")
                .isGreaterThan(3);
    }

    // -- la persistance d'etat --------------------------------------------

    @Test
    @Timeout(120)
    @DisplayName("⚠️ LA MESURE : l'etat sur disque survit au redemarrage, la memoire non")
    void lEtatSurvitAuRedemarrage(@TempDir Path dossier) throws IOException {
        Path magasin = Files.createDirectories(dossier.resolve("etat"));
        AgentStateStore surDisque = new JsonFileAgentStateStore(magasin);

        RuntimeContext ctx = RuntimeContext.builder()
                .sessionId("awa").userId("awa").build();

        // Premiere « instance » : on parle a l'agent, puis on sauvegarde.
        ReActAgent avant = agentAvec(surDisque);
        avant.call("Je cherche un poste Java.", ctx).block();
        avant.saveAgentState(ctx);
        int messagesAvant = avant.getAgentState(ctx).getContext().size();

        // Redemarrage : un AUTRE agent, le meme magasin.
        ReActAgent apres = agentAvec(surDisque);
        assertThat(apres.getAgentState("awa", "awa").getContext())
                .as("la conversation est retrouvee telle quelle")
                .hasSize(messagesAvant);
        assertThat(surDisque.listSessionIds("awa")).contains("awa");

        // Et le defaut : une memoire qui vit dans le processus.
        ReActAgent volatil = agentAvec(null);
        volatil.call("Je cherche un poste Java.", ctx).block();
        assertThat(volatil.getAgentState(ctx).getContext()).isNotEmpty();

        assertThat(agentAvec(null).getAgentState("awa", "awa").getContext())
                .as("⚠️ tout est perdu : l'agent n'est alors pas deployable "
                    + "en plusieurs instances")
                .isEmpty();
    }

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
                .maxIters(4);
        if (magasin != null) {
            constructeur.stateStore(magasin);
        }
        return constructeur.build();
    }
}
