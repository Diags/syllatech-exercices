package fr.portail.rag;

import dev.langchain4j.data.document.Document;
import dev.langchain4j.data.document.Metadata;
import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.store.embedding.EmbeddingStore;
import dev.langchain4j.store.embedding.EmbeddingStoreIngestor;
import dev.langchain4j.store.embedding.inmemory.InMemoryEmbeddingStore;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Les documents du portail, et le magasin vectoriel qui les indexe.
 *
 * <p>{@link InMemoryEmbeddingStore} est celui de LangChain4j : la même
 * interface {@code EmbeddingStore} qu'un pgvector, la même recherche par
 * similarité, les mêmes {@code TextSegment}. Ce qui change en production est
 * l'implémentation derrière — et c'est tout l'intérêt de l'abstraction que le
 * chapitre 3 décrit.
 *
 * <p>⚠️ Ce qu'un magasin en mémoire ne fait pas : il compare la question à
 * <strong>tous</strong> les segments, un par un. Sur quatre offres c'est
 * instantané ; sur dix millions, c'est la raison d'être d'un index approximatif
 * (HNSW, IVFFlat) — et la raison pour laquelle pgvector existe.
 *
 * <p>Les quatre documents sont volontairement <em>longs</em> : le chapitre 3
 * mesure ce que {@code DocumentSplitters.recursive(300, 30)} en fait, et un
 * document de deux lignes ne se découpe pas.
 */
@Configuration
public class Corpus {

    /** La taille de morceau du cours : 300 caractères, 30 de chevauchement. */
    public static final int TAILLE = 300;
    public static final int CHEVAUCHEMENT = 30;

    /** Les offres publiées, telles qu'un RAG les indexerait. */
    public static final List<Document> OFFRES = List.of(
            document("OFF-014", """
                    OFF-014 — Developpeuse Java senior, Lyon. Salaire 52000 a
                    58000 euros bruts annuels. Teletravail deux jours par
                    semaine, les mardis et jeudis. Stack Java 25, Spring Boot,
                    PostgreSQL, un peu de Kafka. Cinq ans d'experience
                    demandes, dont deux sur des applications en production.
                    L'equipe compte huit personnes et pratique la revue de
                    code systematique. Le processus comprend un entretien
                    technique d'une heure, puis un echange avec l'equipe. Les
                    candidatures sans lettre de motivation sont acceptees.
                    """, "Lyon", 52_000),
            document("OFF-021", """
                    OFF-021 — Ingenieure SRE, Toulouse. Salaire 58000 a 64000
                    euros bruts annuels. Teletravail integral possible, avec
                    deux rassemblements par an. Kubernetes, Terraform,
                    Prometheus, astreintes une semaine sur six, compensees.
                    L'equipe gere une plateforme de quarante services et une
                    base de donnees de trois teraoctets. On cherche quelqu'un
                    capable d'ecrire du Go ou du Python, et surtout de tenir
                    un post-mortem sans chercher de coupable.
                    """, "Toulouse", 58_000),
            document("OFF-033", """
                    OFF-033 — Analyste donnees, Paris. Salaire 44000 a 47000
                    euros bruts annuels. Aucun teletravail : l'equipe
                    travaille sur site, dans des locaux du onzieme
                    arrondissement. SQL, Python, un peu de dbt, et beaucoup de
                    discussions avec les equipes metier. Le poste convient a
                    quelqu'un qui aime expliquer un chiffre autant que le
                    calculer. Trois ans d'experience suffisent.
                    """, "Paris", 44_000),
            document("PROC-01", """
                    Procedure de candidature du portail. Toute candidature
                    recoit une reponse sous dix jours ouvres, y compris un
                    refus. Un entretien technique d'une heure precede
                    l'entretien avec l'equipe. Le portail ne conserve aucun CV
                    au-dela de six mois, conformement a sa politique de
                    donnees. Les candidatures spontanees sont examinees une
                    fois par mois. Aucun test technique a domicile n'est
                    demande : nous considerons que le temps des candidats
                    vaut le notre.
                    """, "toutes", 0));

    private static Document document(String reference, String texte,
                                     String ville, int salaire) {
        return Document.from(texte.replaceAll("\\s+", " ").strip(),
                Metadata.from(java.util.Map.of("reference", reference,
                        "ville", ville, "salaire", String.valueOf(salaire))));
    }

    /**
     * L'ingestion : découper, vectoriser, ranger — une seule fois.
     *
     * <p>C'est exactement le pipeline du cours. Ce que le chapitre 3 y
     * mesure : combien de morceaux quatre documents produisent, et que le
     * chevauchement existe vraiment — la fin d'un morceau se retrouve au
     * début du suivant.
     */
    @Bean
    EmbeddingStore<TextSegment> magasin(EmbeddingModel embeddings) {
        var magasin = new InMemoryEmbeddingStore<TextSegment>();
        // >>> depart: ingerer les documents — decouper en morceaux de 300 avec 30 de chevauchement, puis vectoriser et ranger
        //     // un magasin vide ne leve aucune erreur : il ne trouve rien
        EmbeddingStoreIngestor.builder()
                .documentSplitter(DocumentSplitters.recursive(TAILLE, CHEVAUCHEMENT))
                .embeddingModel(embeddings)
                .embeddingStore(magasin)
                .build()
                .ingest(OFFRES);
        // <<<
        return magasin;
    }
}
