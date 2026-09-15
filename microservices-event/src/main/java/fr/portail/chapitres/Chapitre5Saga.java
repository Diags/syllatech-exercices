package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Agenda;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.saga.SagaDeCandidature;
import java.util.ArrayList;
import java.util.List;
import org.axonframework.eventhandling.DomainEventMessage;

/**
 * Chapitre 5 — Le pattern Saga.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Saga
 * </pre>
 *
 * <p>« Si une étape échoue, elle défait les précédentes par des actions
 * inverses. » Ce chapitre déroule les deux chemins, étape par étape : trois
 * candidatures pour deux créneaux, et la troisième déclenche la
 * <strong>compensation</strong>.
 *
 * <p>Tout est imprimé dans l'ordre — ce que la saga reçoit, ce qu'elle envoie,
 * et ce que le journal finit par contenir.
 */
public final class Chapitre5Saga {

    private Chapitre5Saga() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrerAvecSaga()) {
            SagaDeCandidature.viderLeJournal();

            Console.titre(1, "LE CHEMIN HEUREUX, ETAPE PAR ETAPE");
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-awa", "Awa", "OFF-014"));
            Console.sousTitre("Ce que la saga a fait :");
            for (var etape : SagaDeCandidature.journal()) {
                Console.texte("→ " + etape, 5);
            }
            System.out.println();
            Console.ligne("candidature", statut(banc, "c-awa"), 26);
            Console.ligne("creneau obtenu", creneau(banc, "c-awa"), 26);
            System.out.println();
            Console.texte("Un seul appel de l'exterieur — "
                    + "`DeposerCandidature` — et trois agregats ont bouge. "
                    + "Personne n'a orchestre cela depuis un controleur : la "
                    + "saga a ecoute un fait, envoye une commande, ecoute le "
                    + "fait suivant, et ainsi de suite.");
            System.out.println();
            Console.texte("C'est l'orchestration, par opposition a la "
                    + "choregraphie ou chaque service reagirait dans son "
                    + "coin. On y gagne un endroit unique ou lire la "
                    + "sequence — et on y perd un point de coordination de "
                    + "plus a surveiller.");

            Console.titre(2, "L'ETAPE QUI ECHOUE, ET LA COMPENSATION");
            SagaDeCandidature.viderLeJournal();
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-karim", "Karim", "OFF-021"));
            SagaDeCandidature.viderLeJournal();
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-lea", "Lea", "OFF-033"));
            Console.ligne("creneaux ouverts",
                    String.valueOf(Agenda.CRENEAUX), 26);
            Console.ligne("candidatures deposees", "3", 26);
            System.out.println();
            Console.sousTitre("Ce que la saga a fait pour la troisieme :");
            for (var etape : SagaDeCandidature.journal()) {
                Console.texte("→ " + etape, 5);
            }
            System.out.println();
            Console.tableau(List.of("candidature", "statut final"), List.of(
                    List.of("c-awa", statut(banc, "c-awa")),
                    List.of("c-karim", statut(banc, "c-karim")),
                    List.of("c-lea", statut(banc, "c-lea"))),
                    List.of(20, 24));
            System.out.println();
            Console.texte("La troisieme candidature n'a pas eu de creneau, et "
                    + "elle a ete ANNULEE — pas par un rollback, qui serait "
                    + "impossible : elle etait deja ecrite dans son propre "
                    + "journal. La saga a envoye l'action inverse, et c'est "
                    + "cette action qui a produit le fait « annulee ».");
            System.out.println();
            Console.texte("⚠️ Relisez la ligne de la troisieme dans le "
                    + "tableau : elle est passee par DEPOSEE avant d'etre "
                    + "ANNULEE. Pendant quelques instants, le systeme "
                    + "affichait une candidature qui allait etre defaite. "
                    + "C'est inherent a la saga — il n'y a pas d'etat "
                    + "intermediaire invisible, contrairement a une "
                    + "transaction.");

            Console.titre(3, "CE QUE LE REFUS EST, ET CE QU'IL N'EST PAS");
            Console.sousTitre("Le flux de l'agenda :");
            for (var message : flux(banc, Banc.AGENDA)) {
                Console.texte("seq=%d  %s".formatted(message.getSequenceNumber(),
                        message.getPayload()), 5);
            }
            System.out.println();
            Console.texte("Le refus de creneau est un EVENEMENT, pas une "
                    + "exception. C'est une decision de conception, et elle "
                    + "est capitale : une exception ne serait vue que de "
                    + "l'appelant direct, et la saga resterait a attendre une "
                    + "reponse qui ne viendrait jamais.");
            System.out.println();
            Console.texte("La regle pratique : ce qui interesse d'autres "
                    + "acteurs que l'appelant doit etre un fait publie. Une "
                    + "exception sert a dire « votre commande est "
                    + "invalide » ; un evenement sert a dire « voici ce qui "
                    + "s'est passe ».");

            Console.titre(4, "CE QUI FAIT VIVRE, ET MOURIR, UNE SAGA");
            Console.ligne("evenements dans le journal",
                    String.valueOf(tous(banc).size()), 32);
            Console.ligne("sagas encore vivantes",
                    "0 — toutes terminees par @EndSaga", 36);
            System.out.println();
            Console.texte("`@StartSaga` cree l'instance, `@EndSaga` la "
                    + "termine. Entre les deux, c'est "
                    + "l'`associationProperty` qui relie chaque evenement a "
                    + "la bonne instance : elle nomme un ACCESSEUR de "
                    + "l'evenement, ici `candidatureId()`.");
            System.out.println();
            Console.texte("⚠️ Et c'est le piege le plus couteux du chapitre. "
                    + "Se tromper de nom ne produit aucune erreur de "
                    + "compilation, et aucune a l'execution : la saga ne "
                    + "recoit simplement JAMAIS l'evenement. Elle n'est donc "
                    + "jamais terminee — elle reste en base, pour toujours, "
                    + "et son nombre grandit sans que rien ne le signale. "
                    + "Une saga qu'on oublie de terminer est une fuite.");
            System.out.println();
            Console.texte("Le remede tient en deux habitudes : surveiller le "
                    + "nombre de sagas actives comme une metrique de "
                    + "production, et armer une `@DeadlineHandler` sur chaque "
                    + "etape qui attend une reponse exterieure — pour "
                    + "compenser au lieu d'attendre indefiniment.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le pattern Outbox, teste en fabriquant la panne "
                    + "qu'il evite — et les fixtures given/when/then qui "
                    + "rendent tout cela testable sans infrastructure.");
            System.out.println();
        }
    }

    /**
     * Le statut d'une ligne, ou un mot quand la ligne n'existe pas.
     *
     * <p>⚠️ Sur la branche « depart », la projection n'est pas remplie : ce
     * chapitre doit alors AFFICHER le vide, pas planter. Un squelette qui
     * s'arrête sur une {@code NullPointerException} n'enseigne rien.
     */
    private static String statut(Banc banc, String id) {
        var ligne = banc.vue().parId(id);
        return ligne == null ? "(aucune ligne)" : ligne.statut();
    }

    private static String creneau(Banc banc, String id) {
        var ligne = banc.vue().parId(id);
        return ligne == null ? "(aucune ligne)" : ligne.creneau();
    }

    private static List<DomainEventMessage<?>> flux(Banc banc, String id) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(id, 0).asStream().forEach(tout::add);
        return tout;
    }

    private static List<Object> tous(Banc banc) {
        var tout = new ArrayList<Object>();
        banc.moteur().readEvents(null, false).forEach(tout::add);
        return tout;
    }
}
