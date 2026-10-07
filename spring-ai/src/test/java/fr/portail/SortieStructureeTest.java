package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.modele.ModeleFactice;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.memory.ChatMemory;
import org.springframework.ai.chat.memory.MessageWindowChatMemory;

/**
 * Ce que {@code entity()} ajoute, et ce que le template casse.
 *
 * <p>Le chapitre 2 affirme trois choses : Spring AI écrit un schéma JSON à
 * votre place, la conversion échoue bruyamment si le modèle n'obéit pas, et
 * une accolade dans les données fait tomber la requête. Ces tests les
 * vérifient sans lire l'écran.
 */
class SortieStructureeTest {

    record AnalyseCV(String pointsForts, List<String> competences, int score) {
    }

    @Test
    @DisplayName("`entity()` colle un schema JSON complet a la fin du prompt")
    void leSchemaEstAjouteAuPrompt() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele).build();

        client.prompt().user("Analyse ce CV").call().entity(AnalyseCV.class);

        String envoye = modele.dernierTexte();
        assertThat(envoye)
                .contains("json-schema.org")
                .contains("\"pointsForts\"")
                .contains("\"competences\"")
                .contains("\"score\"")
                .contains("RFC8259");
        assertThat(envoye)
                .as("le schema doit nommer le type Java, pas seulement le champ")
                .contains("\"integer\"");
        assertThat(envoye.length())
                .as("votre phrase fait 13 caracteres ; le reste vient de Spring AI")
                .isGreaterThan(500);
    }

    @Test
    @DisplayName("le record rendu est vraiment type")
    void leRecordEstType() {
        var modele = new ModeleFactice();

        var analyse = ChatClient.builder(modele).build().prompt()
                .user("Analyse ce CV").call().entity(AnalyseCV.class);

        assertThat(analyse).isInstanceOf(AnalyseCV.class);
        assertThat(analyse.score()).isEqualTo(78);
        assertThat(analyse.competences()).contains("Java", "Spring");
    }

    @Test
    @DisplayName("un modele qui n'obeit pas fait echouer la conversion")
    void laConversionEchoueBruyamment() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "Bien sur ! Voici l'analyse : bon profil.");

        assertThatThrownBy(() -> ChatClient.builder(modele).build().prompt()
                .user("Analyse ce CV").call().entity(AnalyseCV.class))
                .as("aucun type Java ne protege d'un modele bavard")
                .isInstanceOf(RuntimeException.class);
    }

    /**
     * ⚠️ La règle du chapitre 2, mesurée.
     *
     * <p>Tant qu'aucun paramètre n'est fourni, le texte part tel quel et une
     * accolade dans les données ne gêne personne. Dès qu'<em>un</em>
     * paramètre existe, Spring AI rend le texte comme un template — et bute
     * sur les accolades venues des données.
     */
    @Test
    @DisplayName("une accolade dans les donnees ne casse rien... sans parametre")
    void sansParametreLesAccoladesPassent() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele).build();
        String cv = "ecrit des expressions comme {utilisateur} dans ses vues";

        String reponse = client.prompt().user("Analyse : " + cv)
                .call().content();

        assertThat(reponse).isNotNull();
        assertThat(modele.dernierTexte()).contains("{utilisateur}");
    }

    @Test
    @DisplayName("la meme accolade fait tomber la requete des qu'un parametre existe")
    void avecUnParametreLesAccoladesCassent() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele).build();
        String cv = "ecrit des expressions comme {utilisateur} dans ses vues";

        assertThatThrownBy(() -> client.prompt()
                .user(u -> u.text("Analyse : " + cv + " pour le poste {poste}")
                        .param("poste", "developpeur"))
                .call().content())
                .isInstanceOf(IllegalStateException.class);
    }

    @Test
    @DisplayName("ce qui passe par `param()` est une valeur, jamais un template")
    void paramEstUneValeur() {
        var modele = new ModeleFactice();
        String cv = "maitrise les templates : {utilisateur}, {poste}";

        ChatClient.builder(modele).build().prompt()
                .user(u -> u.text("Analyse ce CV : {cv}").param("cv", cv))
                .call().content();

        assertThat(modele.dernierTexte())
                .as("la substitution n'a lieu qu'une fois")
                .contains("{utilisateur}");
    }

    @Test
    @DisplayName("`ChatMemory` rejoue tout l'historique a chaque tour")
    void laMemoireRejoueTout() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele)
                .defaultAdvisors(MessageChatMemoryAdvisor.builder(
                        MessageWindowChatMemory.builder().maxMessages(10)
                                .build()).build())
                .build();

        var tailles = new java.util.ArrayList<Integer>();
        for (var tour : List.of("bonjour", "et le salaire ?", "et le teletravail ?")) {
            client.prompt().user(tour)
                    .advisors(a -> a.param(ChatMemory.CONVERSATION_ID, "awa"))
                    .call().content();
            tailles.add(modele.derniersMessages().size());
        }

        assertThat(tailles)
                .as("1 message, puis 3, puis 5 : l'historique est renvoye entier")
                .containsExactly(1, 3, 5);
    }

    @Test
    @DisplayName("la fenetre de memoire borne ce qui est renvoye")
    void laFenetreBorne() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele)
                .defaultAdvisors(MessageChatMemoryAdvisor.builder(
                        MessageWindowChatMemory.builder().maxMessages(4)
                                .build()).build())
                .build();

        for (int i = 0; i < 6; i++) {
            client.prompt().user("tour " + i)
                    .advisors(a -> a.param(ChatMemory.CONVERSATION_ID, "bornee"))
                    .call().content();
        }

        assertThat(modele.derniersMessages().size())
                .as("sans fenetre, le sixieme tour enverrait onze messages")
                .isLessThanOrEqualTo(5);
    }
}
