package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Candidature;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.PlanifierEntretien;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.axonframework.eventhandling.DomainEventMessage;
import org.axonframework.messaging.unitofwork.DefaultUnitOfWork;

/**
 * Chapitre 4 — Event Sourcing.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4EventSourcing
 * </pre>
 *
 * <p>« L'état courant se recalcule en rejouant ses événements. » Ce chapitre
 * <strong>compte</strong> ce rejeu : combien d'événements Axon relit à chaque
 * chargement d'un agrégat, et ce que le chiffre devient une fois un snapshot
 * posé.
 *
 * <p>Il imprime aussi le flux complet d'une candidature — la seule vérité du
 * système — et montre ce qu'un <em>upcaster</em> résout.
 */
public final class Chapitre4EventSourcing {

    private Chapitre4EventSourcing() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            Console.titre(1, "L'ETAT N'EST PAS STOCKE, IL EST CALCULE");
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-awa", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-awa", "mardi 14h"));
            Console.sousTitre("Le flux de la candidature c-awa :");
            int rang = 0;
            for (var message : flux(banc, "c-awa")) {
                Console.texte("%d. seq=%d  %s".formatted(++rang,
                        message.getSequenceNumber(),
                        message.getPayload()), 5);
            }
            System.out.println();
            Console.texte("Voila tout ce que la base contient sur cette "
                    + "candidature. Pas une colonne « statut », pas un champ "
                    + "« entretien planifie » : deux faits, horodates et "
                    + "numerotes. L'etat courant est ce que l'on OBTIENT en "
                    + "les rejouant dans l'ordre.");
            System.out.println();
            Console.texte("Le numero de sequence n'est pas decoratif : c'est "
                    + "lui qui garantit l'ordre a l'interieur d'un agregat, "
                    + "et c'est lui qui detecte un conflit quand deux "
                    + "commandes concurrentes veulent ecrire le meme "
                    + "rang.");

            Console.titre(2, "COMBIEN D'EVENEMENTS REJOUES A CHAQUE APPEL");
            var lignes = new ArrayList<List<String>>();
            for (int tour = 1; tour <= 4; tour++) {
                banc.passerelle().sendAndWait(
                        new PlanifierEntretien("c-awa", "creneau " + tour));
                lignes.add(List.of("apres " + (tour + 2) + " evenements",
                        String.valueOf(flux(banc, "c-awa").size()),
                        String.valueOf(rejouesAuChargement(banc, "c-awa"))));
            }
            Console.tableau(List.of("etat du flux", "evenements stockes",
                    "relus au chargement"), lignes, List.of(24, 22, 22));
            System.out.println();
            Console.texte("Chaque commande recharge l'agregat, et recharger "
                    + "signifie RELIRE tout le flux. Le cout d'une ecriture "
                    + "croit donc avec l'histoire de l'agregat — pas avec la "
                    + "taille de la base, ce qui est deja une bonne nouvelle, "
                    + "mais il croit.");
            System.out.println();
            Console.texte("⚠️ C'est la raison d'etre des snapshots, et c'est "
                    + "aussi un signal de conception : un agregat qui "
                    + "accumule des dizaines de milliers d'evenements est "
                    + "souvent un agregat trop gros. Avant d'ajouter un "
                    + "snapshot, demandez-vous si la frontiere est au bon "
                    + "endroit.");

            Console.titre(3, "CE QU'UN SNAPSHOT CHANGE");
            try (var avecSnapshot = Banc.demarrer(3)) {
                avecSnapshot.passerelle().sendAndWait(
                        new DeposerCandidature("c-snap", "Lea", "OFF-021"));
                for (int tour = 1; tour <= 6; tour++) {
                    avecSnapshot.passerelle().sendAndWait(
                            new PlanifierEntretien("c-snap", "creneau " + tour));
                }
                // Le snapshot est ecrit de facon asynchrone par le
                // `Snapshotter` : on laisse le temps a l'ecriture.
                attendreUnSnapshot(avecSnapshot, "c-snap");
                Console.ligne("seuil de snapshot", "3 evenements", 30);
                Console.ligne("evenements dans le flux",
                        String.valueOf(flux(avecSnapshot, "c-snap").size()), 30);
                Console.ligne("un snapshot existe-t-il",
                        avecSnapshot.moteur().readSnapshot("c-snap")
                                .isPresent() ? "oui" : "non", 32);
                avecSnapshot.moteur().readSnapshot("c-snap").ifPresent(photo ->
                        Console.ligne("photo prise au rang",
                                String.valueOf(photo.getSequenceNumber()), 30));
                Console.ligne("evenements relus au chargement",
                        String.valueOf(rejouesAuChargement(avecSnapshot,
                                "c-snap")), 34);
                Console.ligne("sans snapshot, il en relirait",
                        String.valueOf(flux(avecSnapshot, "c-snap").size()), 34);
                System.out.println();
                Console.texte("Les deux dernieres lignes disent tout. Le "
                        + "journal contient toujours ses evenements — le "
                        + "snapshot n'en a efface aucun — mais Axon repart de "
                        + "la photo et ne rejoue plus que ce qui la suit. "
                        + "C'est une pure optimisation de lecture.");
                System.out.println();
                Console.texte("⚠️ Un snapshot est un etat SERIALISE de votre "
                        + "classe d'agregat. Renommer un champ le rend "
                        + "illisible : Axon le rejette et rejoue tout le "
                        + "flux — c'est le bon comportement, mais c'est une "
                        + "degradation silencieuse de performance. Les "
                        + "snapshots se jettent a chaque changement de "
                        + "structure ; les evenements, jamais.");
            }

            Console.titre(4, "POURQUOI UN EVENEMENT NE SE MODIFIE PAS");
            Console.sousTitre("Ce que le magasin contient reellement pour un "
                    + "evenement :");
            var premier = flux(banc, "c-awa").getFirst();
            Console.ligne("type", premier.getPayloadType().getName(), 22);
            Console.ligne("agregat", premier.getAggregateIdentifier(), 22);
            Console.ligne("rang", String.valueOf(premier.getSequenceNumber()), 22);
            Console.ligne("horodatage", String.valueOf(premier.getTimestamp()), 22);
            Console.ligne("charge utile", String.valueOf(premier.getPayload()), 22);
            System.out.println();
            Console.texte("Le TYPE est stocke sous son nom de classe complet, "
                    + "et la charge utile est serialisee selon la forme "
                    + "qu'avait la classe ce jour-la. Renommer la classe, "
                    + "renommer un champ, en supprimer un : le rejeu de "
                    + "demain retrouvera l'ancienne forme, et devra en faire "
                    + "quelque chose.");
            System.out.println();
            Console.texte("C'est le role des `upcaster` : ils transforment a "
                    + "la volee l'ancien format vers le nouveau AU MOMENT DU "
                    + "REJEU, sans jamais reecrire l'historique. La regle "
                    + "d'or du cours est exacte : on n'edite ni ne supprime "
                    + "un evenement passe, on ajoute et on migre.");
            System.out.println();
            Console.texte("⚠️ Le corollaire est plus dur a avaler : vos "
                    + "classes d'evenements font partie du CONTRAT de "
                    + "persistance, au meme titre qu'un schema de base. Un "
                    + "`record` qu'on refactorise sans y penser casse le "
                    + "rejeu — et le rejeu, c'est le chargement de chaque "
                    + "agregat.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La saga : le chemin heureux, puis la compensation, "
                    + "commande par commande — avec ce qui se passe quand "
                    + "l'agenda dit non.");
            System.out.println();
        }
    }

    /**
     * Le flux BRUT d'un agrégat — tous ses événements, snapshot ignoré.
     *
     * <p>⚠️ La distinction compte. {@code eventStore().readEvents(id)}
     * consulte d'abord le snapshot et ne rend que ce qui le suit : c'est ce
     * qu'Axon relit au chargement, et c'est justement ce que la section 3
     * mesure. Pour voir le journal COMPLET, il faut interroger le moteur de
     * stockage directement — le snapshot n'efface rien, il court-circuite.
     */
    private static List<DomainEventMessage<?>> flux(Banc banc, String id) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(id, 0).asStream().forEach(tout::add);
        return tout;
    }

    /**
     * Le nombre d'événements qu'Axon relit vraiment pour charger l'agrégat.
     *
     * <p>L'agrégat est d'abord chargé par le dépôt d'Axon — celui-là même que
     * le bus de commandes utilise — pour que la mesure porte sur le vrai
     * chemin. Le compte, lui, part du rang du snapshot s'il y en a un.
     */
    private static int rejouesAuChargement(Banc banc, String id) {
        var compte = new AtomicInteger();
        var uow = DefaultUnitOfWork.startAndGet(null);
        try {
            banc.configuration().repository(Candidature.class)
                    .load(id)
                    .execute(agregat -> { });
        } finally {
            uow.commit();
        }
        long depart = banc.moteur().readSnapshot(id)
                .map(photo -> photo.getSequenceNumber() + 1).orElse(0L);
        banc.moteur().readEvents(id, depart).asStream()
                .forEach(message -> compte.incrementAndGet());
        return compte.get();
    }

    /** Le snapshotter écrit de façon asynchrone : on lui laisse le temps. */
    private static void attendreUnSnapshot(Banc banc, String id) {
        for (int essai = 0; essai < 50; essai++) {
            if (banc.moteur().readSnapshot(id).isPresent()) {
                return;
            }
            try {
                Thread.sleep(20);
            } catch (InterruptedException interrompu) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }
}
