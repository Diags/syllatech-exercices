package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.MsgRole;
import io.agentscope.core.message.TextBlock;
import io.agentscope.core.message.ToolResultBlock;
import io.agentscope.core.message.ToolUseBlock;
import io.agentscope.core.tool.Toolkit;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

/**
 * La boucle ReAct du VRAI framework, mesuree.
 *
 * <p>Ce que ces tests verifient n'est pas ecrit dans ce projet : le
 * chainage reflexion → appel d'outil → observation → reponse vient
 * d'AgentScope. Ce qui est ecrit ici est le MODELE, et il est deterministe
 * — c'est ce qui rend la boucle mesurable.
 */
class BoucleAgentTest {

    private static ReActAgent agent(ModeleFactice modele, Toolkit toolkit) {
        return ReActAgent.builder()
                .name("conseiller")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modele)
                .toolkit(toolkit)
                .maxIters(6)
                .build();
    }

    private static RuntimeContext contexte(String session) {
        return RuntimeContext.builder().sessionId(session).userId("awa").build();
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ LA MESURE : un appel au modele n'execute rien, un agent execute")
    void unAppelNEstPasUnAgent() {
        // A gauche : un modele qui repond, sans aucun outil.
        CatalogueOffres sansOutils = new CatalogueOffres();
        ModeleFactice seul = ModeleFactice.quiRepond("factice:seul",
                "Des postes Java a Paris et Lille.");
        agent(seul, new Toolkit()).call("Quelles offres Java ?",
                                        contexte("s-seul")).block();

        // A droite : le meme genre de question, un agent outille.
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);
        ModeleFactice outille = new ModeleFactice("factice:outille", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(
                        ModeleFactice::resultatsDOutils)));
        Msg reponse = agent(outille, toolkit)
                .call("Quelles offres Java ?", contexte("s-outille")).block();

        assertThat(seul.appels()).isEqualTo(1);
        assertThat(sansOutils.journal()).isEmpty();

        assertThat(outille.appels())
                .as("un appel pour decider, un pour repondre")
                .isEqualTo(2);
        assertThat(catalogue.journal()).containsExactly("rechercher_offres(java)");
        assertThat(reponse).isNotNull();
        assertThat(reponse.getTextContent())
                .as("la reponse cite les references REELLES du portail")
                .contains("OFF-101", "OFF-103");
    }

    @Test
    @Timeout(60)
    @DisplayName("la conversation est une suite de blocs types, pas du texte")
    void desBlocsTypes() {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);
        ModeleFactice modele = new ModeleFactice("factice:types", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.Reponse("Voila.")));

        ReActAgent agent = agent(modele, toolkit);
        RuntimeContext ctx = contexte("s-types");
        agent.call("Quelles offres Java ?", ctx).block();

        List<Msg> historique = agent.getAgentState(ctx).getContext();
        assertThat(historique).hasSize(4);
        assertThat(historique.get(0).getRole()).isEqualTo(MsgRole.USER);
        assertThat(historique.get(1).hasContentBlocks(ToolUseBlock.class))
                .as("l'assistant demande un outil")
                .isTrue();
        assertThat(historique.get(2).getRole()).isEqualTo(MsgRole.TOOL);
        assertThat(historique.get(2).hasContentBlocks(ToolResultBlock.class))
                .isTrue();
        assertThat(historique.get(3).hasContentBlocks(TextBlock.class))
                .as("puis il repond")
                .isTrue();
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ deux sessions ne se melangent pas, avec le MEME objet agent")
    void deuxSessionsNeSeMelangentPas() {
        ModeleFactice modele = new ModeleFactice("factice:sessions", List.of(
                new ModeleFactice.Tour.Reponse("Bien note."),
                new ModeleFactice.Tour.Reponse("Bien note."),
                new ModeleFactice.Tour.Reponse("Bien note.")));
        ReActAgent partage = agent(modele, new Toolkit());

        RuntimeContext awa = contexte("session-awa");
        RuntimeContext bilal = RuntimeContext.builder()
                .sessionId("session-bilal").userId("bilal").build();

        partage.call("Je cherche du Java.", awa).block();
        partage.call("Et la suite ?", awa).block();
        partage.call("Bonjour.", bilal).block();

        // ⚠️ C'est la propriete qui rend un agent deployable : sans elle, il
        // faudrait une instance par utilisateur — ou les conversations
        // fuiraient les unes dans les autres.
        assertThat(partage.getAgentState(awa).getContext()).hasSize(4);
        assertThat(partage.getAgentState(bilal).getContext()).hasSize(2);
        assertThat(partage.getAgentState(bilal).getContext().getFirst()
                          .getTextContent())
                .doesNotContain("Java");
    }

    @Test
    @Timeout(60)
    @DisplayName("le modele voit les outils, et l'historique grossit a chaque tour")
    void leModeleVoitLesOutilsEtLHistorique() {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);
        ModeleFactice modele = new ModeleFactice("factice:contexte", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.AppelDOutil("compter_candidatures",
                        Map.of("reference", "OFF-101")),
                new ModeleFactice.Tour.Reponse("Voila.")));

        agent(modele, toolkit).call("Analyse.", contexte("s-contexte")).block();

        assertThat(modele.outilsVus()).hasSize(3);
        assertThat(modele.outilsVus().getFirst())
                .as("les trois outils du catalogue sont presentes au modele")
                .hasSize(3);

        // ⚠️ Chaque resultat d'outil RESTE dans le contexte : un outil bavard
        // coute a tous les tours suivants, pas seulement au sien.
        assertThat(modele.messagesVus())
                .as("l'historique grossit strictement")
                .isSorted()
                .doesNotHaveDuplicates();
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ un modele qui boucle est arrete par maxIters")
    void maxItersBorneLaBoucle() {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);

        // Un modele qui ne repond JAMAIS : il redemande l'outil sans fin.
        ModeleFactice entete = new ModeleFactice("factice:sans-fin",
                java.util.Collections.nCopies(50,
                        new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                                Map.of("motCle", "java"))));

        ReActAgent borne = ReActAgent.builder()
                .name("borne")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(entete)
                .toolkit(toolkit)
                .maxIters(3)
                .build();

        borne.call("Cherche.", contexte("s-borne")).block();

        // La boucle s'arrete d'elle-meme : sans cette borne, un modele qui
        // redemande indefiniment le meme outil coute jusqu'au budget.
        assertThat(entete.appels())
                .as("le nombre d'appels reste borne par maxIters")
                .isLessThanOrEqualTo(5);
        assertThat(catalogue.journal().size()).isLessThanOrEqualTo(5);
    }
}
