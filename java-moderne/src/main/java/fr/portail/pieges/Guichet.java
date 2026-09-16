package fr.portail.pieges;

import java.util.concurrent.atomic.AtomicInteger;

/**
 * Le guichet qui compte les candidatures reçues — deux fois, de deux façons.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Le champ
 * {@code recuesSansProtection} est incrémenté par {@code recues++}, qui n'est
 * pas une opération : c'en est trois — lire, ajouter un, écrire. Deux threads
 * qui lisent la même valeur écrivent la même valeur, et un des deux comptages
 * disparaît.
 *
 * <p>Le chapitre 5 lance huit threads virtuels qui incrémentent les deux
 * compteurs le même nombre de fois, et affiche l'écart. Il est de l'ordre de
 * 40 % — pas de 0,001 %, et c'est ce qui rend le bug dangereux : il est trop
 * gros pour être un arrondi et trop irrégulier pour être reproductible.
 */
public final class Guichet {

    private int recuesSansProtection;

    private final AtomicInteger recuesAtomiques = new AtomicInteger();

    private int recuesSousVerrou;

    private final Object verrou = new Object();

    /** Le geste fautif. Trois opérations que rien ne rend indivisibles. */
    public void recevoirSansProtection() {
        recuesSansProtection++;
    }

    /** Sans verrou : le processeur garantit l'indivisibilité. */
    public void recevoirAtomique() {
        recuesAtomiques.incrementAndGet();
    }

    /** Avec verrou : correct aussi, et plus général — mais il sérialise. */
    public void recevoirSousVerrou() {
        synchronized (verrou) {
            recuesSousVerrou++;
        }
    }

    public int sansProtection() {
        return recuesSansProtection;
    }

    public int atomiques() {
        return recuesAtomiques.get();
    }

    public int sousVerrou() {
        synchronized (verrou) {
            return recuesSousVerrou;
        }
    }
}
