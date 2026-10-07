package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.services.OffresService;
import java.time.Duration;
import java.util.List;

/**
 * Chapitre 1 — Du monolithe aux microservices.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Decoupage
 * </pre>
 *
 * <p>« Le prix est réel — latence réseau, cohérence distribuée, complexité
 * opérationnelle. » Ce chapitre <strong>chiffre</strong> le premier de ces
 * prix : le même travail, appelé en mémoire puis par HTTP, sur la boucle
 * locale — c'est-à-dire dans les conditions les plus favorables qui soient.
 *
 * <p>Il mesure ensuite ce que le découpage achète : un service tombe, l'autre
 * répond toujours.
 */
public final class Chapitre1Decoupage {

    private Chapitre1Decoupage() {
    }

    private static final int APPELS = 300;

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.avecInstances(1)) {
            int port = banc.portsDesInstances().getFirst();
            String url = "http://localhost:" + port + "/offres";
            Banc.attendre(() -> Banc.get(url).code() == 200,
                    Duration.ofSeconds(30));

            Console.titre(1, "CE QUE COUTE UN APPEL RESEAU");
            // L'appel « monolithe » : la meme methode, dans la meme JVM.
            var service = new OffresService(new org.springframework.core.env
                    .StandardEnvironment());
            long enMemoire = chronometrer(() -> service.offres());
            long parHttp = chronometrer(() -> Banc.get(url));
            Console.tableau(List.of("comment on appelle", "appels",
                    "duree totale", "par appel"), List.of(
                    List.of("en memoire (monolithe)", String.valueOf(APPELS),
                            enMemoire / 1_000_000 + " ms",
                            "%.3f ms".formatted(enMemoire / 1e6 / APPELS)),
                    List.of("par HTTP (microservice)", String.valueOf(APPELS),
                            parHttp / 1_000_000 + " ms",
                            "%.3f ms".formatted(parHttp / 1e6 / APPELS))),
                    List.of(26, 10, 16, 14));
            Console.ligne("rapport", "x" + Math.max(1,
                    parHttp / Math.max(1, enMemoire)), 26);
            System.out.println();
            Console.texte("Le meme travail, et un rapport qui se compte en "
                    + "ordres de grandeur — sur la BOUCLE LOCALE, sans "
                    + "serialisation lourde, sans reseau physique, sans TLS. "
                    + "C'est le plancher absolu du cout d'un appel entre "
                    + "services.");
            System.out.println();
            Console.texte("⚠️ En production, ajoutez le reseau, le TLS, la "
                    + "traversee d'une passerelle, et la latence de queue — "
                    + "celle du centile 99, qui est celle que vos "
                    + "utilisateurs ressentent. Un ecran qui enchaine cinq "
                    + "appels entre services paie cinq fois ce prix, en "
                    + "serie.");
            System.out.println();
            Console.texte("C'est pourquoi le cours a raison d'ecrire que le "
                    + "microservice « n'est pas un objectif, c'est un "
                    + "compromis ». On ne decoupe pas pour la beaute du "
                    + "schema : on decoupe quand une equipe ou une charge le "
                    + "justifie, et on paie cette facture en connaissance de "
                    + "cause.");

            Console.titre(2, "CE QUE LE DECOUPAGE ACHETE VRAIMENT");
            int second = banc.ajouterUneInstance();
            String urlSecond = "http://localhost:" + second + "/offres";
            Banc.attendre(() -> Banc.get(urlSecond).code() == 200,
                    Duration.ofSeconds(30));
            Console.ligne("instances en vie", "2", 30);
            banc.tuerLInstance(port);
            var morte = Banc.get(url);
            var vivante = Banc.get(urlSecond);
            Console.tableau(List.of("l'instance", "etat", "reponse HTTP"),
                    List.of(
                    List.of("port " + port, "arretee",
                            morte.code() == 0 ? "aucune connexion"
                                    : String.valueOf(morte.code())),
                    List.of("port " + second, "en vie",
                            String.valueOf(vivante.code()))),
                    List.of(16, 14, 22));
            System.out.println();
            Console.texte("Une instance disparait, l'autre continue. C'est le "
                    + "deploiement independant que le cours promet, et il est "
                    + "reel — mais notez la nuance : ce qui continue, c'est "
                    + "le MEME service sur une autre instance.");
            System.out.println();
            Console.texte("⚠️ Le vrai test de l'independance est ailleurs : "
                    + "que se passe-t-il pour l'APPELANT ? Si le service des "
                    + "candidatures appelle celui des offres en synchrone et "
                    + "que celui-ci tombe, l'appelant tombe avec lui — sauf "
                    + "s'il a un disjoncteur et un repli. C'est exactement "
                    + "l'objet du chapitre 3, et c'est ce qui fait la "
                    + "difference entre « des services separes » et « un "
                    + "systeme resilient ».");

            Console.titre(3, "CHAQUE SERVICE POSSEDE SES DONNEES");
            Console.ligne("routes exposees par le service",
                    "/offres, /qui, /panne", 34);
            Console.ligne("acces direct a ses donnees", "aucun", 34);
            System.out.println();
            Console.texte("Il n'y a pas de mesure spectaculaire a faire ici, "
                    + "et c'est justement le point : la seule porte d'entree "
                    + "du service des offres est son API HTTP. Aucun autre "
                    + "service ne peut lire sa base, parce qu'il n'y a aucun "
                    + "chemin pour le faire.");
            System.out.println();
            Console.texte("C'est la regle la plus simple a enoncer et la plus "
                    + "facile a violer : « un service ne lit jamais "
                    + "directement la base d'un autre ». La violer donne un "
                    + "monolithe distribue — tous les inconvenients du "
                    + "reseau, aucun des avantages du decouplage, et un "
                    + "schema de base que personne ne peut plus faire "
                    + "evoluer.");
            System.out.println();
            Console.texte("Le corollaire est le decoupage par BOUNDED "
                    + "CONTEXT : « offres », « candidatures », "
                    + "« notifications » — jamais « service de base de "
                    + "donnees » et « service de logique ». Un decoupage "
                    + "technique multiplie les appels reseau mesures plus "
                    + "haut sans rien decoupler du tout.");

            Console.titre(4, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("L'annuaire : ce qu'Eureka contient vraiment, "
                    + "combien de temps un service met a y apparaitre, et "
                    + "combien de temps une instance morte y reste.");
            System.out.println();
        }
    }

    /** Le temps total de {@link #APPELS} appels, en nanosecondes. */
    private static long chronometrer(Runnable appel) {
        // Une mise en jambe : la premiere requete HTTP paie l'ouverture de
        // connexion, et le JIT n'a encore rien compile.
        for (int i = 0; i < 20; i++) {
            appel.run();
        }
        long debut = System.nanoTime();
        for (int i = 0; i < APPELS; i++) {
            appel.run();
        }
        return System.nanoTime() - debut;
    }
}
