package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.modele.ModeleFactice;
import fr.portail.rag.Corpus;
import fr.portail.rag.ModeleDEmbeddings;
import java.util.ArrayList;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.rag.advisor.RetrievalAugmentationAdvisor;
import org.springframework.ai.rag.retrieval.search.VectorStoreDocumentRetriever;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.SimpleVectorStore;
import org.springframework.ai.vectorstore.VectorStore;

/**
 * Le RAG, sans lire l'écran.
 *
 * <p>Ces tests ne démarrent pas d'application : ils construisent la base
 * vectorielle à la main. C'est à la fois plus rapide et plus honnête — ce qui
 * est vérifié ici est le comportement de Spring AI, pas celui du câblage
 * Spring.
 */
class RagTest {

    private static VectorStore base() {
        var base = SimpleVectorStore.builder(new ModeleDEmbeddings()).build();
        base.add(new ArrayList<>(Corpus.OFFRES));
        return base;
    }

    @Test
    @DisplayName("un vecteur d'embeddings est normalise")
    void leVecteurEstNormalise() {
        var vecteur = ModeleDEmbeddings.vecteur("Quelles offres en teletravail ?");

        double norme = Math.sqrt(ModeleDEmbeddings.similarite(vecteur, vecteur));

        assertThat(vecteur).hasSize(ModeleDEmbeddings.DIMENSIONS);
        assertThat(norme).isCloseTo(1.0, org.assertj.core.data.Offset.offset(1e-5));
    }

    @Test
    @DisplayName("un texte vide donne un vecteur nul, sans division par zero")
    void leTexteVideNeCassePas() {
        assertThat(ModeleDEmbeddings.vecteur("")).containsOnly(0f);
        assertThat(ModeleDEmbeddings.similarite(
                ModeleDEmbeddings.vecteur(""),
                ModeleDEmbeddings.vecteur("teletravail"))).isZero();
    }

    /**
     * ⚠️ Le défaut que le chapitre 3 montre, figé en test.
     *
     * <p>La question porte sur le télétravail ; le document le mieux classé
     * est celui qui annonce « Aucun télétravail ». Un sac de mots ne voit pas
     * la négation — et un vrai modèle d'embeddings place lui aussi « avec »
     * et « sans » côte à côte, parce qu'ils parlent du même sujet.
     */
    @Test
    @DisplayName("la recherche remonte le document le plus PROCHE, pas le plus PERTINENT")
    void leClassementSeTrompe() {
        var question = ModeleDEmbeddings.vecteur(
                "Quelles offres proposent du teletravail ?");

        String meilleur = Corpus.OFFRES.stream()
                .max(java.util.Comparator.comparingDouble(
                        d -> ModeleDEmbeddings.similarite(question,
                                ModeleDEmbeddings.vecteur(d.getText()))))
                .map(d -> String.valueOf(d.getMetadata().get("reference")))
                .orElseThrow();

        assertThat(meilleur).isEqualTo("OFF-033");
        assertThat(Corpus.OFFRES.stream()
                .filter(d -> "OFF-033".equals(d.getMetadata().get("reference")))
                .findFirst().orElseThrow().getText())
                .as("OFF-033 est justement l'offre SANS teletravail")
                .contains("Aucun teletravail");
    }

    @Test
    @DisplayName("`topK` borne ce que la base rend")
    void topKBorne() {
        var trouves = base().similaritySearch(SearchRequest.builder()
                .query("teletravail").topK(2).build());

        assertThat(trouves).hasSize(2);
        assertThat(trouves.getFirst().getScore())
                .isGreaterThanOrEqualTo(trouves.getLast().getScore());
    }

    @Test
    @DisplayName("l'advisor colle les documents trouves dans le prompt")
    void leContexteEstInjecte() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele)
                .defaultAdvisors(RetrievalAugmentationAdvisor.builder()
                        .documentRetriever(VectorStoreDocumentRetriever.builder()
                                .vectorStore(base()).topK(2)
                                .similarityThreshold(0.0).build())
                        .build())
                .build();
        String question = "Quelles offres proposent du teletravail ?";

        client.prompt().user(question).call().content();

        String envoye = modele.dernierTexte();
        assertThat(envoye)
                .contains("Context information is below")
                .contains("OFF-")
                .contains(question);
        assertThat(envoye.length())
                .as("le prompt part bien plus long que la question")
                .isGreaterThan(question.length() * 10);
    }

    /**
     * ⚠️ Le comportement silencieux du chapitre 3, section 6.
     *
     * <p>Quand aucun document ne passe le seuil, le
     * {@code ContextualQueryAugmenter} ne lève rien : il REMPLACE la question
     * par une consigne de refus poli. Un seuil mal réglé transforme donc un
     * RAG en assistant qui ne sait jamais rien, sans une ligne de journal.
     */
    @Test
    @DisplayName("sans document, la question est REMPLACEE, et rien n'est signale")
    void leContexteVideRemplaceLaQuestion() {
        var modele = new ModeleFactice();
        var client = ChatClient.builder(modele)
                .defaultAdvisors(RetrievalAugmentationAdvisor.builder()
                        .documentRetriever(VectorStoreDocumentRetriever.builder()
                                .vectorStore(base()).topK(2)
                                .similarityThreshold(0.9).build())
                        .build())
                .build();
        String question = "Quelles offres proposent du teletravail ?";

        String reponse = client.prompt().user(question).call().content();

        assertThat(modele.dernierTexte())
                .doesNotContain(question)
                .contains("outside your knowledge base");
        assertThat(reponse).isNotNull();
    }

    @Test
    @DisplayName("le decoupage change ce qu'on trouve")
    void leDecoupageCompte() {
        var question = ModeleDEmbeddings.vecteur(
                "Quelles offres proposent du teletravail ?");
        String tout = Corpus.OFFRES.stream()
                .map(org.springframework.ai.document.Document::getText)
                .reduce("", (a, b) -> a + " " + b);

        double entier = ModeleDEmbeddings.similarite(question,
                ModeleDEmbeddings.vecteur(tout));
        double meilleurMorceau = Corpus.OFFRES.stream()
                .mapToDouble(d -> ModeleDEmbeddings.similarite(question,
                        ModeleDEmbeddings.vecteur(d.getText())))
                .max().orElseThrow();

        assertThat(meilleurMorceau)
                .as("un gros document noie ses mots utiles dans les autres")
                .isGreaterThan(entier);
    }

    /**
     * La classe que le cours nomme n'existe plus en Spring AI 2.
     *
     * <p>Ce test échouera le jour où elle reviendra — et ce sera une bonne
     * nouvelle à traiter, pas une régression.
     */
    @Test
    @DisplayName("`QuestionAnswerAdvisor` a disparu au profit de la chaine RAG")
    void lAncienAdvisorNExistePlus() {
        assertThat(presente("org.springframework.ai.chat.client.advisor"
                + ".vectorstore.QuestionAnswerAdvisor")).isFalse();
        assertThat(presente("org.springframework.ai.rag.advisor"
                + ".RetrievalAugmentationAdvisor")).isTrue();
        assertThat(presente("org.springframework.ai.rag.retrieval.search"
                + ".VectorStoreDocumentRetriever")).isTrue();
    }

    private static boolean presente(String nom) {
        try {
            Class.forName(nom);
            return true;
        } catch (ClassNotFoundException absente) {
            return false;
        }
    }
}
