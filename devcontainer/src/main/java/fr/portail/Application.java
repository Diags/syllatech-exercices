package fr.portail;

/**
 * Le point d'entree du Portail de l'emploi.
 *
 * Comme le pom.xml, ce fichier existe pour que le dev container ait
 * quelque chose a decrire : le Dockerfile copie `src/`, et c'est
 * `build.context` qui decide si ce dossier est visible.
 */
public final class Application {
    public static void main(String[] args) {
        System.out.println("Portail de l'emploi");
    }
}
