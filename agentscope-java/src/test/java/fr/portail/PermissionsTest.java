package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import fr.portail.outils.CatalogueOffres;
import io.agentscope.core.ReActAgent;
import io.agentscope.core.agent.RuntimeContext;
import io.agentscope.core.event.AgentEvent;
import io.agentscope.core.event.AgentEventType;
import io.agentscope.core.message.Msg;
import io.agentscope.core.permission.PermissionBehavior;
import io.agentscope.core.permission.PermissionContextState;
import io.agentscope.core.permission.PermissionDecision;
import io.agentscope.core.permission.PermissionEngine;
import io.agentscope.core.permission.PermissionMode;
import io.agentscope.core.permission.PermissionRule;
import io.agentscope.core.tool.ToolBase;
import io.agentscope.core.tool.Toolkit;
import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * Le moteur de permissions du framework, et les deux facons de s'en servir
 * sans rien proteger.
 *
 * <p>⚠️ Le contenu d'une regle est un MOTIF compare aux arguments de l'appel.
 * La chaine vide s'applique a tout ; une etoile ne s'applique a rien. Ces
 * tests fixent cette limite, parce qu'elle ne produit aucune erreur.
 */
class PermissionsTest {

    /** Le contenu de regle qui s'applique a tous les arguments. */
    private static final String TOUS = "";

    private static ToolBase outil(String nom) {
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(new CatalogueOffres());
        return (ToolBase) toolkit.getTool(nom);
    }

    private static PermissionDecision decider(PermissionMode mode,
                                              PermissionRule... regles) {
        PermissionContextState.Builder contexte =
                PermissionContextState.builder().mode(mode);
        for (PermissionRule regle : regles) {
            switch (regle.behavior()) {
                case ALLOW -> contexte.addAllowRule(regle.toolName(), regle);
                case ASK -> contexte.addAskRule(regle.toolName(), regle);
                case DENY -> contexte.addDenyRule(regle.toolName(), regle);
                default -> throw new IllegalArgumentException(regle.toString());
            }
        }
        return new PermissionEngine(contexte.build())
                .checkPermission(outil("supprimer_offre"),
                                 Map.of("reference", "OFF-101"))
                .block();
    }

    // -- les trois regimes -------------------------------------------------

    @Test
    @DisplayName("les trois regimes rendent trois decisions differentes")
    void lesTroisRegimes() {
        for (PermissionBehavior regime : List.of(PermissionBehavior.ALLOW,
                                                 PermissionBehavior.ASK,
                                                 PermissionBehavior.DENY)) {
            PermissionDecision decision = decider(PermissionMode.DEFAULT,
                    new PermissionRule("supprimer_offre", TOUS, regime, "test"));
            assertThat(decision).isNotNull();
            assertThat(decision.getBehavior()).isEqualTo(regime);
        }
    }

    @ParameterizedTest(name = "une regle de contenu « {0} » ne s''applique pas")
    @ValueSource(strings = {"*", "**", "OFF-101", "supprimer_offre",
                            "supprimer_offre(*)"})
    @DisplayName("⚠️ LA MESURE : une regle ecrite avec un joker ne protege RIEN")
    void leJokerNeProtegeRien(String contenu) {
        // Le reflexe est d'ecrire « * » pour « tous les arguments ». Le
        // contenu d'une regle est un MOTIF : l'etoile n'y est pas un joker,
        // c'est un motif litteral, et il ne correspond a rien.
        PermissionDecision decision = decider(PermissionMode.DEFAULT,
                new PermissionRule("supprimer_offre", contenu,
                                   PermissionBehavior.DENY, "test"));

        assertThat(decision).isNotNull();
        assertThat(decision.getBehavior())
                .as("la regle DENY est ignoree : on retombe sur le mode")
                .isNotEqualTo(PermissionBehavior.DENY)
                .isEqualTo(PermissionBehavior.ASK);
    }

