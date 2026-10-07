package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.securite.SecurityConfig;
import java.util.List;
import org.springframework.web.cors.CorsConfiguration;

/**
 * Chapitre 3 — CORS et CSRF.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3CorsCsrf
 * </pre>
 *
 * <p>Le cours donne la clé : « CORS est appliqué par le navigateur, jamais
 * par votre API ». C'est une affirmation sur ce que le serveur fait, donc
 * elle se mesure. Ce chapitre envoie la requête qu'un site malveillant
 * enverrait — en-tête {@code Origin} compris — et regarde ce qui revient.
 *
 * <p>Réponse : <strong>les données</strong>. Le serveur répond, complètement.
 * Seul l'en-tête {@code Access-Control-Allow-Origin} manque, et c'est le
 * navigateur qui, ne le voyant pas, cache la réponse au JavaScript appelant.
 * Un client qui n'est pas un navigateur — curl, un script, un autre serveur —
 * n'est gêné par rien.
 */
public final class Chapitre3CorsCsrf {

    private Chapitre3CorsCsrf() {
    }

    private static final String ORIGINE_PIRATE = "https://site-pirate.test";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            Console.titre(1, "CORS N'EMPECHE PAS LE SERVEUR DE REPONDRE");
            var depuisLaSpa = banc.obtenir("/api/public/offres",
                    "Origin", SecurityConfig.ORIGINE_AUTORISEE);
            var depuisLePirate = banc.obtenir("/api/public/offres",
                    "Origin", ORIGINE_PIRATE);
            var sansOrigine = banc.obtenir("/api/public/offres");
            Console.tableau(List.of("Origin envoye", "code", "octets recus",
                    "Allow-Origin"), List.of(
                    List.of("(aucun — curl)", String.valueOf(sansOrigine.code()),
                            String.valueOf(sansOrigine.corps().length()),
                            sansOrigine.entete("Access-Control-Allow-Origin")),
                    List.of("la SPA autorisee", String.valueOf(depuisLaSpa.code()),
                            String.valueOf(depuisLaSpa.corps().length()),
                            raccourcir(depuisLaSpa.entete(
                                    "Access-Control-Allow-Origin"))),
                    List.of("un site pirate", String.valueOf(depuisLePirate.code()),
                            String.valueOf(depuisLePirate.corps().length()),
                            depuisLePirate.entete("Access-Control-Allow-Origin"))),
                    List.of(22, 8, 16, 30));
            System.out.println();
            Console.sousTitre("Ce que le « site pirate » a reellement recu :");
            Console.texte(depuisLePirate.apercu(120), 6);
            System.out.println();
            Console.texte("⚠️ La troisieme ligne surprend, et elle corrige une "
                    + "formule courante. La specification CORS dit que le "
                    + "serveur repond toujours et que le NAVIGATEUR cache la "
                    + "reponse ; le `CorsFilter` de Spring Security va plus "
                    + "loin et REFUSE la requete — 403, « Invalid CORS "
                    + "request », vingt octets. Le controleur n'est jamais "
                    + "atteint.");
            System.out.println();
            Console.texte("Mais regardez la PREMIERE ligne : sans en-tete "
                    + "`Origin`, la meme route rend les 142 octets complets. "
                    + "Or un attaquant n'est pas oblige d'envoyer `Origin` — "
                    + "seul un navigateur le fait, et il le fait parce qu'il "
                    + "joue le jeu. Un `curl`, un script, un autre serveur "
                    + "passent sans rien.");
            System.out.println();
            Console.texte("La conclusion du cours tient donc, et il faut la "
                    + "lire au pied de la lettre : CORS ne protege pas votre "
                    + "API. Une route ouverte reste ouverte a tout ce qui "
                    + "n'est pas un navigateur. CORS protege VOS UTILISATEURS "
                    + "contre des pages tierces qui liraient leurs donnees — "
                    + "et c'est deja beaucoup.");

            Console.titre(2, "LA REQUETE QUE LE NAVIGATEUR ENVOIE AVANT");
            var preflightAutorise = banc.preflight("/api/moi",
                    SecurityConfig.ORIGINE_AUTORISEE, "GET");
            var preflightRefuse = banc.preflight("/api/moi",
                    ORIGINE_PIRATE, "GET");
            Console.tableau(List.of("preflight OPTIONS depuis", "code",
                    "Allow-Methods", "Max-Age"), List.of(
                    List.of("la SPA autorisee",
                            String.valueOf(preflightAutorise.code()),
                            preflightAutorise.entete("Access-Control-Allow-Methods"),
                            preflightAutorise.entete("Access-Control-Max-Age")),
                    List.of("un site pirate", String.valueOf(preflightRefuse.code()),
                            preflightRefuse.entete("Access-Control-Allow-Methods"),
                            preflightRefuse.entete("Access-Control-Max-Age"))),
                    List.of(24, 8, 28, 12));
            System.out.println();
            Console.texte("Des qu'une requete n'est pas « simple » — un "
                    + "en-tete `Authorization`, un `Content-Type: "
                    + "application/json` — le navigateur envoie d'abord un "
                    + "`OPTIONS` pour demander la permission. C'est la seule "
                    + "requete CORS que le serveur traite vraiment : il y "
                    + "repond sans jamais atteindre votre controleur.");
            System.out.println();
            Console.texte("`Max-Age` dit au navigateur combien de temps il "
                    + "peut garder cette permission. Sans lui, chaque appel "
                    + "de votre SPA en coute deux.");

