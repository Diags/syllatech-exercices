package fr.portail.erreurs;

/**
 * L'entreprise citée dans la demande n'existe pas au catalogue.
 *
 * <p>Une exception <em>métier</em>, non vérifiée — donc elle annule la
 * transaction, ce qui est le bon comportement ici. Le
 * {@link GestionnaireErreurs} la traduit une seule fois en
 * {@code ProblemDetail}, et toutes les routes en bénéficient.
 */
public class EntrepriseInconnue extends RuntimeException {

    private static final long serialVersionUID = 1L;

    private final String nom;

    public EntrepriseInconnue(String nom) {
        super("entreprise inconnue : " + nom);
        this.nom = nom;
    }

    public String nom() {
        return nom;
    }
}
