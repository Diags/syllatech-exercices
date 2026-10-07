package fr.portail.chapitres;

import dev.langchain4j.data.document.splitter.DocumentSplitters;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.rag.content.retriever.EmbeddingStoreContentRetriever;
import dev.langchain4j.rag.query.Query;
import dev.langchain4j.service.AiServices;
import dev.langchain4j.store.embedding.EmbeddingStore;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.rag.Corpus;
import fr.portail.rag.ModeleDEmbeddings;
import fr.portail.service.AssistantCarriere;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 3 — RAG : vos documents dans la conversation.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Rag
 * </pre>
 *
 * <p>« LangChain4j les injecte automatiquement dans le prompt avant l'appel
 * au modèle. » Ce chapitre montre <strong>le texte injecté</strong> : le
 * message que le modèle reçoit, contexte compris, avant et après.
 *
 * <p>Il mesure aussi ce que {@code DocumentSplitters.recursive(300, 30)}
 * fabrique réellement — combien de morceaux, de quelle taille, et si le
 * chevauchement existe vraiment.
 */
public final class Chapitre3Rag {

    private Chapitre3Rag() {
    }

    private static final String QUESTION =
            "Quelles offres proposent du teletravail ?";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var embeddings = banc.bean(EmbeddingModel.class);
            @SuppressWarnings("unchecked")
            var magasin = (EmbeddingStore<TextSegment>) banc.bean(EmbeddingStore.class);

            Console.titre(1, "CE QUE LE DECOUPAGE FABRIQUE VRAIMENT");
            var decoupeur = DocumentSplitters.recursive(Corpus.TAILLE,
                    Corpus.CHEVAUCHEMENT);
            var morceaux = new ArrayList<TextSegment>();
            for (var document : Corpus.OFFRES) {
                morceaux.addAll(decoupeur.split(document));
            }
            Console.ligne("documents indexes",
                    String.valueOf(Corpus.OFFRES.size()), 30);
            Console.ligne("caracteres au total",
                    String.valueOf(Corpus.OFFRES.stream()
                            .mapToInt(d -> d.text().length()).sum()), 30);
            Console.ligne("taille demandee",
                    Corpus.TAILLE + " caracteres", 30);
            Console.ligne("chevauchement demande",
                    Corpus.CHEVAUCHEMENT + " caracteres", 30);
            Console.ligne("morceaux obtenus",
                    String.valueOf(morceaux.size()), 30);
            Console.ligne("le plus long",
                    morceaux.stream().mapToInt(m -> m.text().length()).max()
                            .orElse(0) + " caracteres", 30);
            System.out.println();
            Console.sousTitre("Les deux premiers morceaux du premier document :");
            for (var morceau : morceaux.subList(0, Math.min(2, morceaux.size()))) {
                Console.texte("→ " + morceau.metadata().getString("reference")
                              + "  (" + morceau.text().length() + " caracteres)", 5);
                Console.bloc(morceau.text(), 9);
            }
            System.out.println();
            Console.sousTitre("Le chevauchement, mesure et non suppose :");
            var essais = new ArrayList<List<String>>();
            for (int demande : new int[] {0, Corpus.CHEVAUCHEMENT, 60, 120}) {
                var coupes = new ArrayList<TextSegment>();
                var essai = DocumentSplitters.recursive(Corpus.TAILLE, demande);
                for (var document : Corpus.OFFRES) {
                    coupes.addAll(essai.split(document));
                }
                essais.add(List.of(demande + " caracteres",
                        String.valueOf(coupes.size()),
                        chevauchement(coupes) + " caracteres"));
            }
            Console.tableau(List.of("chevauchement demande", "morceaux",
                    "chevauchement OBTENU"), essais, List.of(24, 12, 22));
            System.out.println();
            Console.texte("⚠️ Voila un chiffre que le cours ne donne pas. "
                    + "`recursive(300, 30)` — la ligne que tout le monde "
                    + "recopie — produit un chevauchement de ZERO sur de la "
                    + "vraie prose. La raison : LangChain4j remplit le "
                    + "chevauchement avec des PHRASES ENTIERES reprises du "
                    + "morceau precedent, et aucune phrase de ce corpus ne "
                    + "tient en 30 caracteres.");
            System.out.println();
            Console.texte("Le chevauchement n'est pourtant pas decoratif : "
                    + "sans lui, une idee a cheval sur deux morceaux devient "
                    + "deux moities, et aucune des deux ne remonte a la "
                    + "recherche. Il faut donc le dimensionner en fonction de "
                    + "vos phrases — et le MESURER, comme ici, plutot que de "
                    + "recopier un chiffre.");
            System.out.println();
            Console.texte("Et remarquez ce que chaque morceau garde : les "
                    + "METADONNEES du document d'origine. C'est ce qui permet "
                    + "de citer sa source — et de filtrer, en production, sur "
                    + "un client ou une langue.");

