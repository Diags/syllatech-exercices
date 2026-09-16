package fr.portail.web;

import fr.portail.modele.ModeleFactice;
import fr.portail.observabilite.JournalDeMiddleware;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.state.AgentStateStore;
import io.agentscope.core.state.JsonFileAgentStateStore;
import io.agentscope.core.tool.Toolkit;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;

/**
 * L'application du portail : l'agent y est un BEAN, comme un autre.
 *
 * <p>C'est tout le propos du chapitre 6. Integrer AgentScope ne veut pas dire
 * reecrire l'application : on declare l'agent dans une configuration, on lui
 * injecte les services existants sous forme d'outils, et il devient
 * disponible partout par injection de dependances.
 *
 * <p>⚠️ Le {@link CatalogueOffres} est un bean ORDINAIRE. L'agent ne le
 * connait pas : il connait un {@link Toolkit} dans lequel ce bean a ete
 * enregistre. Les regles metier restent ou elles sont.
 */
@SpringBootApplication
public class ApplicationPortail {

    public static void main(String[] args) {
        SpringApplication.run(ApplicationPortail.class, args);
    }

    /** Le service metier existant — il ne sait rien des agents. */
    @Bean
    public CatalogueOffres catalogueOffres() {
        return new CatalogueOffres();
    }

    /**
     * L'etat des conversations, sur DISQUE.
     *
     * <p>⚠️ Le cours parle de PostgreSQL ou de Redis, et c'est la bonne
     * reponse en production : plusieurs instances derriere un repartiteur
     * doivent lire le meme etat. Ce projet utilise le magasin de fichiers
     * JSON livre par AgentScope, parce qu'il tourne sans base — ce qui se
     * demontre reste le meme : l'etat SURVIT au redemarrage, et il ne vit
     * pas dans la memoire du processus.
     */
    @Bean
    public AgentStateStore magasinDEtat() {
        return new JsonFileAgentStateStore(
                Path.of(System.getProperty("java.io.tmpdir"),
                        "portail-agentscope"));
    }

    @Bean
    public JournalDeMiddleware journalDeMiddleware() {
        return new JournalDeMiddleware();
    }

    /**
     * L'agent, construit une fois, injecte partout.
     *
     * <p>Il recoit VOS services comme outils et VOTRE magasin d'etat. Le
     * controleur, lui, ne connaitra qu'un `ReActAgent`.
     */
    @Bean
    public ReActAgent assistantCarriere(CatalogueOffres catalogue,
                                        AgentStateStore magasin,
                                        JournalDeMiddleware journal) {
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);

        // TODO : construire l'agent — il recoit VOS services comme outils, VOTRE magasin d'etat (sans quoi les conversations meurent au redemarrage) et le middleware
        return ReActAgent.builder()
                .name("assistant-carriere")
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(modeleDuPortail())
                .build();
    }

    /**
     * ⚠️ LE SEUL ENDROIT OU LE FOURNISSEUR EST NOMME.
     *
     * <p>En production, cette ligne devient
     * {@code .model("anthropic:claude-sonnet-5")} et rien d'autre ne bouge —
     * c'est la demonstration du chapitre 2.
     */
    private static ModeleFactice modeleDuPortail() {
        return new ModeleFactice("factice:portail", List.of(
                new ModeleFactice.Tour.AppelDOutil("rechercher_offres",
                        Map.of("motCle", "java")),
                new ModeleFactice.Tour.ReponseSelonLHistorique(messages ->
                        "Offres trouvees :\n"
                        + ModeleFactice.resultatsDOutils(messages))));
    }
}
