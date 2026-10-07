package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.OutilsDOffres;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.ToolCallAdvisor;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.model.tool.DefaultToolCallingManager;
import org.springframework.ai.model.tool.ToolCallLimitBehavior;
import org.springframework.ai.model.tool.ToolCallingChatOptions;
import org.springframework.ai.tool.method.MethodToolCallbackProvider;

/**
 * Les outils : le schéma déduit, le voyage dans les options, l'aller-retour.
 *
 * <p>Le chapitre 4 imprime ces mesures ; ces tests les figent. Le plus utile
 * d'entre eux est sans doute {@link #lesOutilsVoyagentDansLesOptions()} : il
 * garde la trace du piège qui a fait perdre le plus de temps sur ce projet —
 * des outils passés à {@code .tools(...)} et perdus en silence.
 */
class OutilsTest {

    private final OutilsDOffres outils = new OutilsDOffres();

    @BeforeEach
    void repartirDeZero() {
        OutilsDOffres.remettreAZero();
    }

    @Test
    @DisplayName("Spring AI deduit un schema JSON de chaque methode `@Tool`")
    void leSchemaEstDeduit() {
        var rappels = MethodToolCallbackProvider.builder()
                .toolObjects(outils).build().getToolCallbacks();

        assertThat(rappels).hasSize(3);
        var cherche = java.util.Arrays.stream(rappels)
                .filter(r -> r.getToolDefinition().name().equals("rechercherOffres"))
                .findFirst().orElseThrow();
        assertThat(cherche.getToolDefinition().description())
                .contains("mot-cle");
        assertThat(cherche.getToolDefinition().inputSchema())
                .as("le nom du parametre survit grace a -parameters")
                .contains("\"motCle\"")
                .contains("\"type\" : \"string\"")
                .as("la description de @ToolParam finit dans le schema")
                .contains("en minuscules")
                .contains("\"required\"");
    }

