package fr.portail.pieges;

import java.util.Collection;
import java.util.HashSet;

/**
 * Un ensemble qui compte ce qu'on lui a demandé d'ajouter — et compte double.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Le code est
 * évident, le raisonnement est juste, et le résultat est faux : après un
 * {@code addAll} de trois éléments, le compteur vaut <strong>six</strong>.
 *
 * <p>La raison n'est écrite nulle part dans ce fichier : {@code HashSet.addAll}
 * appelle {@code add} pour chaque élément. Notre {@code addAll} compte trois,
 * puis délègue — et notre {@code add} compte trois de plus. C'est le
 * « problème de la classe de base fragile » que le cours nomme : la
 * sous-classe dépend d'un <em>détail d'implémentation</em> de la classe mère,
 * détail que rien n'oblige à rester stable.
 *
 * <p>La composition n'a pas ce défaut : une classe qui <em>possède</em> un
 * {@code HashSet} et lui délègue ne voit que les appels qu'on lui fait.
 * {@link SacParComposition} est la version juste, gardée à côté pour la
 * comparaison.
 */
public class SacCompteur<E> extends HashSet<E> {

    private static final long serialVersionUID = 1L;

    private int ajoutes;

    public int ajoutes() {
        return ajoutes;
    }

    @Override
    public boolean add(E element) {
        ajoutes++;
        return super.add(element);
    }

    @Override
    public boolean addAll(Collection<? extends E> elements) {
        ajoutes += elements.size();
        return super.addAll(elements);
    }
}
