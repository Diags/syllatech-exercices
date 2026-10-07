package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.rag.Corpus;
import fr.portail.rag.ModeleDEmbeddings;
import java.util.List;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.rag.advisor.RetrievalAugmentationAdvisor;
import org.springframework.ai.rag.retrieval.search.VectorStoreDocumentRetriever;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;

/**
 * Chapitre 3 — RAG : embeddings et bases vectorielles.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rag
 * </pre>
 *
 * <p>« Le {@code QuestionAnswerAdvisor} injecte automatiquement le contexte
 * trouvé. » Ce chapitre montre <strong>le texte injecté</strong> : le prompt
 * que le modèle reçoit, contexte compris, avant et après.
 *
 * <p>⚠️ Et il commence par constater que cette classe <strong>n'existe
 * plus</strong> en Spring AI 2.0 : la section 4 la cherche dans le classpath
 * et imprime le résultat. Ce n'est pas un détail de nommage — l'API du RAG a
 * été refondue, et tout le code que vous trouverez en ligne date d'avant.
 *
 * <p>Il mesure aussi ce qu'une recherche par similarité classe, et pourquoi
 * elle se trompe parfois — parce que le classement se lit, et qu'un RAG qui
 * remonte le mauvais document répond faux avec assurance.
 */
public final class Chapitre3Rag {

    private Chapitre3Rag() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var base = banc.bean(VectorStore.class);
            var embeddings = banc.bean(EmbeddingModel.class);

            Console.titre(1, "UN TEXTE DEVIENT UN VECTEUR");
            String question = "Quelles offres proposent du teletravail ?";
            var vecteur = embeddings.embed(question);
            Console.ligne("la question", question, 24);
            Console.ligne("dimensions", String.valueOf(vecteur.length), 24);
            Console.ligne("cases non nulles",
                    String.valueOf(java.util.stream.IntStream
                            .range(0, vecteur.length)
                            .filter(i -> vecteur[i] != 0).count()), 24);
            Console.ligne("norme du vecteur",
                    "%.4f".formatted(Math.sqrt(produit(vecteur, vecteur))), 24);
            System.out.println();
            Console.texte("Un vecteur normalise : sa longueur vaut 1. C'est ce "
                    + "qui permet de comparer un texte court a un texte long "
                    + "sans que la longueur decide du resultat.");
            System.out.println();
            Console.texte("⚠️ Le modele d'embeddings de ce projet est un sac "
                    + "de mots : il pose chaque mot dans une case, et ne "
                    + "rapprochera JAMAIS « salaire » de « remuneration ». Un "
                    + "vrai modele le ferait — c'est exactement ce qu'on "
                    + "achete en payant des embeddings, et ce que ce projet "
                    + "ne peut pas simuler.");

            Console.titre(2, "CE QUE LA RECHERCHE CLASSE");
            var lignes = new java.util.ArrayList<List<String>>();
            for (var document : Corpus.OFFRES) {
                double score = ModeleDEmbeddings.similarite(
                        ModeleDEmbeddings.vecteur(question),
                        ModeleDEmbeddings.vecteur(document.getText()));
                lignes.add(List.of(
                        String.valueOf(document.getMetadata().get("reference")),
                        "%.4f".formatted(score),
                        verite(document.getText())));
            }
            lignes.sort((a, b) -> b.get(1).compareTo(a.get(1)));
            Console.tableau(List.of("document", "similarite", "verite terrain"),
                    lignes, List.of(14, 14, 26));
            System.out.println();
            Console.texte("Le classement est calcule, pas devine : c'est le "
                    + "produit scalaire de deux vecteurs normalises, soit le "
                    + "cosinus de l'angle entre eux. Plus c'est proche de 1, "
                    + "plus les deux textes partagent de mots.");
            System.out.println();
            Console.texte("Maintenant lisez la colonne de droite. Le document "
                    + "le MIEUX classe est celui qui dit « Aucun "
                    + "teletravail ». Il gagne parce qu'il contient le mot, et "
                    + "un sac de mots ne voit pas la negation devant.");
            System.out.println();
            Console.texte("C'est la faille du procede, et elle ne vient pas "
                    + "de ce modele jouet : un vrai modele d'embeddings place "
                    + "lui aussi « avec teletravail » et « sans teletravail » "
                    + "cote a cote, parce qu'ils parlent du meme sujet. Un RAG "
                    + "remonte les documents les plus PROCHES, pas les plus "
                    + "PERTINENTS.");
            System.out.println();
            Console.texte("Et la suite du chapitre montre le degat : ce "
                    + "document ira dans le prompt, et le modele repondra "
                    + "faux avec assurance, en citant sa source.");

