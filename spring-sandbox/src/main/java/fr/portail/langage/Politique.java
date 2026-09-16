package fr.portail.langage;

import java.util.EnumSet;
import java.util.Set;

/**
 * Ce qu'un script a le droit de demander.
 *
 * <p>⚠️ UNE POLITIQUE N'EST PAS UN BAC A SABLE. Elle vit DANS le processus
 * qui execute le code : un script qui trouverait un moyen de la contourner
 * — et c'est le metier d'un attaquant — n'aurait plus rien devant lui. Elle
 * est une couche, la derniere, et elle ne vaut que posee derriere une
 * frontiere de processus.
 *
 * <p>C'est exactement ce qui a fait retirer le {@code SecurityManager} de
 * Java : une politique interne au processus ne resiste pas a du code qui
 * s'execute dans ce processus.
 */
public final class Politique {

    private final Set<Capacite> accordees;
    private final String nom;

    private Politique(String nom, Set<Capacite> accordees) {
        this.nom = nom;
        this.accordees = accordees;
    }

    /**
     * ⚠️ Ce que fait un moteur de script dans votre JVM : rien n'est
     * refuse, parce que rien ne refuse.
     */
    public static Politique toutPermis() {
        return new Politique("tout permis", EnumSet.allOf(Capacite.class));
    }

    /** Ce qu'un bac a sable accorde : rien du tout. */
    public static Politique rienDuTout() {
        return new Politique("rien du tout", EnumSet.noneOf(Capacite.class));
    }

    public static Politique de(String nom, Capacite... capacites) {
        return new Politique(nom, capacites.length == 0
                ? EnumSet.noneOf(Capacite.class)
                : EnumSet.copyOf(java.util.List.of(capacites)));
    }

    public boolean accorde(Capacite capacite) {
        return accordees.contains(capacite);
    }

    public Set<Capacite> accordees() {
        return Set.copyOf(accordees);
    }

    public String nom() {
        return nom;
    }

    void exiger(Capacite capacite, String tentative) {
        if (!accordees.contains(capacite)) {
            throw new RefusDePrivilege(capacite, tentative);
        }
    }

    @Override
    public String toString() {
        return nom + " " + accordees;
    }
}
