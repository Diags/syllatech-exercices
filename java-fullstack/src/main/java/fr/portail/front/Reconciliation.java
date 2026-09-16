package fr.portail.front;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * La reconciliation d'une liste — avec et sans {@code key}.
 *
 * <p>POURQUOI CE CODE EST EN JAVA
 * <p>Parce qu'un cours ne peut pas exiger Node ni un navigateur, et que
 * l'affirmation « le {@code key} n'est pas decoratif » merite mieux qu'une
 * phrase. L'algorithme ci-dessous est celui que React applique a une liste :
 * apparier l'ancien rendu au nouveau, puis n'emettre que les operations
 * necessaires. Ce qui est compte ici — le nombre d'operations sur le DOM —
 * est ce que React ferait.
 *
 * <p>⚠️ CE QUE CE CODE N'EST PAS. Ce n'est pas React : ni fibres, ni
 * priorites, ni rendu concurrent. C'est l'appariement d'une liste, et c'est
 * precisement ce que le {@code key} gouverne.
 */
public final class Reconciliation {

    /** Un element de liste, tel qu'il est rendu. */
    public record Element(String cle, String texte) {
    }

    /** Une operation sur le DOM. */
    public enum Operation { CREER, SUPPRIMER, DEPLACER, METTRE_A_JOUR }

    /** Le resultat d'une reconciliation. */
    public record Rendu(List<Operation> operations) {

        public long compte(Operation operation) {
            return operations.stream().filter(op -> op == operation).count();
        }

        public int total() {
            return operations.size();
        }
    }

    private Reconciliation() {
    }

    /**
     * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
     *
     * <p>La reconciliation par POSITION : c'est ce que React fait quand la
     * liste n'a pas de {@code key}, et c'est aussi ce qu'il fait quand la
     * {@code key} est l'INDICE du tableau — les deux sont equivalents.
     *
     * <p>Elle compare le rang 0 au rang 0, le rang 1 au rang 1, et ainsi de
     * suite. Inserer un element en tete decale donc tout : chaque ligne est
     * mise a jour, alors qu'aucune n'a change.
     */
    public static Rendu parPosition(List<Element> avant, List<Element> apres) {
        List<Operation> operations = new ArrayList<>();
        int commun = Math.min(avant.size(), apres.size());
        for (int rang = 0; rang < commun; rang++) {
            if (!avant.get(rang).texte().equals(apres.get(rang).texte())) {
                operations.add(Operation.METTRE_A_JOUR);
            }
        }
        for (int rang = commun; rang < apres.size(); rang++) {
            operations.add(Operation.CREER);
        }
        for (int rang = commun; rang < avant.size(); rang++) {
            operations.add(Operation.SUPPRIMER);
        }
        return new Rendu(List.copyOf(operations));
    }

    /**
     * La reconciliation par CLE : celle qu'une {@code key} stable permet.
     *
     * <p>Chaque element est retrouve par son identite, pas par sa place. Un
     * element insere en tete est donc CREE, et les autres sont, au pire,
     * deplaces — jamais reconstruits.
     */
    public static Rendu parCle(List<Element> avant, List<Element> apres) {
        Map<String, Element> anciens = new LinkedHashMap<>();
        Map<String, Integer> rangsAnciens = new HashMap<>();
        for (int rang = 0; rang < avant.size(); rang++) {
            anciens.put(avant.get(rang).cle(), avant.get(rang));
            rangsAnciens.put(avant.get(rang).cle(), rang);
        }

        List<Operation> operations = new ArrayList<>();
        // TODO : apparier par CLE, pas par position — un element retrouve garde son nœud du DOM et son etat ; et un element deja dans le bon ordre relatif ne bouge PAS (heuristique du dernier indice place)
        return new Rendu(List.of());
    }

    /**
     * ⚠️ ET LE CAS QUI FAIT VRAIMENT MAL : l'etat interne d'un composant.
     *
     * <p>Une ligne de liste n'est pas qu'un texte : elle peut contenir une
     * case a cocher, un champ de saisie a demi rempli. Cet etat suit le
     * composant, et le composant est identifie par sa cle.
     *
     * <p>Par POSITION, l'etat de la ligne 0 reste sur la ligne 0 — donc il
     * migre vers une AUTRE offre quand on insere en tete. C'est le bogue que
     * l'utilisateur signale par « ma coche a saute sur la mauvaise ligne »,
     * et qu'aucun test d'affichage ne voit.
     *
     * @return la cle de l'element qui HERITE de l'etat du rang donne
     */
    public static String quiHeriteDeLEtat(List<Element> apres, int rang,
                                          boolean parCle, String cleInitiale) {
        if (parCle) {
            return cleInitiale;   // l'etat suit la cle, donc l'element
        }
        return rang < apres.size() ? apres.get(rang).cle() : "(aucun)";
    }
}
