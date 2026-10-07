package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Candidature;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.PlanifierEntretien;
import java.util.ArrayList;
import java.util.List;
import org.axonframework.commandhandling.GenericCommandMessage;
import org.axonframework.eventhandling.DomainEventMessage;
import org.axonframework.modelling.command.AnnotationCommandTargetResolver;

/**
 * Chapitre 2 — Axon Framework : les bases.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Axon
 * </pre>
 *
 * <p>« Axon fournit le {@code CommandBus}, l'{@code EventStore} et le
 * {@code QueryBus} : la plomberie prête à l'emploi. » Ce chapitre imprime
 * cette plomberie — les classes réellement instanciées — et montre par quoi
 * une commande trouve la bonne instance d'agrégat.
 *
 * <p>Il mesure aussi ce qui arrive quand l'identifiant de routage manque :
 * rien à la compilation, une exception à l'exécution.
 */
public final class Chapitre2Axon {

    private Chapitre2Axon() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            Console.titre(1, "LA PLOMBERIE, EN VRAI");
            Console.ligne("version d'Axon",
                    String.valueOf(DomainEventMessage.class.getPackage()
                            .getImplementationVersion()), 30);
            Console.ligne("bus de commandes", banc.busDeCommandes(), 30);
            Console.ligne("bus d'evenements", banc.busDEvenements(), 30);
            Console.ligne("magasin d'evenements", banc.magasinDEvenements(), 30);
            Console.ligne("passerelle de commandes",
                    banc.passerelle().getClass().getSimpleName(), 30);
            System.out.println();
            Console.sousTitre("Les processeurs d'evenements en place :");
            for (var processeur : banc.processeurs()) {
                Console.texte("→ " + processeur, 5);
            }
            System.out.println();
            Console.texte("Voila ce que le starter Spring Boot aurait "
                    + "assemble pour vous. Ce projet le fait a la main, dans "
                    + "`Banc`, precisement pour que ces noms soient lisibles : "
                    + "un `SimpleCommandBus` qui route par type de commande, "
                    + "un `EmbeddedEventStore` pose sur un moteur de "
                    + "stockage, et un processeur par groupe de handlers.");
            System.out.println();
            Console.texte("⚠️ Ce que cela change pour vos agregats : ils ne "
                    + "portent pas `@Aggregate` ici, et la saga ne porte pas "
                    + "`@Saga`. Ces deux annotations vivent dans "
                    + "`axon-spring` et ne font rien d'autre que declencher "
                    + "`configureAggregate(...)` et `registerSaga(...)`. Le "
                    + "code metier, lui, est identique.");
            System.out.println();
            Console.texte("⚠️ Relisez les deux lignes du milieu : le bus "
                    + "d'evenements et le magasin sont LE MEME OBJET. Ce "
                    + "n'est pas une bizarrerie de configuration — en event "
                    + "sourcing, publier un evenement, c'est l'ecrire. Il n'y "
                    + "a pas un moment ou l'on enregistre puis un moment ou "
                    + "l'on publie ; c'est le meme geste, et c'est ce qui "
                    + "rend le pattern Outbox du chapitre 6 inutile ICI — et "
                    + "indispensable des qu'une base metier classique entre "
                    + "dans le tableau.");

            Console.titre(2, "UNE COMMANDE TROUVE SON AGREGAT PAR SON ID");
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-awa", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-karim", "Karim", "OFF-021"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-awa", "mardi 14h"));
            Console.tableau(List.of("flux d'evenements", "evenements",
                    "contenu"), List.of(
                    ligneDuFlux(banc, "c-awa"),
                    ligneDuFlux(banc, "c-karim")),
                    List.of(20, 14, 32));
            System.out.println();
            Console.texte("Deux identifiants, deux flux separes. La commande "
                    + "`PlanifierEntretien` ne s'est pas trompee de "
                    + "candidature : c'est le `@TargetAggregateIdentifier` "
                    + "qui l'a routee, et le `@AggregateIdentifier` qui a "
                    + "nomme le flux a charger.");
            System.out.println();
            Console.texte("C'est aussi ce que « frontiere de coherence » veut "
                    + "dire concretement : chaque agregat a SON journal, et "
                    + "une commande n'en voit jamais qu'un. Deux candidatures "
                    + "ne se bloquent pas l'une l'autre.");