    @Test
    @DisplayName("la chaine vide, elle, s'applique a tous les arguments")
    void laChaineVideSApplique() {
        assertThat(decider(PermissionMode.DEFAULT,
                new PermissionRule("supprimer_offre", TOUS,
                                   PermissionBehavior.DENY, "test"))
                .getBehavior())
                .isEqualTo(PermissionBehavior.DENY);
    }

    @Test
    @DisplayName("⚠️ et sous BYPASS, la regle au joker laisse passer la suppression")
    void leJokerSousBypassLaissePasser() {
        // La combinaison a ne jamais laisser partir en production : un mode
        // permissif, et une regle qui croit interdire.
        PermissionDecision decision = decider(PermissionMode.BYPASS,
                new PermissionRule("supprimer_offre", "*",
                                   PermissionBehavior.DENY, "test"));

        assertThat(decision.getBehavior()).isEqualTo(PermissionBehavior.ALLOW);
    }

    // -- les modes ---------------------------------------------------------

    @Test
    @DisplayName("le mode decide de tout ce qu'aucune regle ne couvre")
    void leModeEstLaPolitiqueParDefaut() {
        ToolBase lecture = outil("rechercher_offres");
        ToolBase ecriture = outil("supprimer_offre");
        assertThat(lecture.isReadOnly()).isTrue();
        assertThat(ecriture.isReadOnly()).isFalse();

        assertThat(sansRegle(PermissionMode.DEFAULT, lecture))
                .as("⚠️ sous DEFAULT, meme une LECTURE demande confirmation")
                .isEqualTo(PermissionBehavior.ASK);
        assertThat(sansRegle(PermissionMode.EXPLORE, lecture))
                .isEqualTo(PermissionBehavior.ALLOW);
        assertThat(sansRegle(PermissionMode.EXPLORE, ecriture))
                .as("EXPLORE : lire oui, ecrire non — le mode d'un assistant")
                .isEqualTo(PermissionBehavior.DENY);
        assertThat(sansRegle(PermissionMode.BYPASS, ecriture))
                .as("⚠️ BYPASS autorise tout, y compris une suppression")
                .isEqualTo(PermissionBehavior.ALLOW);
        assertThat(sansRegle(PermissionMode.DONT_ASK, lecture))
                .as("DONT_ASK refuse tout ce qui n'est pas explicitement permis")
                .isEqualTo(PermissionBehavior.DENY);
    }

    private static PermissionBehavior sansRegle(PermissionMode mode,
                                                ToolBase outil) {
        PermissionDecision decision =
                new PermissionEngine(
                        PermissionContextState.builder().mode(mode).build())
                        .checkPermission(outil, Map.of("reference", "OFF-101"))
                        .block();
        return decision == null ? null : decision.getBehavior();
    }

    // -- de bout en bout, a travers la boucle ------------------------------

    @Test
    @Timeout(90)
    @DisplayName("⚠️ LA MESURE : sous DENY, le catalogue n'est PAS appele")
    void sousDenyRienNeSExecute() {
        Resultat refus = jouer(PermissionBehavior.DENY);
        Resultat permis = jouer(PermissionBehavior.ALLOW);

        assertThat(refus.outilsExecutes())
                .as("le modele a demande, le runtime a refuse")
                .isZero();
        assertThat(refus.offresRestantes()).isEqualTo(6);

        assertThat(permis.outilsExecutes()).isEqualTo(1);
        assertThat(permis.offresRestantes())
                .as("la meme intention, autorisee, supprime bien une offre")
                .isEqualTo(5);
    }

    @Test
    @Timeout(90)
    @DisplayName("un refus revient au modele comme un RESULTAT, pas comme une exception")
    void leRefusEstUnResultat() {
        Resultat refus = jouer(PermissionBehavior.DENY);

        // ⚠️ Le modele apprend qu'il n'a pas le droit, et peut s'adapter. Une
        // exception aurait casse la conversation.
        assertThat(refus.typesDEvenements())
                .contains(AgentEventType.TOOL_RESULT_END)
                .doesNotContain(AgentEventType.REQUIRE_USER_CONFIRM);
    }

