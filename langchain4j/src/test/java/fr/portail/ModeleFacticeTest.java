package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.model.chat.Capability;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.service.AiServices;
import fr.portail.modele.ModeleFactice;
import fr.portail.service.AssistantCarriere;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * L'instrument de mesure lui-même.
 *
 * <p>Tout le projet repose sur {@link ModeleFactice} : si lui se trompe, les
 * six chapitres mentent avec assurance. Ces tests vérifient donc ce qu'il
 * promet — qu'il retient tout, qu'il rend ce qu'on lui a dit de rendre, et
 * qu'il se branche là où LangChain4j l'attend.
 */
class ModeleFacticeTest {

    @Test
    @DisplayName("il retient chaque requete recue, dans l'ordre")
    void ilRetientTout() {
        var modele = new ModeleFactice();
        var assistant = AiServices.create(AssistantCarriere.class, modele);

        assistant.conseiller("premier");
        assistant.conseiller("second");

        assertThat(modele.appels()).isEqualTo(2);
        assertThat(modele.recues()).hasSize(2);
        assertThat(modele.dernierTexte()).contains("second");
    }

    @Test
    @DisplayName("`oublier()` vide la memoire des appels, pas les regles")
    void oublierNeCassePasLesRegles() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "toujours la meme chose");
        var assistant = AiServices.create(AssistantCarriere.class, modele);

        assistant.conseiller("bonjour");
        modele.oublier();
        String apres = assistant.conseiller("bonjour");

        assertThat(modele.appels()).isEqualTo(1);
        assertThat(apres).isEqualTo("toujours la meme chose");
    }

    @Test
    @DisplayName("les regles sont essayees dans l'ordre, la derniere ajoutee d'abord")
    void lOrdreDesRegles() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> prompt.contains("conseil") ? "premiere" : null);
        modele.repondre(prompt -> prompt.contains("conseil") ? "seconde" : null);

        assertThat(AiServices.create(AssistantCarriere.class, modele)
                .conseiller("un conseil ?"))
                .as("`repondre` ajoute EN TETE : la derniere posee gagne")
                .isEqualTo("seconde");
    }

    /**
     * ⚠️ Le piège que le chapitre 6 mesure, figé en test.
     *
     * <p>{@code chat} est l'enveloppe qui prévient les écouteurs ;
     * {@code doChat} est la méthode à écrire. Ce test vérifie que ce projet
     * redéfinit bien la seconde — une régression le rendrait muet sans rien
     * casser d'autre.
     */
    @Test
    @DisplayName("c'est `doChat` qui est redefini, pas `chat`")
    void cEstDoChatQuiEstRedefini() throws Exception {
        assertThat(ModeleFactice.class.getDeclaredMethod("doChat",
                ChatRequest.class)).isNotNull();
        assertThatThrownBy(() -> ModeleFactice.class.getDeclaredMethod("chat",
                ChatRequest.class))
                .as("redefinir `chat` desactiverait tous les ChatModelListener")
                .isInstanceOf(NoSuchMethodException.class);
    }

    @Test
    @DisplayName("les capacites declarees changent ce que LangChain4j envoie")
    void lesCapacitesSontDeclarees() {
        var modele = new ModeleFactice();
        assertThat(modele.supportedCapabilities()).isEmpty();

        modele.sachant(Capability.RESPONSE_FORMAT_JSON_SCHEMA);

        assertThat(modele.supportedCapabilities())
                .containsExactly(Capability.RESPONSE_FORMAT_JSON_SCHEMA);
    }

    @Test
    @DisplayName("il sait rendre une demande d'outil, sans texte")
    void ilSaitDemanderUnOutil() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> ToolExecutionRequest.builder()
                .id("un").name("rechercherOffres")
                .arguments("{\"motCle\":\"java\"}").build());

        var reponse = modele.doChat(ChatRequest.builder()
                .messages(UserMessage.from("trouve")).build());

        assertThat(reponse.aiMessage().hasToolExecutionRequests()).isTrue();
        assertThat(reponse.aiMessage().toolExecutionRequests())
                .singleElement()
                .satisfies(appel -> {
                    assertThat(appel.name()).isEqualTo("rechercherOffres");
                    assertThat(appel.arguments()).contains("java");
                });
        assertThat(reponse.finishReason())
                .isEqualTo(dev.langchain4j.model.output.FinishReason.TOOL_EXECUTION);
    }

    @Test
    @DisplayName("l'usage de jetons est rempli : le chapitre 6 en depend")
    void lUsageEstRempli() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "trois mots ici");

        var usage = modele.doChat(ChatRequest.builder()
                .messages(UserMessage.from("une question de cinq mots"))
                .build()).tokenUsage();

        assertThat(usage.inputTokenCount()).isPositive();
        assertThat(usage.outputTokenCount()).isEqualTo(3);
    }

    @Test
    @DisplayName("une regle qui echoue laisse passer l'exception")
    void lesPannesRemontent() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> {
            throw new IllegalStateException("503 chez le fournisseur");
        });

        assertThatThrownBy(() -> AiServices.create(AssistantCarriere.class, modele)
                .conseiller("bonjour"))
                .as("un modele qui avale ses pannes rendrait la section "
                    + "resilience du chapitre 6 fausse")
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("503");
    }

    /**
     * ⚠️ {@code singleText()} lève dès qu'un message porte une image.
     *
     * <p>C'est ce qui a fait planter le chapitre 5 la première fois. Un
     * message utilisateur est une LISTE de contenus, et le rendu doit tenir
     * compte de tous.
     */
    @Test
    @DisplayName("un message multimodal se rend sans exploser")
    void leRenduTientLeMultimodal() {
        var message = UserMessage.from(
                dev.langchain4j.data.message.TextContent.from("lis ce CV"),
                dev.langchain4j.data.message.ImageContent.from(
                        dev.langchain4j.data.image.Image.builder()
                                .base64Data("AAAA").mimeType("image/png")
                                .build()));

        assertThat(ModeleFactice.contenu(message))
                .contains("lis ce CV")
                .contains("image/png");
    }

    /**
     * ⚠️ Le test passe par le modèle directement, et non par l'assistant.
     *
     * <p>Le {@code @SystemMessage} d'{@link AssistantCarriere} contient le
     * mot « conseiller » — et la règle des conseils, qui cherche
     * « conseil », s'y déclenche quelle que soit la question. C'est un
     * rappel utile : le message système fait partie de ce que le modèle lit,
     * y compris quand on l'a oublié.
     */
    @Test
    @DisplayName("sans regle applicable, il le dit plutot que d'inventer")
    void ilAvoueSonIgnorance() {
        var modele = new ModeleFactice();

        var reponse = modele.doChat(ChatRequest.builder()
                .messages(UserMessage.from("Quel temps fait-il a Lyon ?"))
                .build());

        assertThat(reponse.aiMessage().text())
                .isEqualTo("Je n'ai pas d'information la-dessus.");
    }

    @Test
    @DisplayName("les six chapitres existent")
    void lesSixChapitres() {
        for (var nom : List.of("Chapitre1Demarrer", "Chapitre2AiServices",
                "Chapitre3Rag", "Chapitre4Outils", "Chapitre5Memoire",
                "Chapitre6Production")) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }
}
