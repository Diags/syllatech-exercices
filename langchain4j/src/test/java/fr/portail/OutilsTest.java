package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.message.ToolExecutionResultMessage;
import dev.langchain4j.service.AiServices;
import fr.portail.modele.ModeleFactice;
import fr.portail.outils.OutilsDOffres;
import fr.portail.service.AssistantCarriere;
import java.util.ArrayList;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Les outils : le schéma déduit, le voyage hors du prompt, l'aller-retour.
 *
 * <p>Le chapitre 4 imprime ces mesures ; ces tests les figent. Le plus utile
 * d'entre eux est sans doute {@link #laBoucleParDefautEstEnorme()} : il garde
 * la trace d'un défaut que personne n'annonce — cent appels d'outils avant
 * que LangChain4j ne s'arrête.
 */
class OutilsTest {

    private final OutilsDOffres outils = new OutilsDOffres();

    @BeforeEach
    void repartirDeZero() {
        OutilsDOffres.remettreAZero();
    }

    @Test
    @DisplayName("LangChain4j deduit une specification de chaque `@Tool`")
    void laSpecificationEstDeduite() {
        var modele = new ModeleFactice();
        AiServices.builder(AssistantCarriere.class).chatModel(modele)
                .tools(outils).build().conseiller("bonjour");

        var specifications = modele.derniereRequete().toolSpecifications();
        assertThat(specifications).hasSize(3);
        var cherche = specifications.stream()
                .filter(s -> s.name().equals("rechercherOffres"))
                .findFirst().orElseThrow();
        assertThat(cherche.description()).contains("mot-cle");
        assertThat(String.valueOf(cherche.parameters()))
                .as("le nom du parametre survit grace a -parameters")
                .contains("motCle")
                .as("la description de @P finit dans le schema")
                .contains("en minuscules");
    }

    @Test
    @DisplayName("les outils voyagent hors du prompt")
    void lesOutilsVoyagentHorsDuPrompt() {
        var modele = new ModeleFactice();
        AiServices.create(AssistantCarriere.class, modele).conseiller("Bonjour");
        int sansOutils = modele.dernierTexte().length();

        AiServices.builder(AssistantCarriere.class).chatModel(modele)
                .tools(outils).build().conseiller("Bonjour");

        assertThat(modele.dernierTexte()).hasSize(sansOutils);
        assertThat(modele.derniereRequete().toolSpecifications()).hasSize(3);
    }