    @Test
    @Timeout(90)
    @DisplayName("⚠️ LA MESURE : sous ASK, l'agent repond « c'est fait » alors que RIEN n'a ete fait")
    void sousAskLAgentRepondQuandMeme() {
        Resultat attente = jouer(PermissionBehavior.ASK);

        // Le runtime a bien annonce qu'une confirmation etait requise...
        assertThat(attente.typesDEvenements())
                .contains(AgentEventType.REQUIRE_USER_CONFIRM);
        // ... et il n'a rien execute.
        assertThat(attente.outilsExecutes()).isZero();
        assertThat(attente.offresRestantes()).isEqualTo(6);

        // ⚠️ MAIS IL N'A PAS ATTENDU. ASK n'est pas une suspension
        // automatique : c'est un PROTOCOLE. Le framework emet l'evenement et
        // rend la main ; c'est a l'APPLICATION de s'arreter la, de poser la
        // question, et de reprendre avec la reponse. Une interface qui
        // ignore cet evenement affiche une confirmation pour une action qui
        // n'a jamais eu lieu.
        //
        // La regle : si votre interface ne sait pas traiter
        // REQUIRE_USER_CONFIRM, posez DENY, pas ASK.
        assertThat(attente.reponseFinale())
                .as("l'agent annonce le succes d'une action qui n'a pas eu lieu")
                .contains("fait");
    }

    private record Resultat(int offresRestantes, int outilsExecutes,
                            List<AgentEventType> typesDEvenements,
                            String reponseFinale) {
    }

    private static Resultat jouer(PermissionBehavior regle) {
        CatalogueOffres catalogue = new CatalogueOffres();
        Toolkit toolkit = new Toolkit();
        toolkit.registerTool(catalogue);

        PermissionContextState.Builder contexte = PermissionContextState.builder();
        PermissionRule sur = new PermissionRule("supprimer_offre", TOUS, regle,
                                                "test");
        switch (regle) {
            case ALLOW -> contexte.addAllowRule("supprimer_offre", sur);
            case ASK -> contexte.addAskRule("supprimer_offre", sur);
            case DENY -> contexte.addDenyRule("supprimer_offre", sur);
            default -> throw new IllegalArgumentException(regle.toString());
        }

        ReActAgent agent = ReActAgent.builder()
                .name("conseiller-" + regle.getValue())
                .sysPrompt("Tu es le conseiller carriere syllatech.")
                .model(new ModeleFactice("factice:" + regle.getValue(), List.of(
                        new ModeleFactice.Tour.AppelDOutil("supprimer_offre",
                                Map.of("reference", "OFF-101")),
                        new ModeleFactice.Tour.Reponse("C'est fait."))))
                .toolkit(toolkit)
                .maxIters(3)
                .permissionContext(contexte.build())
                .build();

        // On lit le flux pour voir ce que le runtime ANNONCE, puis on rejoue
        // la meme demande pour lire ce qu'il REND a l'utilisateur.
        List<AgentEvent> evenements = agent
                .streamEvents("Fais le menage dans les offres.",
                        RuntimeContext.builder()
                                .sessionId("s-" + regle).userId("awa").build())
                .take(Duration.ofSeconds(15))
                .collectList()
                .block();

        Msg reponse = agent.call("Fais le menage dans les offres.",
                        RuntimeContext.builder()
                                .sessionId("s2-" + regle).userId("awa").build())
                .block(Duration.ofSeconds(15));

        return new Resultat(catalogue.nombreDOffres(), catalogue.journal().size(),
                evenements == null ? List.of()
                        : evenements.stream().map(AgentEvent::getType).toList(),
                reponse == null ? "" : reponse.getTextContent());
    }
}
