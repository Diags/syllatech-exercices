package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.observation.ObservationRegistry;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.evaluation.RelevancyEvaluator;
import org.springframework.ai.chat.observation.ChatModelMeterObservationHandler;
import org.springframework.ai.evaluation.EvaluationRequest;

/**
 * Les métriques, le juge, et ce que coûte la résilience.
 *
 * <p>Le chapitre 6 du cours nomme {@code gen_ai.client.token.usage} : ces
 * tests vérifient que la métrique existe vraiment, avec ses étiquettes, et
 * qu'elle ne compte que ce qu'elle peut compter.
 */
class ProductionTest {

    private static SimpleMeterRegistry brancher(ModeleFactice modele) {
        var compteurs = new SimpleMeterRegistry();
        var observations = ObservationRegistry.create();
        observations.observationConfig().observationHandler(
                new ChatModelMeterObservationHandler(compteurs));
        modele.observer(observations);
        return compteurs;
    }

    private static double valeur(SimpleMeterRegistry compteurs, String nom,
                                 String typeDeJeton) {
        double total = 0;
        for (var compteur : compteurs.getMeters()) {
            if (!compteur.getId().getName().equals(nom)) {
                continue;
            }
            if (typeDeJeton != null && !typeDeJeton.equals(
                    compteur.getId().getTag("gen_ai.token.type"))) {
                continue;
            }
            for (var mesure : compteur.measure()) {
                total += mesure.getValue();
            }
        }
        return total;
    }

    @Test
    @DisplayName("`gen_ai.client.token.usage` existe, avec ses etiquettes")
    void laMetriqueExiste() {
        var modele = new ModeleFactice();
        var compteurs = brancher(modele);

        ChatClient.builder(modele).build().prompt()
                .user("Donne 3 conseils pour un entretien").call().content();

        assertThat(compteurs.getMeters())
                .extracting(m -> m.getId().getName())
                .contains("gen_ai.client.token.usage");
        assertThat(valeur(compteurs, "gen_ai.client.token.usage", "input"))
                .isPositive();
        assertThat(valeur(compteurs, "gen_ai.client.token.usage", "output"))
                .isPositive();
        assertThat(valeur(compteurs, "gen_ai.client.token.usage", "total"))
                .isEqualTo(valeur(compteurs, "gen_ai.client.token.usage", "input")
                        + valeur(compteurs, "gen_ai.client.token.usage", "output"));
    }

    /**
     * ⚠️ L'instrumentation est dans le {@code ChatModel}, pas dans
     * {@code ChatClient}.
     *
     * <p>Un modèle qui n'ouvre pas l'observation n'expose rien — et le
     * tableau de bord reste vide sans qu'aucune erreur ne le signale.
     */
    @Test
    @DisplayName("sans registre branche, aucun compteur n'apparait")
    void sansRegistreRienNApparait() {
        var modele = new ModeleFactice();
        var compteurs = new SimpleMeterRegistry();

        ChatClient.builder(modele).build().prompt().user("bonjour")
                .call().content();

        assertThat(compteurs.getMeters()).isEmpty();
    }

    @Test
    @DisplayName("un appel qui echoue ne compte aucun jeton")
    void lAppelRateNeCompteRien() {
        var modele = new ModeleFactice();
        var compteurs = brancher(modele);
        modele.repondre(prompt -> {
            throw new IllegalStateException("503 chez le fournisseur");
        });

        try {
            ChatClient.builder(modele).build().prompt().user("bonjour")
                    .call().content();
        } catch (RuntimeException attendue) {
            // c'est le cas mesure
        }

        assertThat(valeur(compteurs, "gen_ai.client.token.usage", null))
                .as("les reessais sont invisibles dans le compteur de jetons")
                .isZero();
    }

    @Test
    @DisplayName("trois reessais ne comptent qu'un appel de jetons")
    void lesReessaisSontInvisibles() {
        var modele = new ModeleFactice();
        var compteurs = brancher(modele);
        var pannes = new AtomicInteger();
        modele.repondre(prompt -> {
            if (pannes.incrementAndGet() % 3 != 0) {
                throw new IllegalStateException("503");
            }
            return "Trois offres proposent du teletravail.";
        });
        var client = ChatClient.builder(modele).build();

        String recu = null;
        for (int tentative = 0; tentative < 3 && recu == null; tentative++) {
            try {
                recu = client.prompt().user("les offres ?").call().content();
            } catch (RuntimeException panne) {
                recu = null;
            }
        }

        assertThat(recu).isNotNull();
        assertThat(modele.appels()).isEqualTo(3);
        assertThat(valeur(compteurs, "gen_ai.client.token.usage", "output"))
                .as("un seul appel a rendu des jetons, sur trois factures")
                .isEqualTo(5);
    }

    /**
     * {@code isPass()} est une comparaison de chaîne, pas une note.
     *
     * <p>Spring AI compare la réponse du juge à « YES », sans tenir compte de
     * la casse, après un {@code strip()}. Un « Yes, absolument. » qui veut
     * dire oui est donc un échec — et c'est une source de faux rouges qu'il
     * vaut mieux connaître avant de chercher la panne ailleurs.
     */
    @ParameterizedTest(name = "le juge repond « {0} » : isPass = {1}")
    @CsvSource(delimiter = '|', textBlock = """
        YES               | true
        yes               | true
        '  YES  '         | true
        'YES.'            | false
        'Yes, absolument' | false
        NO                | false
        """)
    @DisplayName("`isPass()` compare une chaine, et rien d'autre")
    void isPassCompareUneChaine(String reponseDuJuge, boolean attendu) {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> prompt.contains("evaluate if the response")
                ? reponseDuJuge : null);

        var verdict = new RelevancyEvaluator(ChatClient.builder(modele))
                .evaluate(new EvaluationRequest("les offres ?", List.of(),
                        "OFF-014 propose du teletravail."));

        assertThat(verdict.isPass()).isEqualTo(attendu);
    }

    @Test
    @DisplayName("le juge recoit un prompt, comme n'importe quel appel")
    void leJugeEstUnAppelCommeUnAutre() {
        var modele = new ModeleFactice();
        modele.repondre(prompt -> prompt.contains("evaluate if the response")
                ? "YES" : null);

        new RelevancyEvaluator(ChatClient.builder(modele))
                .evaluate(new EvaluationRequest("les offres en teletravail ?",
                        List.of(), "OFF-014 propose du teletravail."));

        assertThat(modele.appels())
                .as("juger coute un appel de plus")
                .isEqualTo(1);
        assertThat(modele.dernierTexte())
                .contains("Either YES or NO")
                .contains("les offres en teletravail ?")
                .contains("OFF-014 propose du teletravail.");
    }

    @Test
    @DisplayName("aucun starter de fournisseur dans le classpath")
    void aucunFournisseur() {
        for (var classe : List.of(
                "org.springframework.ai.openai.OpenAiChatModel",
                "org.springframework.ai.anthropic.AnthropicChatModel",
                "org.springframework.ai.ollama.OllamaChatModel")) {
            org.junit.jupiter.api.Assertions.assertThrows(
                    ClassNotFoundException.class, () -> Class.forName(classe),
                    classe + " ne devrait pas etre la : ce projet tourne "
                    + "hors ligne, sans cle");
        }
    }
}