            Console.titre(3, "L'ETOILE ET LES IDENTIFIANTS SONT INCOMPATIBLES");
            String verdict;
            try {
                var dangereuse = new CorsConfiguration();
                dangereuse.setAllowedOrigins(List.of("*"));
                dangereuse.setAllowCredentials(true);
                dangereuse.validateAllowCredentials();
                verdict = "acceptee — aucun garde-fou";
            } catch (IllegalArgumentException refus) {
                verdict = "REFUSEE : " + premiereePhrase(refus.getMessage());
            }
            Console.ligne("allowedOrigins(\"*\") + allowCredentials(true)",
                    verdict, 46);
            System.out.println();
            Console.texte("Le garde-fou existe, et il est a la construction — "
                    + "pas a la premiere requete. La combinaison reviendrait "
                    + "a dire « n'importe quel site peut lire les donnees de "
                    + "mes utilisateurs connectes », ce qui est exactement ce "
                    + "que CORS existe pour empecher.");
            System.out.println();
            Console.ligne("l'origine autorisee du portail",
                    SecurityConfig.ORIGINE_AUTORISEE, 34);

            Console.titre(4, "CSRF : CE QUE LE COOKIE FAIT TOUT SEUL");
            var connexion = banc.obtenir("/session/connexion",
                    "Authorization", basic("awa"));
            String cookie = "JSESSIONID=" + connexion.cookie("JSESSIONID");
            // Le jeton CSRF vient de la reponse elle-meme : c'est ce que fait
            // une SPA, qui appelle une route pour l'obtenir avant d'ecrire.
            String jetonCsrf = connexion.valeur("csrfJeton");
            var cookieSeul = banc.obtenir("/session/moi", "Cookie", cookie);
            Console.ligne("GET /session/moi, avec le cookie SEUL",
                    cookieSeul.code() + " — " + cookieSeul.apercu(30), 42);
            System.out.println();
            // ⚠️ Les deux POST portent les MEMES identifiants. On ne fait
            // varier qu'une chose — le jeton CSRF — sinon on ne saurait pas
            // ce que le code de reponse mesure. La ligne au-dessus a deja
            // montre que le cookie seul authentifie.
            var sansJeton = banc.poster("/session/candidater", "{}",
                    "Cookie", cookie, "Authorization", basic("awa"));
            var avecJeton = banc.poster("/session/candidater", "{}",
                    "Cookie", cookie + "; XSRF-TOKEN=" + jetonCsrf,
                    "Authorization", basic("awa"),
                    connexion.valeur("csrfEnTete"), jetonCsrf);
            Console.tableau(List.of("POST /session/candidater", "code",
                    "reponse"), List.of(
                    List.of("authentifie, SANS jeton CSRF",
                            String.valueOf(sansJeton.code()), sansJeton.apercu(34)),
                    List.of("   le meme, AVEC le jeton CSRF",
                            String.valueOf(avecJeton.code()), avecJeton.apercu(34))),
                    List.of(34, 8, 38));
            System.out.println();
            Console.texte("La premiere ligne est le probleme : le cookie "
                    + "seul suffit a etre AUTHENTIFIE. Un site pirate qui fait soumettre un "
                    + "formulaire vers votre domaine voit le navigateur "
                    + "joindre le cookie tout seul, et l'action part en votre "
                    + "nom. Le jeton CSRF ferme la porte : il n'est pas dans "
                    + "un cookie envoye automatiquement, il faut du "
                    + "JavaScript pour le lire et le poser — et la "
                    + "Same-Origin Policy l'interdit depuis un autre site.");

            Console.titre(5, "POURQUOI L'API JWT S'EN PASSE");
            var apiSansRien = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"awa\",\"motDePasse\":\"motdepasse\"}");
            Console.ligne("POST sur l'API, sans jeton CSRF",
                    String.valueOf(apiSansRien.code()), 38);
            Console.ligne("CSRF sur la chaine de l'API", "desactive", 38);
            Console.ligne("CSRF sur la chaine de session", "actif", 38);
            System.out.println();
            Console.texte("La regle tient en une phrase : CSRF protege les "
                    + "sessions par COOKIE, pas les API par JETON. Un en-tete "
                    + "`Authorization: Bearer …` ne part jamais tout seul — "
                    + "il faut du JavaScript pour le poser, et un site tiers "
                    + "n'y a pas acces. L'attaque n'existe pas, la protection "
                    + "n'a rien a proteger.");
            System.out.println();
            Console.texte("La meme application tient donc les deux "
                    + "configurations en meme temps, et c'est la bonne "
                    + "reponse : ce n'est pas une question de gout, c'est une "
                    + "question de la facon dont la requete porte son "
                    + "identite.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Un vrai JWT, lu sans aucune cle — puis trois "
                    + "attaques classiques soumises au decodeur de Spring, et "
                    + "le talon d'Achille : un jeton qu'on ne peut pas "
                    + "revoquer.");
            System.out.println();
        }
    }

    private static String basic(String utilisateur) {
        return "Basic " + java.util.Base64.getEncoder().encodeToString(
                (utilisateur + ":motdepasse")
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    private static String premiereePhrase(String message) {
        if (message == null) {
            return "(sans message)";
        }
        int point = message.indexOf(". ");
        String phrase = point < 0 ? message : message.substring(0, point);
        return phrase.length() <= 46 ? phrase : phrase.substring(0, 43) + "...";
    }

    private static String raccourcir(String valeur) {
        return valeur.length() <= 28 ? valeur : valeur.substring(0, 25) + "...";
    }
}