            Console.titre(3, "CE QUE LE ROUTAGE LIT, EXACTEMENT");
            var resolveur = new AnnotationCommandTargetResolver();
            Console.tableau(List.of("la commande", "cible resolue"), List.of(
                    List.of("PlanifierEntretien",
                            cible(resolveur, new PlanifierEntretien("c-awa",
                                    "mardi 14h"))),
                    List.of("SansCible (meme champ, sans l'annotation)",
                            cible(resolveur, new SansCible("c-awa")))),
                    List.of(42, 32));
            System.out.println();
            Console.texte("Les deux classes ont le MEME champ, portant la "
                    + "MEME valeur. Seule l'annotation change, et elle decide "
                    + "de tout : sans `@TargetAggregateIdentifier`, Axon ne "
                    + "sait pas quel flux d'evenements charger, et il le dit "
                    + "a l'execution. Le compilateur, lui, n'a rien a "
                    + "redire.");
            System.out.println();
            Console.texte("⚠️ Le cas jumeau est plus vicieux : une commande de "
                    + "CREATION, elle, n'a pas besoin de cible — l'agregat "
                    + "n'existe pas encore. `DeposerCandidature` n'a donc "
                    + "aucun `@TargetAggregateIdentifier`, et c'est normal. "
                    + "La regle : creation sans cible, modification avec.");

            Console.titre(4, "CE QUE LE MAGASIN CONTIENT VRAIMENT");
            Console.sousTitre("Le journal du portail, dans l'ordre :");
            int rang = 0;
            for (var message : tousLesEvenements(banc)) {
                Console.texte("%2d. [%s] %s".formatted(++rang,
                        message.getAggregateIdentifier(),
                        message.getPayloadType().getSimpleName()), 5);
            }
            System.out.println();
            Console.ligne("evenements au total", String.valueOf(rang), 30);
            Console.ligne("agregats distincts",
                    String.valueOf(tousLesEvenements(banc).stream()
                            .map(DomainEventMessage::getAggregateIdentifier)
                            .distinct().count()), 30);
            System.out.println();
            Console.texte("Un seul journal, ordonne globalement, ou les flux "
                    + "de chaque agregat s'entrelacent. C'est cette liste que "
                    + "les projections lisent, et c'est elle qu'un nouveau "
                    + "consommateur rejouera depuis le debut.");
            System.out.println();
            Console.texte("⚠️ Et c'est aussi votre journal d'audit, gratuit et "
                    + "incontestable — avec la contrainte qui va avec : on "
                    + "n'y efface rien. Une demande de suppression de donnees "
                    + "personnelles se traite donc par chiffrement des "
                    + "donnees sensibles et destruction de la cle "
                    + "(« crypto-shredding »), pas par un DELETE.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("CQRS : deux projections nourries par le meme "
                    + "journal, et une projection jetee puis reconstruite "
                    + "depuis zero — sans toucher au modele d'ecriture.");
            System.out.println();
        }
    }

    /** Une commande volontairement mal formée : aucune cible de routage. */
    record SansCible(String candidatureId) {
    }

    /** Ce que le résolveur de cible rend — ou l'erreur qu'il lève. */
    private static String cible(AnnotationCommandTargetResolver resolveur,
                                Object commande) {
        try {
            return resolveur.resolveTarget(
                    GenericCommandMessage.asCommandMessage(commande))
                    .getIdentifier();
        } catch (RuntimeException erreur) {
            return erreur.getClass().getSimpleName();
        }
    }

    private static List<String> ligneDuFlux(Banc banc, String id) {
        var types = new ArrayList<String>();
        banc.magasin().readEvents(id).asStream()
                .forEach(m -> types.add(m.getPayloadType().getSimpleName()));
        return List.of(id, String.valueOf(types.size()),
                String.join(", ", types));
    }

    private static List<DomainEventMessage<?>> tousLesEvenements(Banc banc) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(null, false).forEach(message -> {
            if (message instanceof DomainEventMessage<?> domaine) {
                tout.add(domaine);
            }
        });
        return tout;
    }
}
