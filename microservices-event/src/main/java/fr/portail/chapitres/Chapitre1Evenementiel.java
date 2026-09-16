package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DeposerCandidature;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 1 — L'architecture événementielle.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Evenementiel
 * </pre>
 *
 * <p>« Un événement est un fait passé, immuable ; une commande est une
 * intention qui peut échouer. » Ce chapitre rend la différence
 * <strong>visible</strong> : il envoie une commande refusée, puis une
 * acceptée, et compte ce que le journal contient après chacune.
 *
 * <p>Il fabrique ensuite une livraison <em>at-least-once</em> — le même
 * événement deux fois — et montre le compteur qui se met à mentir.
 */
public final class Chapitre1Evenementiel {

    private Chapitre1Evenementiel() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            Console.titre(1, "UNE COMMANDE SE REFUSE, UN EVENEMENT NON");
            int avant = evenements(banc);
            String refus;
            try {
                banc.passerelle().sendAndWait(
                        new DeposerCandidature("c-1", "  ", "OFF-014"));
                refus = "acceptee";
            } catch (RuntimeException erreur) {
                refus = erreur.getClass().getSimpleName() + " — "
                        + court(erreur.getMessage());
            }
            int apresRefus = evenements(banc);
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-1", "Awa", "OFF-014"));
            int apresSucces = evenements(banc);
            Console.tableau(List.of("la commande envoyee", "verdict",
                    "journal"), List.of(
                    List.of("(rien encore)", "-", String.valueOf(avant)),
                    List.of("Deposer, sans candidat", court(refus, 40),
                            String.valueOf(apresRefus)),
                    List.of("Deposer, avec candidat", "acceptee",
                            String.valueOf(apresSucces))),
                    List.of(24, 42, 10));
            System.out.println();
            Console.texte("Une commande refusee ne laisse AUCUNE trace : le "
                    + "journal ne bouge pas. C'est ce qui distingue les deux "
                    + "notions — une intention peut etre rejetee, un fait "
                    + "s'est deja produit. On ne stocke que les faits.");
            System.out.println();
            Console.texte("⚠️ Consequence a connaitre : les refus ne sont donc "
                    + "PAS auditables par le journal d'evenements. Si vous "
                    + "devez savoir qui a tente quoi, c'est une trace "
                    + "separee — journal applicatif ou evenement dedie, "
                    + "decide explicitement.");

            Console.titre(2, "UN INVARIANT QUE SEUL L'AGREGAT PEUT TENIR");
            String tropTot;
            try {
                banc.passerelle().sendAndWait(
                        new Decider("c-1", true, "excellent profil"));
                tropTot = "acceptee";
            } catch (RuntimeException erreur) {
                tropTot = erreur.getClass().getSimpleName() + " — "
                          + court(erreur.getMessage());
            }
            Console.ligne("decider sans entretien planifie", tropTot, 36);
            Console.ligne("evenements dans le journal",
                    String.valueOf(evenements(banc)), 36);
            System.out.println();
            Console.texte("L'agregat a relu son propre passe avant de "
                    + "decider : c'est cela, une frontiere de coherence. La "
                    + "regle « pas de decision sans entretien » ne peut pas "
                    + "vivre dans une projection — une projection est en "
                    + "retard par construction, et deux lecteurs y verraient "
                    + "le meme etat perime au meme instant.");

            Console.titre(3, "CE QUE LE DECOUPLAGE ACHETE, ET CE QU'IL COUTE");
            Console.ligne("emetteur au courant de ses consommateurs",
                    "non", 44);
            Console.ligne("projections abonnees",
                    "2 (vue, compteur)", 30);
            Console.ligne("lignes dans la vue",
                    String.valueOf(banc.vue().taille()), 30);
            Console.ligne("evenements recus par la vue",
                    String.valueOf(banc.vue().evenementsRecus()), 32);
            System.out.println();
            Console.texte("L'agregat n'a jamais nomme la moindre projection. "
                    + "Il publie un fait ; ce qui ecoute est ailleurs. C'est "
                    + "le decouplage que le cours promet, et il est reel — "
                    + "ajouter un troisieme consommateur ne touche pas une "
                    + "ligne du modele d'ecriture.");
            System.out.println();
            Console.texte("⚠️ Le prix est la coherence a terme. Ici le bus "
                    + "est en memoire et le delai est nul ; des qu'un vrai "
                    + "bus separe les deux cotes, il existe une fenetre "
                    + "pendant laquelle l'ecriture est faite et la lecture "
                    + "ne la voit pas encore. Ce n'est pas un bug a corriger, "
                    + "c'est une propriete a assumer — cote interface.");

            Console.titre(4, "AT-LEAST-ONCE : LE MEME FAIT, DEUX FOIS");
            banc.compteur().vider();
            var fait = new CandidatureDeposee("c-2", "Karim", "OFF-021");
            banc.compteur().on(fait);
            banc.compteur().on(fait);
            Console.tableau(List.of("le consommateur", "evenements recus",
                    "candidatures comptees sur OFF-021"), List.of(
                    List.of("compteur naif", "2",
                            String.valueOf(banc.compteur().compteNaif("OFF-021"))),
                    List.of("compteur idempotent", "2",
                            String.valueOf(banc.compteur()
                                    .compteIdempotent("OFF-021")))),
                    List.of(24, 20, 36));
            System.out.println();
            Console.texte("Le meme fait, livre deux fois — ce que fait un bus "
                    + "en at-least-once quand un accuse de reception se "
                    + "perd. Le compteur naif annonce deux candidatures la ou "
                    + "il n'y en a qu'une, et AUCUNE erreur n'est levee : le "
                    + "chiffre est simplement faux.");
            System.out.println();
            Console.texte("La recette de l'idempotence tient en une ligne : "
                    + "retenir ce qu'on a deja traite. Ici l'identifiant de "
                    + "la candidature suffit ; en production, on garde "
                    + "l'identifiant du MESSAGE dans une table, ecrite dans "
                    + "la meme transaction que la mise a jour — sinon on "
                    + "deplace le probleme.");
            System.out.println();
            Console.texte("⚠️ « Exactly-once » n'existe pas au niveau du "
                    + "transport : c'est at-least-once plus une "
                    + "deduplication chez le consommateur. Le contrat a "
                    + "integrer avant d'ecrire la moindre ligne, dit le "
                    + "cours — et il a raison.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La plomberie qu'Axon fournit : quel bus, quel "
                    + "magasin, et comment une commande trouve la bonne "
                    + "instance d'agregat.");
            System.out.println();
        }
    }

    /** Le nombre d'événements dans le journal, tous agrégats confondus. */
    private static int evenements(Banc banc) {
        var tout = new ArrayList<Object>();
        banc.moteur().readEvents(null, false).forEach(tout::add);
        return tout.size();
    }

    private static String court(String texte) {
        return court(texte, 40);
    }

    private static String court(String texte, int largeur) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= largeur ? plat
                : plat.substring(0, largeur - 3) + "...";
    }
}
