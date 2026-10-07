package fr.portail.langage;

/**
 * Ce qu'un script peut demander au monde exterieur.
 *
 * <p>Trois capacites, et ce sont les trois portes du cours : le DISQUE, le
 * RESEAU, et la CONFIGURATION de l'application. Les nommer separement est
 * deja un progres : « donner acces au systeme » ne veut rien dire, « donner
 * acces au disque et pas au reseau » se decide.
 */
public enum Capacite {

    /** ⚠️ Lire le disque de l'hote. */
    FICHIERS("lire des fichiers"),

    /** ⚠️ Ouvrir une connexion sortante — c'est-a-dire exfiltrer. */
    RESEAU("ouvrir une connexion reseau"),

    /** ⚠️ Lire les proprietes de l'application, donc ses secrets. */
    PROPRIETES("lire les proprietes de l'application");

    private final String libelle;

    Capacite(String libelle) {
        this.libelle = libelle;
    }

    public String libelle() {
        return libelle;
    }
}
