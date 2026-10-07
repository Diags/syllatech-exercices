package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.comptes.AuthentificationNaive;
import java.util.List;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.AuthenticationException;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;

/**
 * Chapitre 2 — Authentification.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Authentification
 * </pre>
 *
 * <p>Le cours prévient contre l'énumération d'utilisateurs : « on renvoie le
 * même message d'erreur générique ». C'est nécessaire et ce n'est pas
 * suffisant. Ce chapitre vérifie d'abord que les messages sont bien
 * identiques — puis <strong>chronomètre</strong> les deux chemins, et montre
 * qu'une authentification écrite à la main les distingue par le temps.
 */
public final class Chapitre2Authentification {

    private Chapitre2Authentification() {
    }

    /** Assez d'essais pour que la médiane soit stable, pas assez pour lasser. */
    private static final int ESSAIS = 15;

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var gestionnaire = banc.bean(AuthenticationManager.class);
            var naive = banc.bean(AuthentificationNaive.class);

            Console.titre(1, "LE MEME MESSAGE, QUOI QU'IL ARRIVE");
            var inconnu = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"fantome\",\"motDePasse\":\"motdepasse\"}");
            var mauvais = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"awa\",\"motDePasse\":\"pas-le-bon\"}");
            var bon = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"awa\",\"motDePasse\":\"motdepasse\"}");
            Console.tableau(List.of("tentative", "code", "corps"), List.of(
                    List.of("compte inconnu", String.valueOf(inconnu.code()),
                            inconnu.apercu(38)),
                    List.of("mot de passe faux", String.valueOf(mauvais.code()),
                            mauvais.apercu(38)),
                    List.of("les deux bons", String.valueOf(bon.code()),
                            bon.corps().length() + " caracteres de jetons")),
                    List.of(22, 8, 42));
            System.out.println();
            Console.ligne("les deux refus sont-ils identiques ?",
                    inconnu.corps().equals(mauvais.corps()) ? "oui" : "NON", 40);
            System.out.println();
            Console.texte("C'est la premiere precaution, et elle est "
                    + "respectee : rien dans la reponse ne dit si le compte "
                    + "existe. Un attaquant qui essaie dix mille adresses "
                    + "n'apprend rien... en lisant les reponses.");

            Console.titre(2, "MAIS LE TEMPS, LUI, PARLE");
            var naifInconnu = mediane(() -> naive.verifier("fantome", "x"));
            var naifMauvais = mediane(() -> naive.verifier("awa", "pas-le-bon"));
            Console.tableau(List.of("authentification ecrite a la main",
                    "mediane", "verdict"), List.of(
                    List.of("compte inconnu", enMs(naifInconnu), "refuse"),
                    List.of("compte connu, mot de passe faux",
                            enMs(naifMauvais), "refuse")),
                    List.of(36, 14, 12));
            System.out.println();
            Console.ligne("rapport entre les deux",
                    rapport(naifMauvais, naifInconnu), 36);
            System.out.println();
            Console.texte("Le meme refus, sans commune mesure. La raison est "
                    + "dans le code : sur un compte inconnu, on part avant "
                    + "d'avoir fait tourner BCrypt. Un attaquant qui "
                    + "chronometre ses tentatives trie donc les comptes "
                    + "existants des autres, sans jamais lire un message.");

            Console.titre(3, "CE QUE SPRING FAIT A LA PLACE");
            var springInconnu = mediane(() -> tenter(gestionnaire, "fantome", "x"));
            var springMauvais = mediane(() -> tenter(gestionnaire, "awa", "pas-le-bon"));
            Console.tableau(List.of("AuthenticationManager de Spring",
                    "mediane", "verdict"), List.of(
                    List.of("compte inconnu", enMs(springInconnu), "refuse"),
                    List.of("compte connu, mot de passe faux",
                            enMs(springMauvais), "refuse")),
                    List.of(36, 14, 12));
            System.out.println();
            Console.ligne("rapport entre les deux",
                    rapport(Math.max(springMauvais, springInconnu),
                            Math.min(springMauvais, springInconnu)), 36);
            System.out.println();
            Console.texte("Les deux chemins coutent la meme chose. "
                    + "`DaoAuthenticationProvider` fait tourner BCrypt contre "
                    + "une empreinte FACTICE quand le compte n'existe pas — "
                    + "la methode s'appelle `mitigateAgainstTimingAttack` "
                    + "dans le code de Spring Security, et elle n'a aucun "
                    + "autre but que celui-la.");
            System.out.println();
            Console.texte("C'est l'argument pour ne pas ecrire soi-meme "
                    + "l'authentification : pas la difficulte du code, mais "
                    + "les precautions qu'on ne sait pas qu'il faut prendre.");

            Console.titre(4, "CE QUE COUTE UN FACTEUR DE COUT");
            var lignes = new java.util.ArrayList<List<String>>();
            for (int cout : new int[]{4, 8, 10, 12}) {
                var encodeur = new BCryptPasswordEncoder(cout);
                String empreinte = encodeur.encode("motdepasse");
                long temps = mediane(() -> encodeur.matches("motdepasse", empreinte));
                lignes.add(List.of("cout " + cout, enMs(temps),
                        temps == 0 ? "trop rapide"
                                : (1000 / Math.max(1, temps / 1_000_000))
                                  + " essais/s/cœur",
                        empreinte.substring(0, 7) + "…"));
            }
            Console.tableau(List.of("BCrypt", "une verification",
                    "pour un attaquant", "prefixe"), lignes,
                    List.of(12, 20, 24, 12));
            System.out.println();
            Console.texte("Le cout est un exposant : chaque unite DOUBLE le "
                    + "travail. Il est inscrit dans l'empreinte — `$2a$10$` — "
                    + "ce qui permet de l'augmenter sans invalider les "
                    + "anciennes : a la prochaine connexion reussie, on "
                    + "reencode au nouveau cout.");

            Console.titre(5, "L'EMPREINTE PORTE SON ALGORITHME");
            var delegant = PasswordEncoderFactories.createDelegatingPasswordEncoder();
            String avecPrefixe = delegant.encode("motdepasse");
            Console.ligne("encodeur delegant, empreinte",
                    avecPrefixe.substring(0, Math.min(16, avecPrefixe.length()))
                    + "…", 34);
            Console.ligne("   il la relit ?",
                    delegant.matches("motdepasse", avecPrefixe) ? "oui" : "non", 34);
            String sansPrefixe = new BCryptPasswordEncoder().encode("motdepasse");
            String verdict;
            try {
                verdict = delegant.matches("motdepasse", sansPrefixe)
                        ? "acceptee" : "REFUSEE (sans exception)";
            } catch (RuntimeException erreur) {
                verdict = erreur.getClass().getSimpleName();
            }
            Console.ligne("une empreinte BCrypt SANS prefixe", verdict, 38);
            System.out.println();
            Console.texte("Le prefixe `{bcrypt}` n'est pas decoratif : c'est "
                    + "ce qui permet a une base de contenir plusieurs "
                    + "generations d'empreintes et de migrer sans tout "
                    + "reinitialiser. Une base remplie par un "
                    + "`BCryptPasswordEncoder` nu ne se relit plus des qu'on "
                    + "passe au delegant — la panne classique d'une migration "
                    + "de Spring Security.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("CORS et CSRF, et la phrase qui debloque tout : "
                    + "« CORS est applique par le navigateur, jamais par "
                    + "votre API ». On va envoyer la requete qu'un site "
                    + "malveillant enverrait, et regarder ce que le serveur "
                    + "repond vraiment.");
            System.out.println();
        }
    }

    /** La médiane de {@value #ESSAIS} exécutions, en nanosecondes. */
    private static long mediane(Runnable geste) {
        // Trois tours pour rechauffer : les premieres executions passent par
        // l'interpreteur, et mesureraient la JVM plutot que BCrypt.
        for (int i = 0; i < 3; i++) {
            geste.run();
        }
        var temps = new long[ESSAIS];
        for (int i = 0; i < ESSAIS; i++) {
            long debut = System.nanoTime();
            geste.run();
            temps[i] = System.nanoTime() - debut;
        }
        java.util.Arrays.sort(temps);
        return temps[ESSAIS / 2];
    }

    private static void tenter(AuthenticationManager gestionnaire,
                               String identifiant, String motDePasse) {
        try {
            gestionnaire.authenticate(new UsernamePasswordAuthenticationToken(
                    identifiant, motDePasse));
        } catch (AuthenticationException attendue) {
            // C'est le cas mesure : le refus.
        }
    }

    /** Une durée lisible : en microsecondes tant qu'elle est courte. */
    private static String enMs(long nanos) {
        return nanos < 1_000_000
                ? "%.0f µs".formatted(nanos / 1_000.0)
                : "%.1f ms".formatted(nanos / 1_000_000.0);
    }

    /**
     * Le rapport entre deux durées, avec les précautions d'usage.
     *
     * <p>Sous 1,5 on refuse de conclure : le bruit d'une JVM dépasse cet
     * écart. Au-delà de mille, on cesse aussi de donner un chiffre — un
     * rapport de plusieurs centaines de milliers ne dit rien de plus que
     * « le chemin rapide ne calcule rien », et un nombre à six chiffres
     * donnerait une fausse impression de précision.
     */
    private static String rapport(long lent, long rapide) {
        if (rapide <= 0) {
            return "le chemin rapide ne calcule rien du tout";
        }
        double facteur = (double) lent / rapide;
        if (facteur < 1.5) {
            return "x%.2f — aucun ecart exploitable".formatted(facteur);
        }
        return facteur > 1000
                ? "plus de x1000 — l'ecart est total"
                : "x%.0f — l'ecart se chronometre".formatted(facteur);
    }
}