    /**
     * ⚠️ Le piège de Spring AI 2.0.
     *
     * <p>Les outils ne sont pas dans le prompt : ils voyagent dans les
     * options, sous forme de {@code ToolCallback}. Si les options du modèle
     * n'implémentent pas {@link ToolCallingChatOptions}, ils sont perdus —
     * sans erreur, sans journal, et avec une réponse parfaitement normale.
     */
    @Test
    @DisplayName("les outils voyagent dans les options, pas dans le texte")
    void lesOutilsVoyagentDansLesOptions() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele).build();

        client.prompt().user("Bonjour").call().content();
        int sansOutils = modele.dernierTexte().length();
        client.prompt().user("Bonjour").tools(outils).call().content();

        assertThat(modele.dernierTexte()).hasSize(sansOutils);
        assertThat(modele.derniersOutils())
                .as("si cette liste est vide, `.tools()` a ete perdu en silence")
                .hasSize(3);
    }

    @Test
    @DisplayName("l'aller-retour complet : demande, execution, reponse")
    void lAllerRetourComplet() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> prompt.contains("rechercherOffres = ")
                ? null
                : new AssistantMessage.ToolCall("un", "function",
                        "rechercherOffres", "{\"motCle\":\"teletravail\"}"));
        modele.repondre(prompt -> prompt.contains("rechercherOffres = ")
                ? "Trois offres proposent du teletravail." : null);

        String reponse = ChatClient.builder(modele).build().prompt()
                .user("Quelles offres proposent du teletravail ?")
                .tools(outils).call().content();

        assertThat(modele.appels())
                .as("un outil coute DEUX appels au modele, pas un")
                .isEqualTo(2);
        assertThat(OutilsDOffres.appels()).isEqualTo(1);
        assertThat(reponse).isEqualTo("Trois offres proposent du teletravail.");
        assertThat(modele.conversation())
                .contains("[ASSISTANT] appelle rechercherOffres")
                .contains("[TOOL] rechercherOffres a rendu")
                .contains("OFF-014");
    }

    @Test
    @DisplayName("l'outil qui ecrit refuse une reference inconnue")
    void lOutilQuiEcritRefuse() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> prompt.contains("postuler = ") ? null
                : new AssistantMessage.ToolCall("un", "function", "postuler",
                        "{\"reference\":\"OFF-999\"}"));

        ChatClient.builder(modele).build().prompt()
                .user("Postule sur OFF-999").tools(outils).call().content();

        assertThat(OutilsDOffres.appels())
                .as("on ne peut PAS empecher l'appel : seulement le refuser")
                .isEqualTo(1);
        assertThat(OutilsDOffres.candidatures()).isEmpty();
        assertThat(modele.conversation()).contains("refus");
    }

    @Test
    @DisplayName("l'outil qui ecrit accepte une reference connue")
    void lOutilQuiEcritAccepte() {
        assertThat(outils.postuler("OFF-014")).contains("enregistree");
        assertThat(OutilsDOffres.candidatures()).containsExactly("OFF-014");
    }

    @Test
    @DisplayName("un outil invente par le modele fait echouer l'appel")
    void lOutilInconnuEchoue() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> new AssistantMessage.ToolCall(
                "un", "function", "supprimerToutesLesOffres", "{}"));

        assertThatThrownBy(() -> ChatClient.builder(modele).build().prompt()
                .user("Fais le menage.").tools(outils).call().content())
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("supprimerToutesLesOffres");
    }

    /**
     * Le plafond de Spring AI 2 : il protège la base, pas la facture.
     *
     * <p>Mesure exacte : l'outil n'est jamais appelé une quatrième fois. Mais
     * avec {@code RETURN_ERROR_RESPONSE} — le comportement par défaut — la
     * conversation continue, et les appels au modèle, eux, ne sont pas
     * bornés.
     */
    @Test
    @DisplayName("`maxTotalToolCalls` borne l'outil, jamais le nombre d'allers-retours")
    void lePlafondBorneLOutil() {
        var modele = new ModeleFactice();
        var insistance = new AtomicInteger();
        modele.demanderOutil(prompt -> insistance.incrementAndGet() > 8 ? null
                : new AssistantMessage.ToolCall("boucle", "function",
                        "salaireDe", "{\"reference\":\"OFF-014\"}"));
        modele.repondre(prompt -> "J'abandonne.");

        var borne = ChatClient.builder(modele)
                .defaultAdvisors(ToolCallAdvisor.builder()
                        .toolCallingManager(DefaultToolCallingManager.builder()
                                .maxTotalToolCalls(3)
                                .onLimitExceeded(
                                        ToolCallLimitBehavior.RETURN_ERROR_RESPONSE)
                                .build())
                        .build())
                .build();
        borne.prompt().user("Et le salaire ?").tools(outils).call().content();

        assertThat(OutilsDOffres.appels()).isEqualTo(3);
        assertThat(modele.appels())
                .as("le modele, lui, a ete appele bien plus de trois fois")
                .isGreaterThan(3);
    }

    @Test
    @DisplayName("`THROW` arrete la boucle des le plafond atteint")
    void lePlafondQuiArreteTout() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> new AssistantMessage.ToolCall(
                "boucle", "function", "salaireDe",
                "{\"reference\":\"OFF-014\"}"));

        var borne = ChatClient.builder(modele)
                .defaultAdvisors(ToolCallAdvisor.builder()
                        .toolCallingManager(DefaultToolCallingManager.builder()
                                .maxTotalToolCalls(3)
                                .onLimitExceeded(ToolCallLimitBehavior.THROW)
                                .build())
                        .build())
                .build();
        String reponse = borne.prompt().user("Et le salaire ?")
                .tools(outils).call().content();

        assertThat(OutilsDOffres.appels()).isEqualTo(3);
        assertThat(reponse)
                .as("meme `THROW` finit en reponse ordinaire : rien ne remonte "
                    + "a l'appelant sous forme d'exception")
                .contains("limit");
    }

    @Test
    @DisplayName("aucune dependance MCP : `@Tool` suffit")
    void aucuneDependanceMcp() {
        assertThat(presente("org.springframework.ai.mcp"
                + ".SyncMcpToolCallbackProvider")).isFalse();
        assertThat(presente("io.modelcontextprotocol.client.McpClient")).isFalse();
        assertThat(presente("org.springframework.ai.tool.annotation.Tool")).isTrue();
    }

    private static boolean presente(String nom) {
        try {
            Class.forName(nom);
            return true;
        } catch (ClassNotFoundException absente) {
            return false;
        }
    }
}
