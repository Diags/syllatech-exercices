package fr.portail.securite;

/**
 * La sortie d'un bac a sable est une donnee HOSTILE. On la traite comme
 * telle, ou on la regrette.
 *
 * <p>Trois gestes, et ils ne se remplacent pas :
 * <ul>
 *   <li><strong>plafonner</strong> — la taille est choisie par le candidat,
 *       pas par vous ;</li>
 *   <li><strong>echapper</strong> avant tout affichage. Le candidat ecrit ce
 *       qu'il veut sur {@code stdout}, y compris un {@code <script>} ;</li>
 *   <li><strong>ne jamais interpreter</strong> — ni SQL, ni expression, ni
 *       modele. Rien de ce qui sort du bac ne doit etre evalue.</li>
 * </ul>
 *
 * <p>⚠️ Le troisieme est celui qu'on oublie. Concatener la sortie dans une
 * requete SQL de notation, ou la passer a un moteur de templates, redonne au
 * candidat l'execution qu'on venait de lui retirer — dans VOTRE processus,
 * cette fois.
 */
public final class Sortie {

    public static final int PLAFOND = 10_000;

    private Sortie() {
    }

    public static String plafonner(String texte) {
        if (texte == null) {
            return "";
        }
        return texte.length() <= PLAFOND
                ? texte
                : texte.substring(0, PLAFOND) + "…(tronque)";
    }

    /** L'echappement HTML, dans l'ordre : l'esperluette EN PREMIER. */
    public static String echapper(String texte) {
        if (texte == null) {
            return "";
        }
        // TODO : echapper les cinq caracteres dangereux — et l'esperluette EN PREMIER, sinon « &lt; » ressort en « &amp;lt; »
        return texte;
    }

    /** Ce qu'on affiche : plafonne PUIS echappe. */
    public static String pourAffichage(String texte) {
        return echapper(plafonner(texte));
    }

    /** Vrai si le texte contient de quoi nuire une fois insere tel quel. */
    public static boolean suspecte(String texte) {
        if (texte == null) {
            return false;
        }
        String bas = texte.toLowerCase();
        return bas.contains("<script") || bas.contains("javascript:")
               || bas.contains("onerror=") || bas.contains("<iframe");
    }
}
