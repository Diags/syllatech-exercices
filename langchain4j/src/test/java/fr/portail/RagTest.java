package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.rag.content.retriever.EmbeddingStoreContentRetriever;
import dev.langchain4j.rag.query.Query;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import fr.portail.modele.ModeleFactice;
import fr.portail.rag.Corpus;
import fr.portail.rag.ModeleDEmbeddings;
import fr.portail.service.AssistantCarriere;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Le RAG, sans lire l'écran.
 *
 * <p>Ces tests ne démarrent pas d'application : ils construisent le magasin à
 * la main. C'est à la fois plus rapide et plus honnête — ce qui est vérifié
 * ici est le comportement de LangChain4j, pas celui du câblage Spring.
 */
class RagTest {

    private static final String QUESTION =
            "Quelles offres proposent du teletravail ?";

    private static EmbeddingStore<TextSegment> magasin(ModeleDEmbeddings embeddings) {
        var magasin = new InMemoryEmbeddingStore<TextSegment>();
        EmbeddingStoreIngestor.builder()
                .documentSplitter(DocumentSplitters.recursive(Corpus.TAILLE,
                        Corpus.CHEVAUCHEMENT))
                .embeddingModel(embeddings)
                .embeddingStore(magasin)
                .build()
                .ingest(Corpus.OFFRES);
        return magasin;
    }

    @Test
    @DisplayName("un vecteur d'embeddings est normalise")
    void leVecteurEstNormalise() {
        var vecteur = ModeleDEmbeddings.vecteur(QUESTION);

        double norme = Math.sqrt(ModeleDEmbeddings.similarite(vecteur, vecteur));

        assertThat(vecteur).hasSize(ModeleDEmbeddings.DIMENSIONS);
        assertThat(norme).isCloseTo(1.0, org.assertj.core.data.Offset.offset(1e-5));
    }

    @Test
    @DisplayName("un texte vide donne un vecteur nul, sans division par zero")
    void leTexteVideNeCassePas() {
        assertThat(ModeleDEmbeddings.vecteur("")).containsOnly(0f);
        assertThat(ModeleDEmbeddings.similarite(ModeleDEmbeddings.vecteur(""),
                ModeleDEmbeddings.vecteur("teletravail"))).isZero();
    }

    /**
     * ⚠️ La découverte du chapitre 3, figée en test.
     *
     * <p>{@code recursive(300, 30)} — la ligne que tout le monde recopie —
     * produit un chevauchement de ZÉRO sur de la vraie prose : LangChain4j
     * remplit le chevauchement avec des phrases entières, et aucune phrase de
     * ce corpus ne tient en 30 caractères.
     */
    @Test
    @DisplayName("un chevauchement de 30 caracteres ne chevauche rien")
    void leChevauchementDemandeNEstPasLeChevauchementObtenu() {
        assertThat(chevauchement(decouper(300, 30)))
                .as("30 caracteres ne contiennent aucune phrase entiere")
                .isZero();
        assertThat(chevauchement(decouper(300, 120)))
                .as("120 caracteres en contiennent une")
                .isPositive();
    }

    @Test
    @DisplayName("chaque morceau garde les metadonnees de son document")
    void lesMetadonneesSurvivent() {
        var morceaux = decouper(300, 30);

        assertThat(morceaux).isNotEmpty();
        assertThat(morceaux).allSatisfy(morceau ->
                assertThat(morceau.metadata().getString("reference"))
                        .isNotBlank());
    }

    @Test
    @DisplayName("l'ingestion vectorise tout une fois, la question une seule fois")
    void leCoutDeLIngestion() {
        var embeddings = new ModeleDEmbeddings();
        ModeleDEmbeddings.remettreAZero();
        var magasin = magasin(embeddings);
        int aLIngestion = ModeleDEmbeddings.textesVectorises();

        ModeleDEmbeddings.remettreAZero();
        EmbeddingStoreContentRetriever.builder()
                .embeddingStore(magasin).embeddingModel(embeddings)
                .maxResults(2).build()
                .retrieve(Query.from(QUESTION));

        assertThat(aLIngestion).isGreaterThan(1);
        assertThat(ModeleDEmbeddings.textesVectorises())
                .as("une question ne vectorise QUE la question")
                .isEqualTo(1);
    }

