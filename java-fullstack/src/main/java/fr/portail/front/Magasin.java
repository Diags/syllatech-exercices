package fr.portail.front;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.BiFunction;
import java.util.function.Consumer;

/**
 * Un magasin a la Redux : un etat, des actions, des reducteurs PURS.
 *
 * <p>POURQUOI CE CODE EXISTE
 * <p>Parce que « l'etat reste immuable grace a Immer » est une promesse qui
 * se verifie. Ici, un reducteur rend un NOUVEL etat ; l'ancien est toujours
 * la, intact, et le magasin le garde — c'est exactement ce qui permet le
 * retour arriere et les outils de developpement qui rejouent l'historique.
 *
 * <p>⚠️ CE QUE CE CODE N'EST PAS. Ce n'est pas Redux Toolkit : ni Immer, ni
 * middleware, ni {@code createAsyncThunk}. C'est le CONTRAT — etat + action
 * → nouvel etat — et c'est lui qui porte les proprietes.
 *
 * <p>⚠️ ET LA PREMIERE QUESTION RESTE : en avez-vous besoin ? La plupart de
 * l'etat d'une application est LOCAL — le contenu d'un champ, l'ouverture
 * d'un menu — et n'a rien a faire dans un magasin global. Redux repond au
 * probleme de l'etat PARTAGE entre composants eloignes ; l'y mettre pour le
 * reste transforme chaque saisie de caractere en action globale.
 */
public final class Magasin<E> {

    /** Une action : un type, et une charge utile. */
    public record Action(String type, Object charge) {
    }

    private final BiFunction<E, Action, E> reducteur;
    private final List<E> historique = new ArrayList<>();
    private final List<Consumer<E>> abonnes = new ArrayList<>();
    private E etat;

    public Magasin(E etatInitial, BiFunction<E, Action, E> reducteur) {
        this.etat = etatInitial;
        this.reducteur = reducteur;
        this.historique.add(etatInitial);
    }

    /**
     * Envoie une action. Le reducteur decide du nouvel etat.
     *
     * <p>⚠️ IL N'Y A QU'UNE FACON DE CHANGER L'ETAT, et c'est celle-la. Un
     * composant qui modifierait l'etat directement casserait le rendu : rien
     * ne serait notifie, et l'ecran resterait en retard sur les donnees.
     */
    public void envoyer(Action action) {
        E precedent = etat;
        E suivant = reducteur.apply(precedent, action);
        if (suivant == precedent) {
            // Un reducteur qui ne connait pas l'action rend l'etat tel quel :
            // aucun rendu n'est declenche, et c'est voulu.
            return;
        }
        etat = suivant;
        historique.add(suivant);
        for (Consumer<E> abonne : abonnes) {
            abonne.accept(suivant);
        }
    }

    public E etat() {
        return etat;
    }

    public void abonner(Consumer<E> abonne) {
        abonnes.add(abonne);
    }

    /** Tous les etats traverses — ce que les outils de dev rejouent. */
    public List<E> historique() {
        return List.copyOf(historique);
    }

    /**
     * ⚠️ LA MESURE DU « PROP DRILLING ». Sans magasin, une donnee partagee
     * descend de props en props : chaque composant intermediaire declare un
     * parametre dont il ne fait rien, et chacun se re-rend quand la donnee
     * change.
     *
     * @param profondeur le nombre de niveaux entre la source et le
     *     consommateur
     * @return le nombre de composants qui doivent connaitre la donnee
     */
    public static int composantsTraverses(int profondeur, boolean avecMagasin) {
        // Avec un magasin : la source et le consommateur, et personne
        // d'autre. Sans : tout le chemin.
        return avecMagasin ? 2 : profondeur + 1;
    }
}
