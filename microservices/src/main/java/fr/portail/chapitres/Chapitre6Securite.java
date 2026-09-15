package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.passerelle.Passerelle;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.List;

/**
 * Chapitre 6 — Sécurité et observabilité.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Securite
 * </pre>
 *
 * <p>« La gateway centralise routage, auth, rate limiting et journalisation en
 * un point. » Ce chapitre envoie trois requêtes — sans jeton, avec un jeton
 * mal formé, avec un bon jeton — et mesure ce que chacune obtient.
 *
 * <p>Il pose surtout la question que le schéma d'architecture ne pose
 * jamais : <strong>et si on contourne la passerelle ?</strong>
 */
public final class Chapitre6Securite {

    private Chapitre6Securite() {
    }

    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5)).build();

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.complet(1)) {
            String protegee = banc.urlPasserelle() + "/api/prive/entetes";
            Banc.attendre(() -> avec(protegee, "Bearer jeton-valide")
                    .code() == 200, Duration.ofSeconds(60));
            Passerelle.remettreAZero();

            Console.titre(1, "LE CONTROLE EST A LA PORTE, PAS DANS LE SERVICE");
            Console.tableau(List.of("la requete", "code", "reponse"), List.of(
                    reponse("sans en-tete", avec(protegee, null)),
                    reponse("avec « Basic abc »", avec(protegee, "Basic abc")),
                    reponse("avec « Bearer ... »",
                            avec(protegee, "Bearer jeton-valide"))),
                    List.of(24, 8, 38));
            System.out.println();
            Console.ligne("requetes refusees a la passerelle",
                    String.valueOf(Passerelle.refus()), 38);
            System.out.println();
            Console.texte("Deux requetes sur trois n'ont jamais atteint le "
                    + "service : elles se sont arretees a la porte. C'est "
                    + "l'argument central de la passerelle — un seul endroit "
                    + "ou poser l'authentification, la limitation de debit et "
                    + "la journalisation, au lieu de les repeter dans chaque "
                    + "service et d'en oublier un.");

            Console.titre(2, "ET SI ON CONTOURNE LA PASSERELLE ?");
            int portDirect = banc.portsDesInstances().getFirst();
            var directe = Banc.get("http://localhost:" + portDirect
                                   + "/entetes");
            Console.tableau(List.of("le chemin", "code", "ce que le service voit"),
                    List.of(
                    List.of("par la passerelle, sans jeton",
                            String.valueOf(avec(protegee, null).code()),
                            "rien : la requete est refusee"),
                    List.of("en direct, sans jeton",
                            String.valueOf(directe.code()),
                            court(directe.corps(), 30))),
                    List.of(30, 8, 32));
            System.out.println();
            Console.texte("⚠️ Le service repond. Sans jeton, sans "
                    + "verification, a qui sait son adresse. La passerelle "
                    + "n'est PAS une frontiere de securite : c'est un point "
                    + "de passage commode, et rien de plus, tant que le "
                    + "reseau ne l'impose pas.");
            System.out.println();
            Console.texte("C'est ce qu'on appelle la securite en profondeur, "
                    + "et cela se joue a trois niveaux : le RESEAU — les "
                    + "services ne sont joignables que depuis la passerelle, "
                    + "par une politique reseau Kubernetes ou un maillage de "
                    + "services ; le SERVICE — il valide lui aussi le jeton "
                    + "qu'on lui transmet ; et la PASSERELLE, qui filtre le "
                    + "gros du trafic.");
            System.out.println();
            Console.texte("Un schema d'architecture ou toutes les fleches "
                    + "passent par la passerelle ne dit rien de ce qui se "
                    + "passe quand quelqu'un trace une fleche de plus.");

            Console.titre(3, "UN IDENTIFIANT QUI TRAVERSE TOUT LE SYSTEME");
            var premiere = avec(protegee, "Bearer jeton-valide");
            var seconde = avec(protegee, "Bearer jeton-valide");
            Console.sousTitre("Ce que le service a recu, requete par requete :");
            Console.bloc(premiere.corps(), 6);
            Console.bloc(seconde.corps(), 6);
            System.out.println();
            Console.ligne("identifiants differents",
                    premiere.corps().equals(seconde.corps()) ? "NON" : "oui",
                    30);
            Console.ligne("le jeton est-il relaye au service",
                    premiere.corps().contains("\"Authorization\":\"(present)\"")
                            ? "oui" : "non", 36);
            System.out.println();
            Console.texte("La passerelle a pose un `X-Request-Id` different "
                    + "sur chaque requete, et le service l'a recu. C'est le "
                    + "fil qu'on suivra dans les journaux de TOUS les "
                    + "services pour reconstituer le parcours d'une requete "
                    + "— exactement ce que le cours appelle le tracing "
                    + "distribue.");
            System.out.println();
            Console.texte("⚠️ Et remarquez la derniere ligne : le jeton, lui, "
                    + "est relaye tel quel. C'est un choix, et il doit etre "
                    + "conscient. Le relayer permet au service de verifier "
                    + "lui-meme l'identite — securite en profondeur ; ne pas "
                    + "le relayer oblige a faire confiance a la passerelle "
                    + "pour tout. Ce qu'on ne veut jamais, c'est le relayer "
                    + "SANS que personne ne le verifie ensuite.");

            Console.titre(4, "CE QUE L'ACTUATOR SAIT DEJA");
            var sante = Banc.get(banc.urlPasserelle() + "/actuator/health");
            var disjoncteurs = Banc.get(banc.urlPasserelle()
                                        + "/actuator/circuitbreakers");
            Console.ligne("etat de la passerelle",
                    court(sante.corps(), 40), 30);
            Console.ligne("disjoncteurs exposes",
                    disjoncteurs.code() == 200 ? "oui" : "non", 30);
            Console.sousTitre("Les disjoncteurs, vus de l'exterieur :");
            Console.bloc(court(disjoncteurs.corps(), 300), 6);
            System.out.println();
            Console.texte("Ces points de terminaison ne coutent rien a "
                    + "activer et disent l'essentiel : l'etat de "
                    + "l'application, et celui de chaque disjoncteur. Ce sont "
                    + "eux que Kubernetes interroge pour ses sondes — le "
                    + "chapitre 5 montrait les chemins "
                    + "`/actuator/health/liveness` et `readiness`.");
            System.out.println();
            Console.texte("⚠️ Un point de vigilance qui n'est pas dans le "
                    + "cours : l'actuator expose aussi `/env`, `/beans`, "
                    + "`/configprops`, `/heapdump`… Exposer tout le groupe "
                    + "`*` sur un port public revient a publier votre "
                    + "configuration, variables d'environnement comprises. On "
                    + "n'expose que ce dont on a besoin, et de preference sur "
                    + "un port separe.");

            Console.titre(5, "CE QUI RESTE A FAIRE, ET QUE CE PROJET NE FAIT PAS");
            Console.texte("La limitation de debit. Elle se pose au meme "
                    + "endroit — un filtre de passerelle — et protege les "
                    + "services d'un afflux, legitime ou non. Elle demande un "
                    + "compteur PARTAGE entre les instances de la passerelle, "
                    + "d'ou l'usage courant de Redis.");
            System.out.println();
            Console.texte("La validation d'un vrai JWT, signature comprise, "
                    + "contre le JWKS d'un fournisseur d'identite. C'est "
                    + "l'objet du cours Spring Security, et il y a beaucoup a "
                    + "en dire — a commencer par le fait qu'un jeton "
                    + "d'acces ne se revoque pas.");
            System.out.println();
            Console.texte("Le tracing distribue complet — un `traceId` propage "
                    + "automatiquement, des spans, un collecteur. "
                    + "`X-Request-Id` pose a la main, comme ici, en est la "
                    + "version pauvre : il traverse, mais il ne mesure rien. "
                    + "Micrometer Tracing et OpenTelemetry font le reste.");
            System.out.println();
        }
    }

    private static List<String> reponse(String quoi, Banc.Reponse reponse) {
        return List.of(quoi, String.valueOf(reponse.code()),
                court(reponse.corps(), 36));
    }

    /** Un GET avec, ou sans, en-tête d'autorisation. */
    private static Banc.Reponse avec(String url, String autorisation) {
        var construction = HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10)).GET();
        if (autorisation != null) {
            construction.header("Authorization", autorisation);
        }
        try {
            var reponse = CLIENT.send(construction.build(),
                    HttpResponse.BodyHandlers.ofString());
            return new Banc.Reponse(reponse.statusCode(), reponse.body());
        } catch (java.io.IOException | InterruptedException panne) {
            if (panne instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            return new Banc.Reponse(0, panne.getClass().getSimpleName());
        }
    }

    private static String court(String texte, int largeur) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= largeur ? plat
                : plat.substring(0, largeur - 3) + "...";
    }
}
