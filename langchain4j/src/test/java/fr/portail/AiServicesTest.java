package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.model.chat.Capability;
import dev.langchain4j.service.AiServices;
import fr.portail.modele.ModeleFactice;
import fr.portail.service.AnalyseurCV;
import fr.portail.service.AssistantAvecMemoire;
import fr.portail.service.AssistantCarriere;
import java.lang.reflect.Proxy;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Ce qu'une interface annotée fabrique vraiment.
 *
 * <p>Le chapitre 2 affirme trois choses : le proxy construit les messages, un
 * type de retour impose un format, et {@code @V} sépare la valeur du
 * template. Ces tests les vérifient sans lire l'écran — et gèlent surtout la
 * découverte du chapitre : LangChain4j impose un format de <strong>deux</strong>
 * façons, selon ce que le modèle déclare savoir faire.
 */
class AiServicesTest {

    private static final String CV = "Sept ans en Java, dont trois sur Spring "
            + "Boot. Cherche un poste a Lyon.";

    @Test
    @DisplayName("l'objet rendu est un proxy JDK, sans classe ecrite")
    void leProxyExiste() {
        var assistant = AiServices.create(AssistantCarriere.class,
                new ModeleFactice());

        assertThat(Proxy.isProxyClass(assistant.getClass())).isTrue();
        assertThat(assistant).isInstanceOf(AssistantCarriere.class);
    }

    @Test
    @DisplayName("`@SystemMessage` produit un second message, a chaque appel")
    void leMessageSystemePartToujours() {
        var modele = new ModeleFactice();
        var assistant = AiServices.create(AssistantCarriere.class, modele);

        assistant.conseiller("bonjour");
        var premier = modele.derniersMessages();
        assistant.conseiller("encore");

        assertThat(premier).hasSize(2);
        assertThat(modele.derniersMessages()).hasSize(2);
        assertThat(modele.dernierTexte()).contains("[SYSTEM]", "conseiller");
    }

    /**
     * ⚠️ La découverte du chapitre 2, figée.
     *
     * <p>Sans capacité déclarée, les instructions de format sont écrites en
     * toutes lettres dans le message utilisateur. Avec
     * {@code RESPONSE_FORMAT_JSON_SCHEMA}, elles disparaissent du prompt et
     * voyagent dans la requête. Le même code Java, deux prompts.
     */
    @Test
    @DisplayName("sans capacite, le schema est ecrit dans le prompt")
    void leSchemaEstDansLePrompt() {
        var modele = new ModeleFactice();

        AiServices.create(AnalyseurCV.class, modele)
                .analyser("developpeuse Java", CV);

        assertThat(modele.dernierTexte())
                .contains("JSON")
                .contains("competences")
                .contains("score");
        assertThat(modele.derniereRequete().responseFormat())
                .as("aucun format n'est pose : tout est dans le texte")
                .isNull();
    }

    @Test
    @DisplayName("avec la capacite, le schema quitte le prompt")
    void leSchemaQuitteLePrompt() {
        var modele = new ModeleFactice()
                .sachant(Capability.RESPONSE_FORMAT_JSON_SCHEMA);

        AiServices.create(AnalyseurCV.class, modele)
                .analyser("developpeuse Java", CV);

        assertThat(modele.dernierTexte())
                .as("le prompt redevient propre")
                .doesNotContain("JSON");
        assertThat(modele.derniereRequete().responseFormat()).isNotNull();
        assertThat(String.valueOf(modele.derniereRequete().responseFormat()
                .jsonSchema()))
                .contains("competences", "score", "resume");
    }

    @Test
    @DisplayName("le prompt est plus court quand le schema voyage a cote")
    void leSchemaDansLaRequeteRaccourcitLePrompt() {
        var simple = new ModeleFactice();
        var capable = new ModeleFactice()
                .sachant(Capability.RESPONSE_FORMAT_JSON_SCHEMA);

        AiServices.create(AnalyseurCV.class, simple).analyser("poste", CV);
        AiServices.create(AnalyseurCV.class, capable).analyser("poste", CV);

        assertThat(capable.dernierTexte().length())
                .isLessThan(simple.dernierTexte().length());
    }

