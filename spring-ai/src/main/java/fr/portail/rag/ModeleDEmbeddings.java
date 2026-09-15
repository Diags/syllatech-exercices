package fr.portail.rag;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.ai.document.Document;
import org.springframework.ai.embedding.Embedding;
import org.springframework.ai.embedding.EmbeddingModel;
import org.springframework.ai.embedding.EmbeddingRequest;
import org.springframework.ai.embedding.EmbeddingResponse;
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
 * change pas.</strong> Ce qui est mesuré reste vrai : la similarité cosinus,
 * le classement des documents, le fait que le contexte trouvé finisse dans le
 * prompt, et l'effet de la taille des morceaux. Ce qui n'est PAS mesuré, c'est
 * la qualité sémantique : ce modèle ne rapprochera jamais « salaire » de
 * « rémunération ». Un vrai modèle le ferait, et c'est exactement ce qu'on
 * achète en payant des embeddings.
 *
 * <p>256 dimensions : assez pour que deux textes différents ne se percutent
 * pas, assez peu pour que le chapitre puisse afficher un vecteur.
 */
@Component
public class ModeleDEmbeddings implements EmbeddingModel {

    public static final int DIMENSIONS = 256;

    /** Les mots trop courants pour porter du sens. */
    private static final java.util.Set<String> VIDES = java.util.Set.of(
            "le", "la", "les", "un", "une", "des", "de", "du", "et", "ou",
            "a", "au", "aux", "en", "est", "sont", "pour", "par", "dans",
            "sur", "ce", "cette", "que", "qui", "quoi", "avec", "sans");

    @Override
    public EmbeddingResponse call(EmbeddingRequest requete) {
        var resultats = new ArrayList<Embedding>();
        var textes = requete.getInstructions();
        for (int i = 0; i < textes.size(); i++) {
            resultats.add(new Embedding(vecteur(textes.get(i)), i));
        }
        return new EmbeddingResponse(resultats);
    }

    @Override
    public float[] embed(Document document) {
        return vecteur(document.getText());
    }

    @Override
    public int dimensions() {
        return DIMENSIONS;
    }

    /**
     * Le vecteur d'un texte : un mot par case, puis une normalisation.
     *
     * <p>La normalisation n'est pas un détail. Sans elle, un document long
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
        //     // sans normalisation, le chapitre 3 mesure une norme qui n'est pas 1
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