            Console.titre(2, "CE QUE L'INGESTION A COUTE");
            Console.ligne("textes vectorises a l'ingestion",
                    String.valueOf(ModeleDEmbeddings.textesVectorises()), 36);
            ModeleDEmbeddings.remettreAZero();
            var chercheur = EmbeddingStoreContentRetriever.builder()
                    .embeddingStore(magasin)
                    .embeddingModel(embeddings)
                    .maxResults(2)
                    .build();
            var trouves = chercheur.retrieve(Query.from(QUESTION));
            Console.ligne("textes vectorises pour UNE question",
                    String.valueOf(ModeleDEmbeddings.textesVectorises()), 38);
            Console.ligne("passages rendus", String.valueOf(trouves.size()), 36);
            System.out.println();
            for (var contenu : trouves) {
                Console.texte("→ " + contenu.textSegment().metadata()
                        .getString("reference"), 5);
                Console.bloc(contenu.textSegment().text(), 9);
            }
            System.out.println();
            Console.texte("L'ingestion vectorise tous les morceaux, une fois. "
                    + "Chaque question n'en vectorise qu'UN : la question "
                    + "elle-meme. C'est ce qui rend le RAG viable — le gros "
                    + "du calcul est fait d'avance, et la recherche ne "
                    + "compare que des vecteurs.");
            System.out.println();
            Console.texte("⚠️ En production, cela se paie quand meme deux "
                    + "fois : une facture d'embeddings a l'ingestion, "
                    + "proportionnelle a vos documents, et une par question. "
                    + "Reindexer un corpus entier n'est pas gratuit, et c'est "
                    + "pourquoi on ne change pas de modele d'embeddings a la "
                    + "legere.");

            Console.titre(3, "CE QUE LA RECHERCHE CLASSE, ET CE QU'ELLE RATE");
            var lignes = new ArrayList<List<String>>();
            for (var document : Corpus.OFFRES) {
                double score = ModeleDEmbeddings.similarite(
                        ModeleDEmbeddings.vecteur(QUESTION),
                        ModeleDEmbeddings.vecteur(document.text()));
                lignes.add(List.of(document.metadata().getString("reference"),
                        "%.4f".formatted(score), verite(document.text())));
            }
            lignes.sort((a, b) -> b.get(1).compareTo(a.get(1)));
            Console.tableau(List.of("document", "similarite", "verite terrain"),
                    lignes, List.of(14, 14, 26));
            System.out.println();
            Console.texte("Le classement est calcule, pas devine : c'est le "
                    + "produit scalaire de deux vecteurs normalises, soit le "
                    + "cosinus de l'angle entre eux.");
            System.out.println();
            Console.texte("Maintenant lisez la colonne de droite. Un document "
                    + "qui dit « Aucun teletravail » se classe parmi les "
                    + "premiers : il contient le mot, et une comparaison de "
                    + "vecteurs ne voit pas la negation devant. Un RAG remonte "
                    + "les passages les plus PROCHES, pas les plus PERTINENTS "
                    + "— et ce n'est pas un defaut de ce modele jouet : un "
                    + "vrai modele d'embeddings place lui aussi « avec » et "
                    + "« sans » cote a cote, parce qu'ils parlent du meme "
                    + "sujet.");

            Console.titre(4, "CE QUE LE RETRIEVER COLLE DANS LE PROMPT");
            var avecRag = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .contentRetriever(chercheur)
                    .build();
            modele.oublier();
            String avecContexte = avecRag.conseiller(QUESTION);
            String promptEnrichi = modele.dernierTexte();
            Console.sousTitre("Le prompt recu par le modele :");
            Console.bloc(promptEnrichi, 6);
            System.out.println();
            Console.ligne("votre question",
                    QUESTION.length() + " caracteres", 30);
            Console.ligne("ce qui est parti",
                    promptEnrichi.length() + " caracteres", 30);
            Console.ligne("rapport", "x" + (promptEnrichi.length()
                    / Math.max(1, QUESTION.length())), 30);
            System.out.println();
            Console.texte("Voila le RAG, en clair. Le retriever a cherche, "
                    + "trouve deux passages, et LangChain4j les a COLLES a la "
                    + "fin de votre message utilisateur, avec une consigne. Le "
                    + "modele ne « consulte » aucune base : il lit un message "
                    + "plus long.");
            System.out.println();
            Console.texte("⚠️ Et regardez OU c'est colle : dans le message "
                    + "UTILISATEUR, pas dans le message systeme. Consequence "
                    + "directe : si vous stockez la conversation en memoire, "
                    + "le contexte y entre aussi et repart au tour suivant. "
                    + "`storeRetrievedContentInChatMemory(false)` existe "
                    + "exactement pour cela.");

