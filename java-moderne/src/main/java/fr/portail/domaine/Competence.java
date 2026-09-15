package fr.portail.domaine;

/**
 * Les compétences qu'une offre peut exiger.
 *
 * <p>Une énumération, pas une chaîne : le compilateur refuse
 * {@code Competence.JAVVA}, alors qu'il accepte {@code "JAVVA"} sans un mot.
 * C'est le premier endroit du projet où un type évite un bug plutôt que de
 * le décrire.
 */
public enum Competence {

    JAVA("Java", true),
    SPRING("Spring", true),
    SQL("SQL", true),
    DOCKER("Docker", false),
    KUBERNETES("Kubernetes", false),
    REACT("React", true),
    TERRAFORM("Terraform", false),
    PYTHON("Python", true);

    private final String libelle;
    private final boolean langageOuCadre;

    Competence(String libelle, boolean langageOuCadre) {
        this.libelle = libelle;
        this.langageOuCadre = langageOuCadre;
    }

    public String libelle() {
        return libelle;
    }

    /** Vrai pour ce qu'on écrit, faux pour ce qu'on exploite. */
    public boolean langageOuCadre() {
        return langageOuCadre;
    }
}