    @Test
    @DisplayName("l'aller-retour complet : demande, execution, reponse")
    void lAllerRetourComplet() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> prompt.contains("rechercherOffres a rendu")
                ? null
                : ToolExecutionRequest.builder().id("un")
                        .name("rechercherOffres")
                        .arguments("{\"motCle\":\"teletravail\"}").build());
        modele.repondre(prompt -> prompt.contains("rechercherOffres a rendu")
                ? "Trois offres proposent du teletravail." : null);

        String reponse = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele).tools(outils).build()
                .conseiller("Quelles offres proposent du teletravail ?");

        assertThat(modele.appels())
                .as("un outil coute DEUX appels au modele, pas un")
                .isEqualTo(2);
        assertThat(OutilsDOffres.appels()).isEqualTo(1);
        assertThat(reponse).isEqualTo("Trois offres proposent du teletravail.");
        assertThat(modele.dernierTexte())
                .contains("[AI] appelle rechercherOffres")
                .contains("[TOOL_EXECUTION_RESULT] rechercherOffres a rendu")
                .contains("OFF-014");
    }

    @Test
    @DisplayName("`beforeToolExecution` voit le nom et les arguments")
    void leCrochetVoitPasser() {
        var modele = new ModeleFactice();
        var vus = new ArrayList<String>();
        modele.demanderOutil(prompt -> prompt.contains("postuler a rendu")
                ? null
                : ToolExecutionRequest.builder().id("un").name("postuler")
                        .arguments("{\"reference\":\"OFF-999\"}").build());

        AiServices.builder(AssistantCarriere.class).chatModel(modele)
                .tools(outils)
                .beforeToolExecution(avant -> vus.add(avant.request().name()))
                .build().conseiller("Postule sur OFF-999");

        assertThat(vus).containsExactly("postuler");
    }

    @Test
    @DisplayName("l'outil qui ecrit refuse une reference inconnue")
    void lOutilQuiEcritRefuse() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> prompt.contains("postuler a rendu")
                ? null
                : ToolExecutionRequest.builder().id("un").name("postuler")
                        .arguments("{\"reference\":\"OFF-999\"}").build());

        AiServices.builder(AssistantCarriere.class).chatModel(modele)
                .tools(outils).build().conseiller("Postule sur OFF-999");

        assertThat(OutilsDOffres.appels())
                .as("on ne peut PAS empecher l'appel : seulement le refuser")
                .isEqualTo(1);
        assertThat(OutilsDOffres.candidatures()).isEmpty();
        assertThat(modele.dernierTexte()).contains("refus");
    }

    @Test
    @DisplayName("l'outil qui ecrit accepte une reference connue")
    void lOutilQuiEcritAccepte() {
        assertThat(outils.postuler("OFF-014")).contains("enregistree");
        assertThat(OutilsDOffres.candidatures()).containsExactly("OFF-014");
    }

    @Test
    @DisplayName("par defaut, un outil invente fait echouer l'appel")
    void lOutilInventeEchoue() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> ToolExecutionRequest.builder()
                .id("un").name("supprimerToutesLesOffres").arguments("{}")
                .build());

        assertThatThrownBy(() -> AiServices.builder(AssistantCarriere.class)
                .chatModel(modele).tools(outils).build()
                .conseiller("Fais le menage."))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("supprimerToutesLesOffres");
    }

    @Test
    @DisplayName("une strategie posee laisse la conversation continuer")
    void laStrategieChangeTout() {
        var modele = new ModeleFactice();
        var insistance = new AtomicInteger();
        modele.demanderOutil(prompt -> insistance.incrementAndGet() > 1 ? null
                : ToolExecutionRequest.builder().id("un")
                        .name("supprimerToutesLesOffres").arguments("{}")
                        .build());
        modele.repondre(prompt -> "Je ne peux pas faire cela.");

        String reponse = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele).tools(outils)
                .hallucinatedToolNameStrategy(demande ->
                        ToolExecutionResultMessage.from(demande,
                                "Erreur : outil inconnu."))
                .build().conseiller("Fais le menage.");

        assertThat(reponse).isEqualTo("Je ne peux pas faire cela.");
        assertThat(modele.appels()).isEqualTo(2);
    }

    /**
     * ⚠️ Le défaut que personne n'annonce.
     *
     * <p>{@code maxSequentialToolsInvocations} vaut 100 par défaut. Un modèle
     * qui redemande toujours le même outil déclenche donc cent exécutions et
     * cent-et-un appels au modèle, pour une seule question. C'est un plafond
     * de sécurité, pas un plafond de coût.
     */
    @Test
    @DisplayName("le plafond par defaut laisse passer cent appels d'outils")
    void laBoucleParDefautEstEnorme() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> ToolExecutionRequest.builder()
                .id("boucle").name("salaireDe")
                .arguments("{\"reference\":\"OFF-014\"}").build());
        modele.repondre(prompt -> "J'abandonne.");

        try {
            AiServices.builder(AssistantCarriere.class).chatModel(modele)
                    .tools(outils).build().conseiller("Et le salaire ?");
        } catch (RuntimeException arret) {
            // le plafond peut se signaler par une exception
        }

        assertThat(OutilsDOffres.appels()).isEqualTo(100);
        assertThat(modele.appels()).isGreaterThan(100);
    }

    @Test
    @DisplayName("`maxSequentialToolsInvocations` ramene cela a une valeur assumee")
    void lePlafondSeRegle() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> ToolExecutionRequest.builder()
                .id("boucle").name("salaireDe")
                .arguments("{\"reference\":\"OFF-014\"}").build());
        modele.repondre(prompt -> "J'abandonne.");

        try {
            AiServices.builder(AssistantCarriere.class).chatModel(modele)
                    .tools(outils).maxSequentialToolsInvocations(3).build()
                    .conseiller("Et le salaire ?");
        } catch (RuntimeException arret) {
            // idem
        }

        assertThat(OutilsDOffres.appels()).isEqualTo(3);
    }
}