            Console.titre(5, "AVEC ET SANS");
            var sansRag = AiServices.create(AssistantCarriere.class, modele);
            modele.oublier();
            String sansContexte = sansRag.conseiller(QUESTION);
            Console.tableau(List.of("configuration", "reponse"), List.of(
                    List.of("sans RAG", court(sansContexte)),
                    List.of("avec RAG", court(avecContexte))),
                    List.of(18, 56));
            System.out.println();
            Console.texte("Le modele est le MEME. Ce qui change est ce qu'il a "
                    + "sous les yeux. C'est la definition du RAG : on ne "
                    + "reentraine rien, on enrichit le prompt.");
            System.out.println();
            Console.texte("⚠️ Une reponse « ancree » n'est pas une reponse "
                    + "vraie : elle est ancree dans les passages remontes. Si "
                    + "la recherche s'est trompee, le modele cite fidelement "
                    + "le mauvais passage. C'est pourquoi un RAG serieux se "
                    + "mesure d'abord sur sa RECHERCHE — rappel et precision "
                    + "des passages rendus — avant de se mesurer sur ses "
                    + "reponses.");

            Console.titre(6, "LE SEUIL QUI REND UN RAG MUET");
            var exigeant = EmbeddingStoreContentRetriever.builder()
                    .embeddingStore(magasin)
                    .embeddingModel(embeddings)
                    .maxResults(2)
                    .minScore(0.9)
                    .build();
            var rien = exigeant.retrieve(Query.from(QUESTION));
            var muet = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .contentRetriever(exigeant)
                    .build();
            modele.oublier();
            String reponseMuette = muet.conseiller(QUESTION);
            Console.ligne("minScore demande", "0.9", 30);
            Console.ligne("passages rendus", String.valueOf(rien.size()), 30);
            Console.ligne("prompt avec contexte",
                    promptEnrichi.length() + " caracteres", 30);
            Console.ligne("prompt sans contexte",
                    modele.dernierTexte().length() + " caracteres", 30);
            Console.ligne("erreur levee", "aucune", 30);
            Console.ligne("la reponse rendue", court(reponseMuette), 30);
            System.out.println();
            Console.texte("Aucun passage ne passe le seuil, et il ne se passe "
                    + "RIEN : pas d'exception, pas de journal. LangChain4j "
                    + "envoie simplement la question nue, et le modele repond "
                    + "de memoire — c'est-a-dire qu'il invente, ou qu'il "
                    + "avoue son ignorance.");
            System.out.println();
            Console.texte("⚠️ C'est le reglage le plus dangereux du RAG, "
                    + "parce qu'il echoue en silence. Un `minScore` mal "
                    + "choisi transforme un assistant documente en assistant "
                    + "ordinaire, et rien ne le signale. En production, on "
                    + "compte les recherches vides.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Les outils : le schema d'arguments que LangChain4j "
                    + "deduit d'une methode `@Tool`, et un aller-retour "
                    + "complet ou le modele demande, obtient, et repond.");
            System.out.println();
        }
    }

    /**
     * Le nombre de caractères communs entre la fin d'un morceau et le début
     * du suivant — le chevauchement, mesuré plutôt qu'affirmé.
     */
    private static int chevauchement(List<TextSegment> morceaux) {
        int maximum = 0;
        for (int i = 0; i + 1 < morceaux.size(); i++) {
            String avant = morceaux.get(i).text();
            String apres = morceaux.get(i + 1).text();
            if (!avant.isEmpty() && !apres.isEmpty()
                    && morceaux.get(i).metadata().getString("reference")
                            .equals(morceaux.get(i + 1).metadata()
                                    .getString("reference"))) {
                for (int taille = Math.min(avant.length(), apres.length());
                        taille > 0; taille--) {
                    if (avant.endsWith(apres.substring(0, taille))) {
                        maximum = Math.max(maximum, taille);
                        break;
                    }
                }
            }
        }
        return maximum;
    }

    /** L'offre propose-t-elle vraiment du télétravail ? Le mot ne suffit pas. */
    private static String verite(String texte) {
        String bas = texte.toLowerCase(java.util.Locale.ROOT);
        if (bas.contains("aucun teletravail")) {
            return "dit NON au teletravail";
        }
        return bas.contains("teletravail") ? "en propose vraiment"
                : "hors sujet";
    }

    private static String court(String texte) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 54 ? plat : plat.substring(0, 51) + "...";
    }
}
