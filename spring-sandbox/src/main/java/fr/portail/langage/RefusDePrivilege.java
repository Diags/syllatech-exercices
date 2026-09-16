package fr.portail.langage;

/**
 * Le script a demande une capacite que la politique ne lui accorde pas.
 *
 * <p>⚠️ Distincte d'{@link ErreurScript} a dessein : une faute de frappe du
 * candidat et une tentative d'exfiltration ne se journalisent pas pareil, et
 * ne se comptent pas pareil. Le chapitre 6 compte les secondes.
 */
public class RefusDePrivilege extends RuntimeException {

    private final Capacite capacite;

    public RefusDePrivilege(Capacite capacite, String tentative) {
        super("REFUS : le script a tente de " + capacite.libelle()
              + " (« " + tentative + " »)");
        this.capacite = capacite;
    }

    public Capacite capacite() {
        return capacite;
    }
}