    @Test
    @DisplayName("le record rendu est vraiment type")
    void leRecordEstType() {
        var analyse = AiServices.create(AnalyseurCV.class, new ModeleFactice())
                .analyser("developpeuse Java", CV);

        assertThat(analyse).isInstanceOf(AnalyseurCV.Analyse.class);
        assertThat(analyse.score()).isEqualTo(78);
        assertThat(analyse.competences()).contains("Java", "Spring");
    }

    @Test
    @DisplayName("un modele qui n'obeit pas fait echouer la conversion")
    void laConversionEchoueBruyamment() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> "Bien sur ! Voici l'analyse : bon profil.");

        assertThatThrownBy(() -> AiServices.create(AnalyseurCV.class, modele)
                .analyser("developpeuse Java", CV))
                .as("aucun type Java ne protege d'un modele bavard")
                .isInstanceOf(RuntimeException.class);
    }

    @Test
    @DisplayName("ce qui passe par `@V` est une valeur, jamais un template")
    void laValeurNEstPasUnTemplate() {
        var modele = new ModeleFactice();

        AiServices.create(AssistantCarriere.class, modele)
                .conseilCible("developpeur qui ecrit {{utilisateur}}", "Lyon");

        assertThat(modele.dernierTexte())
                .as("la substitution n'a lieu qu'une fois")
                .contains("{{utilisateur}}")
                .contains("Lyon");
    }

    @Test
    @DisplayName("la memoire rejoue tout l'historique a chaque tour")
    void laMemoireRejoueTout() {
        var modele = new ModeleFactice();
        var assistant = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .chatMemory(MessageWindowChatMemory.withMaxMessages(10))
                .build();

        var tailles = new ArrayList<Integer>();
        for (var tour : List.of("bonjour", "et le salaire ?", "et le teletravail ?")) {
            assistant.conseiller(tour);
            tailles.add(modele.derniersMessages().size());
        }

        assertThat(tailles)
                .as("systeme + question, puis + reponse + question, etc.")
                .containsExactly(2, 4, 6);
    }

    @Test
    @DisplayName("la fenetre borne ce qui est renvoye")
    void laFenetreBorne() {
        var modele = new ModeleFactice();
        var assistant = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .chatMemory(MessageWindowChatMemory.withMaxMessages(4))
                .build();

        for (int tour = 0; tour < 6; tour++) {
            assistant.conseiller("tour " + tour);
        }

        assertThat(modele.derniersMessages().size())
                .as("sans fenetre, le sixieme tour en enverrait douze")
                .isLessThanOrEqualTo(5);
    }

    /**
     * ⚠️ Un seul {@code @MemoryId} rend le provider obligatoire — au BUILD.
     */
    @Test
    @DisplayName("`@MemoryId` sans provider est refuse a la construction")
    void memoryIdExigeUnProvider() {
        assertThatThrownBy(() -> AiServices.create(AssistantAvecMemoire.class,
                new ModeleFactice()))
                .isInstanceOf(RuntimeException.class)
                .hasMessageContaining("ChatMemoryProvider");
    }

    @Test
    @DisplayName("`@MemoryId` isole vraiment deux conversations")
    void memoryIdIsole() {
        var modele = new ModeleFactice();
        var assistant = AiServices.builder(AssistantAvecMemoire.class)
                .chatModel(modele)
                .chatMemoryProvider(id -> MessageWindowChatMemory.withMaxMessages(10))
                .build();

        assistant.discuter("awa", "Je cherche un poste a Lyon.");
        assistant.discuter("karim", "Je cherche un poste a Nantes.");
        assistant.discuter("awa", "Et le salaire ?");
        String vuParAwa = modele.dernierTexte();
        assistant.discuter("karim", "Et le salaire ?");
        String vuParKarim = modele.dernierTexte();

        assertThat(vuParAwa).contains("Lyon").doesNotContain("Nantes");
        assertThat(vuParKarim).contains("Nantes").doesNotContain("Lyon");
    }
}