            Console.titre(3, "CE QUE LA BASE VECTORIELLE REND");
            var trouves = base.similaritySearch(SearchRequest.builder()
                    .query(question).topK(2).build());
            Console.ligne("documents indexes", String.valueOf(Corpus.OFFRES.size()), 26);
            Console.ligne("topK demande", "2", 26);
            Console.ligne("documents rendus", String.valueOf(trouves.size()), 26);
            System.out.println();
            for (var document : trouves) {
                Console.texte("→ " + document.getMetadata().get("reference")
                        + "  (score " + "%.4f".formatted(
                                document.getScore() == null ? 0.0
                                        : document.getScore()) + ")", 5);
                Console.bloc(document.getText(), 9);
            }
            System.out.println();
            Console.texte("`topK` est la decision la plus lourde du RAG. Trop "
                    + "petit, le bon document reste dehors ; trop grand, le "
                    + "prompt se remplit de bruit — et chaque document de "
                    + "trop est facture a chaque question.");

            Console.titre(4, "LA CLASSE DU COURS N'EXISTE PLUS");
            Console.ligne("QuestionAnswerAdvisor (Spring AI 1.x)",
                    presente("org.springframework.ai.chat.client.advisor"
                            + ".vectorstore.QuestionAnswerAdvisor"), 42);
            Console.ligne("RetrievalAugmentationAdvisor (2.x)",
                    presente("org.springframework.ai.rag.advisor"
                            + ".RetrievalAugmentationAdvisor"), 42);
            Console.ligne("VectorStoreDocumentRetriever (2.x)",
                    presente("org.springframework.ai.rag.retrieval.search"
                            + ".VectorStoreDocumentRetriever"), 42);
            System.out.println();
            Console.texte("Ce n'est pas une classe renommee : c'est l'API du "
                    + "RAG qui a ete refondue. En 1.x, un advisor faisait "
                    + "tout — chercher, formater, coller. En 2.x, chaque "
                    + "etape est un objet remplacable : un `DocumentRetriever` "
                    + "cherche, un `DocumentJoiner` fusionne, un "
                    + "`QueryAugmenter` colle, et le "
                    + "`RetrievalAugmentationAdvisor` les enchaine.");
            System.out.println();
            Console.texte("⚠️ Consequence pratique : tout l'exemple de RAG que "
                    + "vous trouverez en ligne ne compile pas avec Spring AI "
                    + "2. Cherchez `RetrievalAugmentationAdvisor`, pas "
                    + "`QuestionAnswerAdvisor` — et defiez-vous d'un tutoriel "
                    + "qui ne dit pas sa version.");

