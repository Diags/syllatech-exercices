package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.modele.ModeleFactice;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.model.tool.ToolCallingChatOptions;

/**
 * L'instrument de mesure lui-même.
 *
 * <p>Tout le projet repose sur {@link ModeleFactice} : si lui se trompe, les
 * six chapitres mentent avec assurance. Ces tests vérifient donc ce qu'il
 * promet — qu'il retient tout, qu'il rend ce qu'on lui a dit de rendre, et
 * qu'il expose les options qu'un vrai fournisseur exposerait.
 */
class ModeleFacticeTest {

    @Test
    @DisplayName("il retient chaque prompt recu, dans l'ordre")
    void ilRetientTout() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele).build();

        client.prompt().user("premier").call().content();
        client.prompt().user("second").call().content();

        assertThat(modele.appels()).isEqualTo(2);
        assertThat(modele.recus()).hasSize(2);
        assertThat(modele.dernierTexte()).contains("second");
    }

    @Test
    @DisplayName("`oublier()` vide la memoire des appels, pas les regles")
    void oublierNeCassePasLesRegles() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "toujours la meme chose");
        var client = ChatClient.builder(modele).build();

        client.prompt().user("bonjour").call().content();
        modele.oublier();
        String apres = client.prompt().user("bonjour").call().content();

        assertThat(modele.appels()).isEqualTo(1);
        assertThat(apres).isEqualTo("toujours la meme chose");
    }

    @Test
    @DisplayName("les regles sont essayees dans l'ordre, la derniere ajoutee d'abord")
    void lOrdreDesRegles() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> prompt.contains("conseil") ? "premiere" : null);
        modele.repondre(prompt -> prompt.contains("conseil") ? "seconde" : null);

        assertThat(ChatClient.builder(modele).build().prompt()
                .user("un conseil ?").call().content())
                .as("`repondre` ajoute EN TETE : la derniere posee gagne")
                .isEqualTo("seconde");
    }

    /**
     * ⚠️ Le piège qui a coûté le plus cher dans ce projet.
     *
     * <p>{@code ChatModel} déclare {@code getOptions()} ET
     * {@code getDefaultOptions()}. C'est la première que {@code ChatClient}
     * appelle pour fabriquer les options de chaque requête. Redéfinir la
     * seconde — celle que toute la documentation de Spring AI 1.x nomme —
     * compile, s'exécute, et fait disparaître les outils sans un mot.
     */
    @Test
    @DisplayName("le modele expose des options qui savent porter des outils")
    void lesOptionsSaventPorterDesOutils() {
        var modele = new ModeleFactice();

        assertThat(modele.getOptions())
                .as("sans ToolCallingChatOptions, `.tools()` est perdu en silence")
                .isInstanceOf(ToolCallingChatOptions.class);
        assertThat(modele.getDefaultOptions())
                .as("la methode historique delegue a la nouvelle")
                .isInstanceOf(ToolCallingChatOptions.class);
    }

    @Test
    @DisplayName("il sait diffuser, et les morceaux se recollent")
    void leFluxSeRecolle() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "un deux trois quatre cinq");
        var morceaux = new java.util.ArrayList<String>();

        ChatClient.builder(modele).build().prompt().user("compte")
                .stream().content().doOnNext(morceaux::add).blockLast();

        assertThat(morceaux).hasSizeGreaterThan(1);
        assertThat(String.join("", morceaux)).isEqualTo("un deux trois quatre cinq");
    }

    @Test
    @DisplayName("il sait rendre une demande d'outil, sans texte")
    void ilSaitDemanderUnOutil() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> new AssistantMessage.ToolCall(
                "un", "function", "rechercherOffres", "{\"motCle\":\"java\"}"));

        var reponse = modele.call(new Prompt("trouve"));

        assertThat(reponse.getResult().getOutput().hasToolCalls()).isTrue();
        assertThat(reponse.getResult().getOutput().getToolCalls())
                .singleElement()
                .satisfies(appel -> {
                    assertThat(appel.name()).isEqualTo("rechercherOffres");
                    assertThat(appel.arguments()).contains("java");
                });
        assertThat(reponse.getResult().getMetadata().getFinishReason())
                .isEqualTo("tool_calls");
    }

    @Test
    @DisplayName("l'usage de jetons est rempli : le chapitre 6 en depend")
    void lUsageEstRempli() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "trois mots ici");

        var usage = modele.call(new Prompt("une question de cinq mots"))
                .getMetadata().getUsage();

        assertThat(usage.getPromptTokens()).isPositive();
        assertThat(usage.getCompletionTokens()).isEqualTo(3);
    }

    @Test
    @DisplayName("une regle qui echoue laisse passer l'exception")
    void lesPannesRemontent() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> {
            throw new IllegalStateException("503 chez le fournisseur");
        });

        assertThatThrownBy(() -> ChatClient.builder(modele).build()
                .prompt().user("bonjour").call().content())
                .as("un modele qui avale ses pannes rendrait la section "
                    + "resilience du chapitre 6 fausse")
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("503");
    }

    @Test
    @DisplayName("`conversation()` montre les appels d'outils, `dernierTexte()` non")
    void laConversationMontreLesOutils() {
        var modele = new ModeleFactice();
        modele.demanderOutil(prompt -> prompt.contains("salaireDe = ") ? null
                : new AssistantMessage.ToolCall("un", "function", "salaireDe",
                        "{\"reference\":\"OFF-014\"}"));
        modele.repondre(prompt -> prompt.contains("salaireDe = ")
                ? "Le salaire est de 52000 euros." : null);

        ChatClient.builder(modele).build().prompt().user("et le salaire ?")
                .tools(new fr.portail.outils.OutilsDOffres()).call().content();

        assertThat(modele.conversation())
                .contains("[ASSISTANT] appelle salaireDe")
                .contains("[TOOL] salaireDe a rendu");
        assertThat(modele.dernierTexte())
                .as("un ASSISTANT qui demande un outil n'a pas de texte")
                .contains("[ASSISTANT] ")
                .doesNotContain("appelle salaireDe");
    }

    @Test
    @DisplayName("sans regle applicable, il le dit plutot que d'inventer")
    void ilAvoueSonIgnorance() {
        var modele = new ModeleFactice();

        assertThat(ChatClient.builder(modele).build().prompt()
                .user("Quel temps fait-il a Lyon ?").call().content())
                .isEqualTo("Je n'ai pas d'information la-dessus.");
    }

    @Test
    @DisplayName("les medias joints sont visibles, et hors du texte")
    void lesMediasSontHorsDuTexte() {
        var modele = new ModeleFactice();

        ChatClient.builder(modele).build().prompt()
                .user(u -> u.text("lis ce CV").media(
                        org.springframework.util.MimeTypeUtils.IMAGE_PNG,
                        new org.springframework.core.io.ByteArrayResource(
                                new byte[] {1, 2, 3})))
                .call().content();

        assertThat(modele.derniersMedias()).hasSize(1);
        assertThat(modele.derniersMedias().getFirst().getMimeType().toString())
                .isEqualTo("image/png");
        assertThat(modele.dernierTexte()).isEqualTo("[USER] lis ce CV\n");
    }

    @Test
    @DisplayName("les six chapitres existent")
    void lesSixChapitres() {
        for (var nom : List.of("Chapitre1ChatClient", "Chapitre2Structure",
                "Chapitre3Rag", "Chapitre4Outils", "Chapitre5Multimodal",
                "Chapitre6Production")) {
            org.junit.jupiter.api.Assertions.assertDoesNotThrow(
                    () -> Class.forName("fr.portail.chapitres." + nom),
                    nom + " est introuvable");
        }
    }
}
