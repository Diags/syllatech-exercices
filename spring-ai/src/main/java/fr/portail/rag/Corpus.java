package fr.portail.rag;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.vectorstore.SimpleVectorStore;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Les documents du portail, et la base vectorielle qui les indexe.
 *
 * <p>{@link SimpleVectorStore} est celui de Spring AI : la même interface
 * {@code VectorStore} qu'un pgvector, la même recherche par similarité, les
 * mêmes {@code Document}. Ce qui change en production est l'implémentation
 * derrière — et c'est tout l'intérêt de l'abstraction que le chapitre 3
 * décrit.
 *
 * <p>⚠️ Ce qu'un {@code SimpleVectorStore} ne fait pas : il compare la
 * question à <strong>tous</strong> les documents, un par un. Sur dix offres
 * c'est instantané ; sur dix millions, c'est la raison d'être d'un index
 * approximatif (HNSW, IVFFlat) — et la raison pour laquelle pgvector existe.
 */
@Configuration
public class Corpus {

    /** Les offres publiées, telles qu'un RAG les indexerait. */
    public static final List<Document> OFFRES = List.of(
            document("OFF-014", """
                    OFF-014 — Developpeuse Java senior, Lyon. Salaire 52000 a
                    58000 euros. Teletravail deux jours par semaine. Stack
                    Java 25, Spring Boot, PostgreSQL. Cinq ans d'experience
                    demandes.""", "Lyon", 52_000),
            document("OFF-021", """
                    OFF-021 — Ingenieure SRE, Toulouse. Salaire 58000 a 64000
                    euros. Teletravail integral possible. Kubernetes,
                    Terraform, astreintes une semaine sur six.""",
                    "Toulouse", 58_000),
            document("OFF-033", """
                    OFF-033 — Analyste donnees, Paris. Salaire 44000 a 47000
                    euros. Aucun teletravail : l'equipe travaille sur site.
                    SQL, Python, un peu de dbt.""", "Paris", 44_000),
            document("OFF-047", """
                    OFF-047 — Developpeur mobile, Nantes. Salaire 46000 a
                    51000 euros. Teletravail trois jours par semaine. Kotlin,
                    Swift, un cycle de publication toutes les deux semaines.""",
                    "Nantes", 46_000),
            document("PROC-01", """
                    Procedure de candidature : toute candidature recoit une
                    reponse sous dix jours ouvres. Un entretien technique
                    d'une heure precede l'entretien avec l'equipe. Le
                    portail ne conserve aucun CV au-dela de six mois.""",
                    "toutes", 0));

    private static Document document(String reference, String texte,
                                     String ville, int salaire) {
        return new Document(texte.replace("\n", " ").replaceAll("\\s+", " "),
                Map.of("reference", reference, "ville", ville,
                        "salaire", salaire));
    }

    @Bean
    VectorStore baseVectorielle(EmbeddingModel embeddings) {
        var base = SimpleVectorStore.builder(embeddings).build();
        // >>> depart: indexer les documents du corpus dans la base vectorielle
        //     // une base vide ne leve aucune erreur : elle ne trouve rien
        base.add(new ArrayList<>(OFFRES));
        // <<<
        return base;
    }
}
