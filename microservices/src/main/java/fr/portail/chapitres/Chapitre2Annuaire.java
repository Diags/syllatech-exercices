package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.services.OffresService;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 2 — Spring Cloud : les fondations.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Annuaire
 * </pre>
 *
 * <p>« Un service demande "donne-moi candidatures-service" et reçoit la liste
 * des instances vivantes. » Ce chapitre interroge l'annuaire
 * <strong>directement</strong>, par son API REST, et imprime ce qu'il
 * contient.
 *
 * <p>Il chronomètre ensuite les deux délais qui surprennent tout le monde en
 * production : celui d'apparition d'un service, et celui de disparition d'une
 * instance morte.
 */
public final class Chapitre2Annuaire {

    private Chapitre2Annuaire() {
    }

    public static void main(String[] args) {
        Console.utf8();

        long depart = System.currentTimeMillis();
        try (var banc = Banc.avecInstances(2)) {
            String annuaire = banc.urlEureka() + "/eureka/apps";

            Console.titre(1, "CE QUE L'ANNUAIRE CONTIENT");
            boolean vues = Banc.attendre(
                    () -> instances(annuaire) >= 2, Duration.ofSeconds(60));
            long delai = System.currentTimeMillis() - depart;
            Console.ligne("le serveur Eureka", banc.urlEureka(), 26);
            Console.ligne("instances demarrees", "2", 26);
            Console.ligne("instances enregistrees",
                    String.valueOf(instances(annuaire)), 26);
            Console.ligne("depuis le demarrage du banc", delai + " ms", 32);
            Console.ligne("tout est-il la", vues ? "oui" : "NON", 26);
            System.out.println();
            Console.sousTitre("La reponse brute de l'annuaire :");
            Console.bloc(extraire(Banc.get(annuaire).corps()), 6);
            System.out.println();
            Console.texte("L'application est enregistree sous "
                    + "OFFRES-SERVICE — en MAJUSCULES. C'est "
                    + "`spring.application.name` qui a donne ce nom, et c'est "
                    + "la clef de tout : Eureka l'enregistre ainsi, le "
                    + "Config Server sert `offres-service.yml`, et la "
                    + "passerelle ecrit `lb://offres-service`. Un nom, trois "
                    + "services rendus.");
            System.out.println();
            Console.texte("⚠️ Deux instances de la MEME application "
                    + "apparaissent parce qu'elles ont des "
                    + "`instance-id` distincts. Sur une meme machine, le "
                    + "defaut les nomme identiquement — et l'annuaire n'en "
                    + "voit alors qu'UNE, la seconde ecrasant la premiere. "
                    + "C'est un des pieges les plus frequents en "
                    + "developpement local.");

            Console.titre(2, "LES DELAIS PAR DEFAUT, ET CEUX D'ICI");
            Console.tableau(List.of("reglage", "defaut Eureka", "ce banc"),
                    List.of(
                    List.of("intervalle de battement", "30 s", "1 s"),
                    List.of("expiration d'un bail", "90 s", "2 s"),
                    List.of("rafraichissement client", "30 s", "1 s"),
                    List.of("balayage des expires", "60 s", "1 s"),
                    List.of("auto-preservation", "activee", "coupee")),
                    List.of(26, 16, 12));
            System.out.println();
            Console.texte("Avec les valeurs par defaut, un service met "
                    + "jusqu'a une minute a devenir visible des autres, et "
                    + "une instance morte reste annoncee pendant QUATRE-VINGT "
                    + "DIX SECONDES. Ce n'est pas un defaut : c'est un choix "
                    + "de robustesse — un hoquet reseau ne doit pas vider "
                    + "l'annuaire.");
            System.out.println();
            Console.texte("⚠️ Mais cela veut dire qu'entre le moment ou une "
                    + "instance meurt et celui ou l'annuaire l'oublie, les "
                    + "appelants recoivent SON ADRESSE. La decouverte ne "
                    + "remplace donc pas le disjoncteur du chapitre 3 : elle "
                    + "dit qui existe, pas qui repond.");
            System.out.println();
            Console.texte("⚠️ Et l'auto-preservation merite sa ligne. Quand "
                    + "trop de battements manquent a l'appel, Eureka refuse "
                    + "d'evincer quoi que ce soit — il prefere annoncer des "
                    + "instances mortes qu'en oublier des vivantes. Sur un "
                    + "annuaire de trois instances, cela signifie qu'il "
                    + "n'evince plus jamais rien. D'ou la ligne « coupee » "
                    + "ici.");

            Console.titre(3, "L'EQUILIBRAGE DE CHARGE, COMPTE INSTANCE PAR INSTANCE");
            OffresService.remettreAZero();
            var ports = banc.portsDesInstances();
            for (int appel = 0; appel < 20; appel++) {
                Banc.get("http://localhost:" + ports.get(appel % ports.size())
                         + "/qui");
            }
            var lignes = new ArrayList<List<String>>();
            OffresService.servies().forEach((port, compteur) ->
                    lignes.add(List.of("instance " + port,
                            String.valueOf(compteur.get()))));
            lignes.sort((a, b) -> a.get(0).compareTo(b.get(0)));
            Console.tableau(List.of("qui a repondu", "requetes servies"),
                    lignes, List.of(24, 20));
            System.out.println();
            Console.texte("Vingt requetes, deux instances, dix chacune. "
                    + "Ici la repartition est faite par le chapitre "
                    + "lui-meme, a la main : ce qui est mesure est que "
                    + "CHAQUE instance repond vraiment, et qu'on sait le "
                    + "verifier. La repartition automatique, celle de "
                    + "`lb://`, est mesuree au chapitre 3 — a travers la "
                    + "passerelle, qui est l'endroit ou elle sert.");

            Console.titre(4, "CE QU'UNE INSTANCE MORTE LAISSE DERRIERE ELLE");
            int victime = ports.getFirst();
            banc.tuerLInstance(victime);
            long mort = System.currentTimeMillis();
            boolean oubliee = Banc.attendre(() -> instances(annuaire) <= 1,
                    Duration.ofSeconds(30));
            Console.ligne("instance arretee", "port " + victime, 30);
            Console.ligne("oubliee par l'annuaire",
                    oubliee ? "oui" : "NON (delai depasse)", 30);
            Console.ligne("temps d'oubli",
                    (System.currentTimeMillis() - mort) + " ms", 30);
            Console.ligne("instances restantes",
                    String.valueOf(instances(annuaire)), 30);
            System.out.println();
            Console.texte("Avec les reglages de ce banc, l'oubli prend moins "
                    + "d'une seconde. Avec les defauts, il prendrait jusqu'a "
                    + "quatre-vingt-dix secondes — pendant lesquelles "
                    + "l'annuaire donne une adresse qui ne repond plus.");
            System.out.println();
            Console.texte("C'est la raison pour laquelle l'equilibrage cote "
                    + "client et le disjoncteur sont complementaires : le "
                    + "premier repartit entre les adresses connues, le second "
                    + "cesse d'appeler celles qui ne repondent pas. Aucun des "
                    + "deux ne suffit seul.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La passerelle : une seule porte d'entree, un "
                    + "chemin reecrit, et un disjoncteur qu'on regarde "
                    + "s'ouvrir puis se refermer.");
            System.out.println();
        }
    }

    /** Le nombre d'instances enregistrées, lu dans la réponse d'Eureka. */
    private static int instances(String annuaire) {
        var reponse = Banc.get(annuaire);
        if (reponse.code() != 200) {
            return 0;
        }
        // La reponse XML d'Eureka liste une balise <instance> par instance.
        int compte = 0;
        int position = 0;
        while ((position = reponse.corps().indexOf("<instance>", position)) >= 0) {
            compte++;
            position += 10;
        }
        return compte;
    }

    /** Les lignes intéressantes de la réponse d'Eureka, sans le bruit XML. */
    private static String extraire(String xml) {
        var garde = new StringBuilder();
        for (var ligne : xml.split("\n")) {
            String propre = ligne.strip();
            if (propre.startsWith("<name>") || propre.startsWith("<instanceId>")
                    || propre.startsWith("<status>")
                    || propre.startsWith("<port")) {
                garde.append(propre).append("\n");
            }
        }
        return garde.isEmpty() ? xml.substring(0, Math.min(400, xml.length()))
                : garde.toString();
    }
}
