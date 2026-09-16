package fr.portail.rag;

import dev.langchain4j.data.embedding.Embedding;
import dev.langchain4j.data.segment.TextSegment;
import dev.langchain4j.model.embedding.EmbeddingModel;
import dev.langchain4j.model.output.Response;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;

/**
 * Le modèle d'embeddings du portail — déterministe, et sans réseau.
 *
 * <p>Un vrai modèle d'embeddings apprend une géométrie du sens : « poste » et
 * « emploi » finissent proches. Celui-ci n'apprend rien. Il pose chaque
 * <strong>mot</strong> dans une case, par un hachage, et compte. C'est un sac
 * de mots, et c'est une approximation grossière.
 *
 * <p>⚠️ <strong>Ce que cela change pour le chapitre 3, et ce que cela ne
 * change pas.</strong> Ce qui est mesuré reste vrai : le découpage en
 * morceaux, la similarité cosinus, le classement des passages, le fait que le
 * contexte trouvé finisse dans le prompt. Ce qui n'est PAS mesuré, c'est la
 * qualité sémantique : ce modèle ne rapprochera jamais « salaire » de
 * « rémunération ». Un vrai modèle le ferait, et c'est exactement ce qu'on
 * achète en payant des embeddings.
 *
 * <p>⚠️ <strong>Il compte ses appels.</strong> Le chapitre 3 s'en sert pour
 * montrer ce que l'ingestion coûte une fois pour toutes, et ce que chaque
 * question coûte ensuite — une vectorisation par question, pas une par
 * document.
 */
@Component
public class ModeleDEmbeddings implements EmbeddingModel {

    public static final int DIMENSIONS = 256;

    private static final AtomicInteger TEXTES = new AtomicInteger();

    /** Les mots trop courants pour porter du sens. */
    private static final java.util.Set<String> VIDES = java.util.Set.of(
            "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou",
            "a", "au", "aux", "en", "est", "sont", "pour", "par", "dans",
            "sur", "ce", "cette", "que", "qui", "quoi", "avec", "sans");

    public static int textesVectorises() {
        return TEXTES.get();
    }

    public static void remettreAZero() {
        TEXTES.set(0);
    }

    /**
     * ⚠️ {@code embedAll} suffit, et c'est le seul à écrire.
     *
     * <p>{@code EmbeddingModel} déclare une dizaine de méthodes, toutes
     * {@code default} : {@code embed(String)} délègue à
     * {@code embed(TextSegment)}, qui délègue à {@code embedAll}. Un modèle
     * écrit à la main n'a donc qu'une méthode à fournir — mais il faut le
     * savoir, car rien dans l'interface ne le dit.
     */
    @Override
    public Response<List<Embedding>> embedAll(List<TextSegment> segments) {
        var vecteurs = new ArrayList<Embedding>();
        for (var segment : segments) {
            TEXTES.incrementAndGet();
            vecteurs.add(Embedding.from(vecteur(segment.text())));
        }
        return Response.from(vecteurs);
    }

    @Override
    public int dimension() {
        return DIMENSIONS;
    }

    /**
     * Le vecteur d'un texte : un mot par case, puis une normalisation.
     *
     * <p>La normalisation n'est pas un détail. Sans elle, un passage long
     * aurait un vecteur plus « grand » et remporterait toutes les
     * comparaisons — le classement mesurerait la longueur, pas la
     * ressemblance.
     */
    public static float[] vecteur(String texte) {
        var valeurs = new float[DIMENSIONS];
        if (texte == null || texte.isBlank()) {
            return valeurs;
        }
        for (var mot : decouper(texte)) {
            valeurs[Math.abs(mot.hashCode()) % DIMENSIONS] += 1f;
        }
        // >>> depart: normaliser le vecteur — diviser chaque case par la longueur du vecteur, sans diviser par zero
        //     // sans normalisation, le classement mesure la longueur, pas la ressemblance
        double norme = 0;
        for (var valeur : valeurs) {
            norme += valeur * valeur;
        }
        norme = Math.sqrt(norme);
        if (norme > 0) {
            for (int i = 0; i < valeurs.length; i++) {
                valeurs[i] /= (float) norme;
            }
        }
        // <<<
        return valeurs;
    }

    /** Les mots porteurs de sens d'un texte. */
    public static List<String> decouper(String texte) {
        var mots = new ArrayList<String>();
        for (var brut : texte.toLowerCase(Locale.ROOT).split("[^\\p{L}\\p{N}-]+")) {
            if (brut.length() > 1 && !VIDES.contains(brut)) {
                mots.add(brut);
            }
        }
        return mots;
    }

    /** La similarité cosinus de deux vecteurs normalisés : leur produit. */
    public static double similarite(float[] premier, float[] second) {
        // >>> depart: rendre la similarite cosinus — le produit scalaire des deux vecteurs
        //     return 0;
        double produit = 0;
        for (int i = 0; i < premier.length && i < second.length; i++) {
            produit += premier[i] * second[i];
        }
        return produit;
        // <<<
    }
}
