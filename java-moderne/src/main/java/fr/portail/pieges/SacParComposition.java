package fr.portail.pieges;

import java.util.Collection;
import java.util.HashSet;
import java.util.Set;

/**
 * Le même compteur, écrit par composition — et qui compte juste.
 *
 * <p>Ce n'est pas une pièce à conviction : c'est la <strong>version
 * correcte</strong>, gardée dans ce paquet pour être comparée à
 * {@link SacCompteur} au chapitre 2.
 *
 * <p>Un seul changement : cette classe n'<em>hérite</em> pas d'un
 * {@code HashSet}, elle en <em>possède</em> un. Elle ne voit donc que les
 * appels qu'on lui adresse, et ce que l'implémentation interne fait de
 * ses propres méthodes ne la concerne plus. Le cours dit « composez pour
 * tout le reste » ; l'écart entre 6 et 3 est la raison.
 */
public final class SacParComposition<E> {

    private final Set<E> contenu = new HashSet<>();

    private int ajoutes;

    public int ajoutes() {
        return ajoutes;
    }

    public boolean add(E element) {
        ajoutes++;
        return contenu.add(element);
    }

    public boolean addAll(Collection<? extends E> elements) {
        ajoutes += elements.size();
        return contenu.addAll(elements);
    }

    public int size() {
        return contenu.size();
    }

    public boolean contains(Object element) {
        return contenu.contains(element);
    }

    /** Une vue non modifiable : l'intérieur reste à l'intérieur. */
    public Set<E> contenu() {
        return Set.copyOf(contenu);
    }
}
