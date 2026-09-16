package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.service.AiServices;
import fr.portail.modele.JournalDesAppels;
import fr.portail.modele.ModeleFactice;
import fr.portail.modele.ModeleFacticeEnFlux;
import fr.portail.service.AssistantCarriere;
import fr.portail.service.AssistantEnFlux;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * L'observabilité, le streaming, et ce que coûte la résilience.
 *
 * <p>Le test le plus important de ce fichier est
 * {@link #redefinirChatRendLEcouteurMuet()} : il fige la correction que le
 * chapitre 6 apporte à l'exemple du cours.
 */
class ProductionTest {

    @Test
    @DisplayName("l'ecouteur voit chaque requete, chaque reponse, ses jetons")
    void lEcouteurVoitTout() {
        var modele = new ModeleFactice();
        var journal = new JournalDesAppels();
        modele.ecouter(journal);
        var assistant = AiServices.create(AssistantCarriere.class, modele);

        for (int i = 0; i < 3; i++) {
            assistant.conseiller("Donne 3 conseils pour un entretien");
        }

        assertThat(journal.requetes()).isEqualTo(3);
        assertThat(journal.reponses()).isEqualTo(3);
        assertThat(journal.erreurs()).isZero();
        assertThat(journal.jetonsEntree()).isPositive();
        assertThat(journal.jetonsSortie()).isPositive();
    }

    /**
     * ⚠️ La correction du chapitre 6, figée.
     *
     * <p>L'exemple de modèle bouchonné du cours redéfinit
     * {@code chat(ChatRequest)}. Or {@code chat} est l'enveloppe qui prévient
     * les écouteurs : la redéfinir désactive toute l'observabilité, sans
     * erreur et sans message.
     */
    @Test
    @DisplayName("redefinir `chat` rend l'ecouteur totalement muet")
    void redefinirChatRendLEcouteurMuet() {
        var journal = new JournalDesAppels();
        var bouchon = new BouchonQuiRedefinitChat(journal);
        var assistant = AiServices.create(AssistantCarriere.class, bouchon);

        for (int i = 0; i < 3; i++) {
            assistant.conseiller("Donne 3 conseils");
        }

        assertThat(bouchon.appels())
                .as("le modele a bien ete appele trois fois")
                .isEqualTo(3);
        assertThat(journal.requetes())
                .as("et l'ecouteur n'a rien vu du tout")
                .isZero();
    }

    @Test
    @DisplayName("une panne declenche `onError`, et aucun jeton n'est compte")
    void lAppelRateNeCompteRien() {
        var modele = new ModeleFactice();
        var journal = new JournalDesAppels();
        modele.ecouter(journal);
        modele.repondre(prompt -> {
            throw new IllegalStateException("503 chez le fournisseur");
        });

        try {
            AiServices.create(AssistantCarriere.class, modele)
                    .conseiller("bonjour");
        } catch (RuntimeException attendue) {
            // c'est le cas mesure
        }

        assertThat(journal.erreurs()).isEqualTo(1);
        assertThat(journal.reponses()).isZero();
        assertThat(journal.jetonsEntree() + journal.jetonsSortie())
                .as("les reessais sont invisibles dans le compteur de jetons")
                .isZero();
    }

    @Test
    @DisplayName("trois reessais ne comptent qu'un appel de jetons")
    void lesReessaisSontInvisiblesCoteJetons() {
        var modele = new ModeleFactice();
        var journal = new JournalDesAppels();
        modele.ecouter(journal);
        var pannes = new AtomicInteger();
        modele.repondre(prompt -> {
            if (pannes.incrementAndGet() % 3 != 0) {
                throw new IllegalStateException("503");
            }
            return "Trois offres proposent du teletravail.";
        });
        var assistant = AiServices.create(AssistantCarriere.class, modele);

        String recu = null;
        for (int tentative = 0; tentative < 3 && recu == null; tentative++) {
            try {
                recu = assistant.conseiller("les offres ?");
            } catch (RuntimeException panne) {
                recu = null;
            }
        }

        assertThat(recu).isNotNull();
        assertThat(modele.appels()).isEqualTo(3);
        assertThat(journal.erreurs()).isEqualTo(2);
        assertThat(journal.reponses())
                .as("un seul appel a abouti, sur trois factures")
                .isEqualTo(1);
    }

    @Test
    @DisplayName("le flux rend des morceaux qui se recollent a l'identique")
    void leFluxSeRecolle() throws Exception {
        var modele = new ModeleFactice();
        var enFlux = new ModeleFacticeEnFlux(modele);
        var morceaux = new ArrayList<String>();
        var attente = new CountDownLatch(1);

        AiServices.builder(AssistantEnFlux.class)
                .streamingChatModel(enFlux).build()
                .conseiller("Donne 3 conseils pour un entretien")
                .onPartialResponse(morceaux::add)
                .onCompleteResponse(complete -> attente.countDown())
                .onError(erreur -> attente.countDown())
                .start();

        assertThat(attente.await(30, TimeUnit.SECONDS)).isTrue();
        assertThat(morceaux).hasSizeGreaterThan(1);
        modele.oublier();
        String dUnSeulCoup = AiServices.create(AssistantCarriere.class, modele)
                .conseiller("Donne 3 conseils pour un entretien");
        assertThat(String.join("", morceaux)).isEqualTo(dUnSeulCoup);
    }

    @Test
    @DisplayName("aucun module de fournisseur dans le classpath")
    void aucunFournisseur() {
        for (var classe : List.of(
                "dev.langchain4j.model.openai.OpenAiChatModel",
                "dev.langchain4j.model.ollama.OllamaChatModel",
                "dev.langchain4j.model.anthropic.AnthropicChatModel")) {
            org.junit.jupiter.api.Assertions.assertThrows(
                    ClassNotFoundException.class, () -> Class.forName(classe),
                    classe + " ne devrait pas etre la : ce projet tourne "
                    + "hors ligne, sans cle");
        }
    }

    /** Le bouchon tel que le cours l'écrit — fonctionnel, et muet. */
    private static final class BouchonQuiRedefinitChat implements ChatModel {

        private final ChatModelListener ecouteur;
        private final AtomicInteger appels = new AtomicInteger();

        private BouchonQuiRedefinitChat(ChatModelListener ecouteur) {
            this.ecouteur = ecouteur;
        }

        @Override
        public ChatResponse chat(ChatRequest requete) {
            appels.incrementAndGet();
            return ChatResponse.builder()
                    .aiMessage(AiMessage.from("Reponse figee du bouchon."))
                    .build();
        }

        @Override
        public List<ChatModelListener> listeners() {
            return List.of(ecouteur);
        }

        int appels() {
            return appels.get();
        }
    }
}