    @Test
    @DisplayName("la recherche remonte le passage le plus PROCHE, pas le plus PERTINENT")
    void leClassementSeTrompe() {
        var question = ModeleDEmbeddings.vecteur(QUESTION);

        String meilleur = Corpus.OFFRES.stream()
                .max(java.util.Comparator.comparingDouble(
                        d -> ModeleDEmbeddings.similarite(question,
                                ModeleDEmbeddings.vecteur(d.text()))))
                .map(d -> d.metadata().getString("reference"))
                .orElseThrow();

        assertThat(meilleur).isEqualTo("OFF-033");
        assertThat(Corpus.OFFRES.stream()
                .filter(d -> "OFF-033".equals(d.metadata().getString("reference")))
                .findFirst().orElseThrow().text())
                .as("OFF-033 est justement l'offre SANS teletravail")
                .contains("Aucun teletravail");
    }

    @Test
    @DisplayName("le retriever colle les passages dans le message utilisateur")
    void leContexteEstInjecte() {
        var embeddings = new ModeleDEmbeddings();
        var modele = new ModeleFactice();
        var assistant = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .contentRetriever(EmbeddingStoreContentRetriever.builder()
                        .embeddingStore(magasin(embeddings))
                        .embeddingModel(embeddings)
                        .maxResults(2).build())
                .build();

        assistant.conseiller(QUESTION);

        String envoye = modele.dernierTexte();
        assertThat(envoye)
                .contains("Answer using the following information")
                .contains("OFF-")
                .contains(QUESTION);
        assertThat(envoye.length()).isGreaterThan(QUESTION.length() * 10);
    }

    /**
     * ⚠️ Le comportement silencieux du chapitre 3.
     *
     * <p>Quand aucun passage ne franchit {@code minScore}, il ne se passe
     * rien : la question part nue, sans exception et sans journal.
     */
    @Test
    @DisplayName("un minScore trop haut rend le RAG muet, sans rien signaler")
    void leSeuilRendMuet() {
        var embeddings = new ModeleDEmbeddings();
        var modele = new ModeleFactice();
        var assistant = AiServices.builder(AssistantCarriere.class)
                .chatModel(modele)
                .contentRetriever(EmbeddingStoreContentRetriever.builder()
                        .embeddingStore(magasin(embeddings))
                        .embeddingModel(embeddings)
                        .maxResults(2).minScore(0.9).build())
                .build();

        String reponse = assistant.conseiller(QUESTION);

        assertThat(reponse).isNotNull();
        assertThat(modele.dernierTexte())
                .doesNotContain("Answer using the following information")
                .contains(QUESTION);
    }

    private static List<TextSegment> decouper(int taille, int chevauchement) {
        var decoupeur = DocumentSplitters.recursive(taille, chevauchement);
        var morceaux = new ArrayList<TextSegment>();
        for (var document : Corpus.OFFRES) {
            morceaux.addAll(decoupeur.split(document));
        }
        return morceaux;
    }

    /** Le plus grand nombre de caractères communs entre deux morceaux voisins. */
    private static int chevauchement(List<TextSegment> morceaux) {
        int maximum = 0;
        for (int i = 0; i + 1 < morceaux.size(); i++) {
            var avant = morceaux.get(i);
            var apres = morceaux.get(i + 1);
            if (!avant.metadata().getString("reference")
                    .equals(apres.metadata().getString("reference"))) {
                continue;
            }
            for (int taille = Math.min(avant.text().length(),
                    apres.text().length()); taille > 0; taille--) {
                if (avant.text().endsWith(apres.text().substring(0, taille))) {
                    maximum = Math.max(maximum, taille);
                    break;
                }
            }
        }
        return maximum;
    }
}