            Console.titre(5, "CE QUE L'ADVISOR COLLE DANS LE PROMPT");
            var avecRag = ChatClient.builder(modele)
                    .defaultAdvisors(RetrievalAugmentationAdvisor.builder()
                            .documentRetriever(VectorStoreDocumentRetriever
                                    .builder()
                                    .vectorStore(base)
                                    .topK(2)
                                    // ⚠️ Un seuil, pas « aucun seuil ». Le
                                    // modele d'embeddings de ce projet rend
                                    // des scores bas ; un seuil trop haut
                                    // rendrait zero document, SANS erreur —
                                    // la section suivante le mesure.
                                    .similarityThreshold(0.0)
                                    .build())
                            .build())
                    .build();
            modele.oublier();
            String avecContexte = avecRag.prompt().user(question).call().content();
            String promptEnrichi = modele.dernierTexte();
            Console.sousTitre("Le prompt recu par le modele :");
            Console.bloc(promptEnrichi, 6);
            System.out.println();
            Console.ligne("votre question", question.length() + " caracteres", 30);
            Console.ligne("ce qui est parti",
                    promptEnrichi.length() + " caracteres", 30);
            Console.ligne("rapport", "x" + (promptEnrichi.length()
                    / Math.max(1, question.length())), 30);
            System.out.println();
            Console.texte("Voila le RAG, en clair. L'advisor a cherche, "
                    + "trouve deux documents, et les a COLLES dans votre "
                    + "message avec une consigne. Le modele ne « consulte » "
                    + "aucune base : il lit un prompt plus long.");
            System.out.println();
            Console.texte("C'est pourquoi le RAG coute cher : chaque question "
                    + "facture les documents remontes. Et c'est pourquoi le "
                    + "decoupage compte — un document de dix pages colle en "
                    + "entier, c'est dix pages facturees pour trois lignes "
                    + "utiles.");

            Console.titre(6, "QUAND LA RECHERCHE NE TROUVE RIEN");
            var tropExigeant = ChatClient.builder(modele)
                    .defaultAdvisors(RetrievalAugmentationAdvisor.builder()
                            .documentRetriever(VectorStoreDocumentRetriever
                                    .builder()
                                    .vectorStore(base)
                                    .topK(2)
                                    // Un seuil que le meilleur document de ce
                                    // corpus n'atteint pas (section 2).
                                    .similarityThreshold(0.9)
                                    .build())
                            .build())
                    .build();
            modele.oublier();
            String reponseVide = tropExigeant.prompt().user(question)
                    .call().content();
            String promptVide = modele.dernierTexte();
            Console.sousTitre("Le prompt recu quand aucun document ne passe :");
            Console.bloc(promptVide, 6);
            System.out.println();
            Console.ligne("prompt avec contexte",
                    promptEnrichi.length() + " caracteres", 30);
            Console.ligne("prompt sans contexte",
                    promptVide.length() + " caracteres", 30);
            Console.ligne("la question est-elle encore la ?",
                    promptVide.contains(question) ? "oui" : "NON", 34);
            Console.ligne("erreur levee", "aucune", 30);
            System.out.println();
            Console.texte("Regardez ce qui est parti : ce n'est plus votre "
                    + "question. Le `ContextualQueryAugmenter` la REMPLACE par "
                    + "une consigne — dire poliment que le sujet est hors "
                    + "base. C'est un choix par defaut de Spring AI, et il est "
                    + "defendable : mieux vaut un refus qu'une reponse "
                    + "inventee.");
            System.out.println();
            Console.texte("⚠️ Mais il est SILENCIEUX. Aucune exception, aucun "
                    + "journal : un seuil de similarite mal regle transforme "
                    + "un RAG en assistant qui ne sait jamais rien, et la "
                    + "seule facon de s'en apercevoir est de lire le prompt — "
                    + "exactement ce que fait cette section. En production, on "
                    + "compte les recherches vides.");
            System.out.println();
            Console.ligne("la reponse rendue", court(reponseVide), 30);

            Console.titre(7, "AVEC ET SANS");
            var sansRag = ChatClient.builder(modele).build();
            modele.oublier();
            String sansContexte = sansRag.prompt().user(question).call().content();
            Console.tableau(List.of("configuration", "reponse"), List.of(
                    List.of("sans RAG", court(sansContexte)),
                    List.of("avec RAG", court(avecContexte))),
                    List.of(18, 56));
            System.out.println();
            Console.texte("Le modele est le MEME. Ce qui change est ce qu'il a "
                    + "sous les yeux. C'est la definition du RAG : on ne "
                    + "reentraine rien, on enrichit le prompt.");
            System.out.println();
            Console.texte("⚠️ Et la limite du procede est sur cette ligne : "
                    + "la reponse « avec RAG » cite OFF-033, l'offre qui "
                    + "annonce AUCUN teletravail. La recherche l'avait classee "
                    + "premiere (section 2), l'advisor l'a collee dans le "
                    + "prompt (section 5), le modele l'a citee. Personne n'a "
                    + "menti ; la chaine a fonctionne exactement comme prevu.");
            System.out.println();
            Console.texte("Une reponse « ancree » n'est donc pas une reponse "
                    + "vraie : elle est ancree dans les documents remontes. "
                    + "C'est pourquoi un RAG serieux se mesure sur sa "
                    + "RECHERCHE — rappel et precision des documents rendus — "
                    + "avant de se mesurer sur ses reponses. Le chapitre 6 y "
                    + "revient.");

