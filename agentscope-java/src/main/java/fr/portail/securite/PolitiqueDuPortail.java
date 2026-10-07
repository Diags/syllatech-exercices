package fr.portail.securite;

import io.agentscope.core.permission.PermissionBehavior;
import io.agentscope.core.permission.PermissionContextState;
import io.agentscope.core.permission.PermissionMode;
import io.agentscope.core.permission.PermissionRule;
import io.agentscope.core.tool.coding.CommandValidator;
import io.agentscope.core.tool.coding.UnixCommandValidator;
import java.nio.file.Path;
import java.util.Set;

/**
 * La politique du portail : ce que l'agent a le droit de faire, en un seul
 * endroit.
 *
 * <p>C'est l'argument du chapitre 3. Un {@code if (utilisateur.estAdmin())}
 * seme dans un service protege l'appel qu'on a pense a proteger ; une
 * politique declaree protege TOUS les appels, y compris celui qu'on ajoutera
 * dans six mois. Et elle se relit : cette classe est un document d'audit, ce
 * que des {@code if} disperses ne forment jamais.
 */
public final class PolitiqueDuPortail {

    /**
     * ⚠️ LE CONTENU D'UNE REGLE QUI VAUT POUR TOUS LES ARGUMENTS EST LA
     * CHAINE VIDE.
     *
     * <p>Pas {@code "*"}. Le contenu d'une regle est un MOTIF compare aux
     * arguments de l'appel ; l'etoile n'y est pas un joker, c'est un motif
     * litteral, et il ne correspond a rien. Une regle ecrite {@code "*"} est
     * enregistree, n'echoue pas, ne previent pas — et ne s'applique jamais.
     */
    public static final String TOUS_LES_ARGUMENTS = "";

    /** Les commandes qu'un agent d'analyse a le droit de lancer. */
    public static final Set<String> COMMANDES_AUTORISEES =
            Set.of("ls", "cat", "grep", "python");

    private static final CommandValidator VALIDATEUR = new UnixCommandValidator();

    private PolitiqueDuPortail() {
    }

    /**
     * La politique de l'assistant en libre-service : il lit, il n'ecrit pas.
     *
     * <p>⚠️ Le mode compte autant que les regles. Sous {@code DEFAULT}, meme
     * un outil de LECTURE demande confirmation — prudent, et invivable.
     * {@code EXPLORE} autorise la lecture et refuse l'ecriture : c'est le
     * mode a connaitre pour un assistant expose a des utilisateurs.
     */
    public static PermissionContextState lectureSeule() {
        // TODO : poser les regles du portail — le MODE, puis une regle par outil. Attention au contenu des regles : voir TOUS_LES_ARGUMENTS
        return PermissionContextState.builder().build();
    }

    /** La politique d'un back-office : la suppression demande un humain. */
    public static PermissionContextState avecApprobationHumaine() {
        return PermissionContextState.builder()
                .mode(PermissionMode.EXPLORE)
                .addAllowRule("rechercher_offres",
                              regle("rechercher_offres", PermissionBehavior.ALLOW))
                .addAllowRule("compter_candidatures",
                              regle("compter_candidatures", PermissionBehavior.ALLOW))
                .addAskRule("supprimer_offre",
                            regle("supprimer_offre", PermissionBehavior.ASK))
                .build();
    }

    private static PermissionRule regle(String outil,
                                        PermissionBehavior comportement) {
        return new PermissionRule(outil, TOUS_LES_ARGUMENTS, comportement,
                                  "politique-du-portail");
    }

    // -- le controle que le validateur ne fait pas -------------------------

    /**
     * Le chemin est-il acceptable ? C'est la ligne qui manque partout.
     *
     * <p>⚠️ {@code CommandValidator.validate} lit l'EXECUTABLE, jamais ses
     * arguments : {@code cat} etant sur la liste blanche,
     * {@code cat /etc/passwd} passe. Et le controle fourni par l'interface,
     * {@code isPathWithinCurrentDirectory}, attrape la remontee par
     * {@code ..} mais declare un chemin ABSOLU interne.
     *
     * <p>Il faut donc les deux verifications, et une seule est fournie.
     */
    public static boolean cheminAcceptable(String chemin) {
        if (chemin == null || chemin.isBlank()) {
            return false;
        }
        // TODO : refuser tout chemin qui SORT du workspace — l'absolu comme la remontee. Resoudre et NORMALISER : comparer des chaines ne suffit pas, et sur exception on REFUSE
        return true;
    }

    /**
     * Ce que le controle FOURNI par le framework en dit — pour comparaison.
     *
     * <p>⚠️ Le chapitre 4 met les deux cote a cote, et l'ecart est le sujet :
     * {@code isPathWithinCurrentDirectory} declare interne un chemin absolu,
     * declare interne une remontee d'un seul cran, et leve une exception sur
     * le chemin {@code "."} (constate sur la 2.0.3).
     */
    public static String avisDuFramework(String chemin) {
        try {
            return VALIDATEUR.isPathWithinCurrentDirectory(chemin)
                    ? "interne" : "externe";
        } catch (RuntimeException erreur) {
            return erreur.getClass().getSimpleName();
        }
    }

    /**
     * La commande complete : liste blanche, enchainement, ET chemins.
     *
     * <p>Les trois controles, parce qu'aucun ne remplace les autres.
     */
    public static boolean commandeAcceptable(String commande) {
        if (commande == null || commande.isBlank()) {
            return false;
        }
        if (!VALIDATEUR.validate(commande, COMMANDES_AUTORISEES).isAllowed()) {
            return false;
        }
        // ⚠️ Et on relit les arguments, un par un : c'est ce que le
        // validateur ne fait pas.
        String[] morceaux = commande.trim().split("\\s+");
        for (int rang = 1; rang < morceaux.length; rang++) {
            String morceau = morceaux[rang];
            if (morceau.startsWith("-")) {
                continue;   // une option, pas un chemin
            }
            if (!cheminAcceptable(morceau)) {
                return false;
            }
        }
        return true;
    }
}
