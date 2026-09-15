package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Candidature;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DecisionPrononcee;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.EntretienPlanifie;
import fr.portail.domaine.Messages.PlanifierEntretien;
import java.util.ArrayList;
import java.util.List;
import org.axonframework.eventhandling.DomainEventMessage;
import org.axonframework.test.aggregate.AggregateTestFixture;

/**
 * Chapitre 6 — Le projet complet.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Projet
 * </pre>
 *
 * <p>« Un agrégat se teste comme une fonction pure : given / when / then. »
 * Ce chapitre fait tourner ces fixtures <strong>devant vous</strong>, y
 * compris un scénario qui échoue, pour montrer ce que l'erreur dit.
 *
 * <p>Il fabrique ensuite la panne que le pattern Outbox évite, mesure ce
 * qu'elle perd, puis mesure ce que la même séquence donne avec l'outbox.
 */
public final class Chapitre6Projet {

    private Chapitre6Projet() {
    }

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "UN AGREGAT SE TESTE SANS BASE NI BUS");
        var fixture = new AggregateTestFixture<>(Candidature.class);
        String scenarioSimple = essai(() -> fixture
                .givenNoPriorActivity()
                .when(new DeposerCandidature("c-1", "Awa", "OFF-014"))
                .expectEvents(new CandidatureDeposee("c-1", "Awa", "OFF-014")));
        String scenarioPasse = essai(() -> fixture
                .given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                        new EntretienPlanifie("c-1", "mardi 14h"))
                .when(new Decider("c-1", true, "excellent profil"))
                .expectEvents(new DecisionPrononcee("c-1", true,
                        "excellent profil")));
        String scenarioRefus = essai(() -> fixture
                .given(new CandidatureDeposee("c-1", "Awa", "OFF-014"))
                .when(new Decider("c-1", true, "excellent profil"))
                .expectException(IllegalStateException.class));
        Console.tableau(List.of("le scenario", "verdict"), List.of(
                List.of("depot d'une candidature", scenarioSimple),
                List.of("decision apres un entretien", scenarioPasse),
                List.of("decision SANS entretien -> refus", scenarioRefus)),
                List.of(38, 24));
        System.out.println();
        Console.texte("Trois scenarios metier, lisibles comme des phrases, "
                + "et pas une seule ligne d'infrastructure : ni base, ni "
                + "broker, ni conteneur. C'est l'event sourcing qui rend "
                + "cela possible — un agregat est une fonction du passe vers "
                + "des faits, donc il se teste comme une fonction.");
        System.out.println();
        Console.texte("Le `given` n'est pas un jeu de donnees : ce sont des "
                + "EVENEMENTS, c'est-a-dire l'histoire exacte qu'on veut "
                + "rejouer. On decrit un passe, on envoie une intention, on "
                + "affirme des faits.");

        Console.titre(2, "CE QUE DIT UNE FIXTURE QUAND ON SE TROMPE");
        String mauvais;
        try {
            fixture.given(new CandidatureDeposee("c-1", "Awa", "OFF-014"),
                            new EntretienPlanifie("c-1", "mardi 14h"))
                    .when(new Decider("c-1", true, "excellent profil"))
                    .expectEvents(new DecisionPrononcee("c-1", false, "refuse"));
            mauvais = "passe (ce qui serait un probleme)";
        } catch (Throwable erreur) {
            mauvais = erreur.getMessage();
        }
        Console.sousTitre("Un test volontairement faux :");
        Console.bloc(mauvais, 6);
        System.out.println();
        Console.texte("L'erreur nomme le champ qui differe, et donne les deux "
                + "valeurs. C'est ce qui fait la valeur de ces fixtures en "
                + "pratique : quand un test casse, on sait en une ligne ce "
                + "qui a change dans le comportement metier.");

        Console.titre(3, "LE CORRELATION ID VOYAGE TOUT SEUL");
        try (var banc = Banc.demarrerAvecSaga()) {
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-trace", "Awa", "OFF-014"));
            var evenements = tous(banc);
            var lignes = new ArrayList<List<String>>();
            for (var message : evenements) {
                lignes.add(List.of(message.getPayloadType().getSimpleName(),
                        String.valueOf(message.getMetaData()
                                .get("correlationId")).substring(0, 8),
                        String.valueOf(message.getMetaData().get("traceId"))
                                .substring(0, 8)));
            }
            Console.tableau(List.of("evenement", "correlationId", "traceId"),
                    lignes, List.of(26, 18, 18));
            System.out.println();
            Console.ligne("evenements produits",
                    String.valueOf(evenements.size()), 30);
            Console.ligne("traceId distincts",
                    String.valueOf(evenements.stream()
                            .map(m -> m.getMetaData().get("traceId"))
                            .distinct().count()), 30);
            System.out.println();
            Console.texte("Une seule commande de l'exterieur, trois "
                    + "evenements produits par deux agregats differents — et "
                    + "un SEUL `traceId`. Axon l'a propage de message en "
                    + "message, a travers la saga et les commandes qu'elle a "
                    + "envoyees, sans qu'une ligne de code s'en occupe.");
            System.out.println();
            Console.texte("C'est ce que le cours appelle le tracing "
                    + "distribue, et c'est ce qui rend un systeme "
                    + "evenementiel debogable : on retrouve le parcours "
                    + "complet d'une candidature en filtrant sur un "
                    + "identifiant. Le `correlationId`, lui, designe le "
                    + "message PARENT immediat — d'ou des valeurs "
                    + "differentes.");

            Console.titre(4, "LE RETARD D'UN CONSOMMATEUR, MESURE");
            // ⚠️ On ne compare pas au journal ENTIER : la vue ne s'abonne
            // qu'aux evenements de candidature, et compter les evenements
            // d'agenda ferait apparaitre un retard imaginaire. Le « lag »
            // d'un consommateur se mesure sur CE QU'IL DOIT TRAITER.
            int pourLaVue = (int) tous(banc).stream()
                    .filter(m -> m.getPayload() instanceof CandidatureDeposee
                            || m.getPayload() instanceof EntretienPlanifie
                            || m.getPayload() instanceof DecisionPrononcee
                            || m.getPayload() instanceof
                                    fr.portail.domaine.Messages.CandidatureAnnulee)
                    .count();
            int traitesParLaVue = banc.vue().evenementsRecus();
            banc.vue().vider();
            Console.tableau(List.of("moment", "a traiter", "traites",
                    "retard"), List.of(
                    List.of("en regime normal", String.valueOf(pourLaVue),
                            String.valueOf(traitesParLaVue),
                            String.valueOf(pourLaVue - traitesParLaVue)),
                    List.of("apres une remise a zero",
                            String.valueOf(pourLaVue), "0",
                            String.valueOf(pourLaVue))),
                    List.of(26, 14, 14, 12));
            System.out.println();
            Console.texte("Le retard d'un consommateur — son « lag » — est "
                    + "la difference entre ce que le journal contient et ce "
                    + "qu'il a traite. C'est la metrique numero un d'un "
                    + "systeme evenementiel : tant qu'elle revient a zero, "
                    + "tout va bien ; si elle monte sans redescendre, un "
                    + "consommateur est en panne ou trop lent.");
            System.out.println();
            Console.texte("⚠️ Le retard ne se voit pas dans les journaux "
                    + "applicatifs et ne leve aucune alerte tout seul : un "
                    + "consommateur en retard REPOND normalement, avec des "
                    + "donnees vieilles. C'est precisement pour cela qu'on la "
                    + "mesure. Les deux autres a surveiller : le taux "
                    + "d'echec, et ce qui part en file de messages morts.");
        }

        Console.titre(5, "LE PATTERN OUTBOX, ET LA PANNE QU'IL EVITE");
        var sansOutbox = new ServiceSansOutbox();
        String panne = sansOutbox.enregistrer("c-42", true);
        var avecOutbox = new ServiceAvecOutbox();
        String protege = avecOutbox.enregistrer("c-42", true);
        Console.tableau(List.of("le service", "ligne en base",
                "evenement publie", "resultat"), List.of(
                List.of("sans outbox", String.valueOf(sansOutbox.enBase()),
                        String.valueOf(sansOutbox.publies()), panne),
                List.of("avec outbox", String.valueOf(avecOutbox.enBase()),
                        String.valueOf(avecOutbox.publies()), protege)),
                List.of(18, 16, 20, 20));
        System.out.println();
        Console.texte("La panne est fabriquee au pire endroit : APRES "
                + "l'ecriture en base, AVANT la publication. Sans outbox, la "
                + "ligne existe et personne n'est prevenu — c'est un "
                + "evenement PERDU, et il ne reviendra jamais. La base et le "
                + "reste du systeme divergent pour toujours.");
        System.out.println();
        Console.texte("Avec l'outbox, l'evenement est ecrit dans la MEME "
                + "transaction que la donnee metier. La panne peut survenir "
                + "juste apres : au redemarrage, le relais lit la table, "
                + "trouve l'evenement non publie, et l'envoie. « Donnee "
                + "modifiee » et « evenement emis » redeviennent atomiques.");
        System.out.println();
        Console.texte("⚠️ Et voici ce que ce projet a de particulier : il n'a "
                + "PAS besoin d'outbox. En event sourcing sur un magasin "
                + "unique, publier un evenement et l'ecrire sont le meme "
                + "geste — le chapitre 2 le montrait, le bus d'evenements et "
                + "le magasin sont le meme objet. L'outbox devient "
                + "indispensable des qu'un service garde une base metier "
                + "CLASSIQUE a cote du bus, ce qui est le cas le plus "
                + "frequent en microservices.");
        System.out.println();
        Console.texte("⚠️ Le relais, lui, publie en at-least-once : s'il tombe "
                + "entre l'envoi et la marque « publie », il renverra le "
                + "message. On retombe donc sur le contrat du chapitre 1 — "
                + "les consommateurs doivent etre idempotents. L'outbox "
                + "garantit qu'on ne PERD rien ; elle ne garantit pas qu'on "
                + "n'envoie qu'une fois.");

        Console.titre(6, "CE QUE CE PROJET NE PROUVE PAS");
        Console.texte("Aucun Axon Server, aucun Kafka, aucune base : les "
                + "evenements vivent dans un `InMemoryEventStorageEngine`. "
                + "Ce qui est mesure — les invariants, le rejeu, les "
                + "snapshots, la saga, la correlation — est identique en "
                + "production ; ce qui ne l'est pas, c'est tout ce qui vient "
                + "du reseau.");
        System.out.println();
        Console.texte("En particulier : les processeurs de ce projet sont en "
                + "mode SUBSCRIBING, donc la fenetre de coherence a terme y "
                + "est nulle. Le debit, la latence, le partitionnement, la "
                + "reprise apres panne d'un consommateur et le comportement "
                + "d'un cluster ne sont pas mesures ici. Ce sont des "
                + "proprietes de l'infrastructure, et elles demandent "
                + "l'infrastructure.");
        System.out.println();
    }

    /** Exécute une fixture et rend « passe », ou l'erreur en une ligne. */
    private static String essai(Runnable scenario) {
        try {
            scenario.run();
            return "passe";
        } catch (Throwable erreur) {
            return court(erreur.getMessage());
        }
    }

    private static List<DomainEventMessage<?>> tous(Banc banc) {
        var tout = new ArrayList<DomainEventMessage<?>>();
        banc.moteur().readEvents(null, false).forEach(message -> {
            if (message instanceof DomainEventMessage<?> domaine) {
                tout.add(domaine);
            }
        });
        return tout;
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 22 ? plat : plat.substring(0, 19) + "...";
    }

    /**
     * Un service qui écrit en base, puis publie — et qui tombe entre les
     * deux.
     *
     * <p>La panne est forcée, pas aléatoire : ce chapitre doit donner le même
     * résultat à chaque exécution.
     */
    private static final class ServiceSansOutbox {

        private final List<String> base = new ArrayList<>();
        private final List<String> bus = new ArrayList<>();

        String enregistrer(String id, boolean panne) {
            base.add(id);
            if (panne) {
                return "evenement PERDU";
            }
            bus.add(id);
            return "publie";
        }

        int enBase() {
            return base.size();
        }

        int publies() {
            return bus.size();
        }
    }

    /**
     * Le même service, avec une table outbox — et un relais qui rattrape.
     *
     * <p>Le point capital tient en une ligne : {@link #enregistrer} écrit la
     * donnée <em>et</em> l'événement dans la même « transaction ». Le relais
     * publie ensuite, et marque. Une panne entre les deux ne perd rien : au
     * redémarrage, le relais retrouve l'événement non publié.
     */
    private static final class ServiceAvecOutbox {

        private final List<String> base = new ArrayList<>();
        private final List<String> outbox = new ArrayList<>();
        private final List<String> bus = new ArrayList<>();

        String enregistrer(String id, boolean panne) {
            // Une seule transaction : la donnee ET l'evenement.
            base.add(id);
            outbox.add(id);
            if (panne) {
                // Le service tombe ici. L'evenement n'est pas publie... mais
                // il est ECRIT. Au redemarrage, le relais le retrouve.
                relayer();
                return "rattrape au redemarrage";
            }
            relayer();
            return "publie";
        }

        private void relayer() {
            for (var id : List.copyOf(outbox)) {
                bus.add(id);
                outbox.remove(id);
            }
        }

        int enBase() {
            return base.size();
        }

        int publies() {
            return bus.size();
        }
    }
}