            Console.titre(8, "LE DECOUPAGE CHANGE CE QU'ON TROUVE");
            var entier = new Document(Corpus.OFFRES.stream()
                    .map(Document::getText)
                    .reduce("", (a, b) -> a + " " + b));
            double scoreEntier = ModeleDEmbeddings.similarite(
                    ModeleDEmbeddings.vecteur(question),
                    ModeleDEmbeddings.vecteur(entier.getText()));
            double scoreMeilleurMorceau = Corpus.OFFRES.stream()
                    .mapToDouble(d -> ModeleDEmbeddings.similarite(
                            ModeleDEmbeddings.vecteur(question),
                            ModeleDEmbeddings.vecteur(d.getText())))
                    .max().orElse(0);
            Console.tableau(List.of("ce qu'on indexe", "caracteres",
                    "meilleure similarite"), List.of(
                    List.of("un seul gros document",
                            String.valueOf(entier.getText().length()),
                            "%.4f".formatted(scoreEntier)),
                    List.of("cinq documents decoupes",
                            String.valueOf(Corpus.OFFRES.stream()
                                    .mapToInt(d -> d.getText().length()).max().orElse(0))
                            + " au plus",
                            "%.4f".formatted(scoreMeilleurMorceau))),
                    List.of(26, 16, 22));
            System.out.println();
            Console.texte("Le gros document contient TOUTES les bonnes "
                    + "reponses, et il est moins bien classe que le meilleur "
                    + "morceau : ses mots utiles sont noyes dans les autres. "
                    + "C'est ce que le cours appelle le chunking, et c'est la "
                    + "raison pour laquelle on decoupe avant d'indexer.");

            Console.titre(9, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le schema JSON que Spring AI deduit d'une methode "
                    + "annotee `@Tool`, et un aller-retour complet ou le "
                    + "modele demande un outil, l'obtient, et repond.");
            System.out.println();
        }
    }

    /**
     * L'offre propose-t-elle vraiment du télétravail ?
     *
     * <p>Chercher le mot ne suffit pas : OFF-033 écrit « Aucun
     * télétravail ». Cette colonne est la <em>vérité terrain</em> du
     * chapitre — ce qu'un humain répondrait — et c'est ce qui rend le
     * classement de la section 2 lisible comme une erreur, et non comme un
     * résultat.
     */
    private static String verite(String texte) {
        String bas = texte.toLowerCase(java.util.Locale.ROOT);
        if (bas.contains("aucun teletravail")) {
            return "dit NON au teletravail";
        }
        return bas.contains("teletravail") ? "en propose vraiment"
                : "hors sujet";
    }

    /**
     * La classe est-elle dans le classpath ? Demandé à la JVM, pas affirmé.
     *
     * <p>Un cours peut se tromper de version ; le classpath, non. C'est la
     * seule façon honnête d'écrire « cette classe n'existe plus » : la
     * chercher devant l'étudiant.
     */
    private static String presente(String nom) {
        try {
            Class.forName(nom);
            return "presente";
        } catch (ClassNotFoundException absente) {
            return "ABSENTE du classpath";
        }
    }

    private static double produit(float[] premier, float[] second) {
        double total = 0;
        for (int i = 0; i < premier.length; i++) {
            total += premier[i] * second[i];
        }
        return total;
    }

    private static String court(String texte) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 54 ? plat : plat.substring(0, 51) + "...";
    }
}
