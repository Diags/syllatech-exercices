package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.securite.AdminController;
import fr.portail.securite.RouteOubliee;
import java.util.List;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.FilterChainProxy;

/**
 * Chapitre 5 — Spring Security : les bases.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Securite
 * </pre>
 *
 * <p>« Spring Security n'est pas dans vos contrôleurs : c'est une chaîne de
 * filtres placée devant eux. Comprendre cet ordre, c'est comprendre 90 % de
 * Spring Security. » Ce chapitre imprime cette chaîne — pas un schéma, la
 * liste réelle, lue dans le {@code FilterChainProxy} de l'application qui
 * tourne.
 *
 * <p>Et il vérifie la phrase suivante : « si un filtre refuse, la requête
 * n'atteint jamais votre code métier ». Un compteur dans le contrôleur le
 * dit — ou le contredit.
 */
public final class Chapitre5Securite {

    private Chapitre5Securite() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            Console.titre(1, "LA CHAINE DE FILTRES, TELLE QU'ELLE EST");
            var proxy = banc.bean(FilterChainProxy.class);
            var chaines = proxy.getFilterChains();
            Console.ligne("chaines configurees", String.valueOf(chaines.size()), 30);
            var filtres = chaines.getFirst().getFilters();
            Console.ligne("filtres dans la chaine", String.valueOf(filtres.size()), 30);
            System.out.println();
            int rang = 1;
            for (var filtre : filtres) {
                Console.texte(String.format("%2d. %s", rang++,
                        filtre.getClass().getSimpleName()), 5);
            }
            System.out.println();
            Console.texte("Nous en avons declare zero. Cette chaine est "
                    + "construite par `HttpSecurity`, a partir des quelques "
                    + "lignes de `SecurityConfig` — et son ordre n'est pas "
                    + "negociable : on ne peut pas autoriser avant d'avoir "
                    + "authentifie, ni lire un jeton avant d'avoir un "
                    + "contexte ou le ranger.");
            System.out.println();
            Console.texte("Les deux filtres a retenir sont "
                    + "`BasicAuthenticationFilter` — « qui es-tu ? » — et "
                    + "`AuthorizationFilter`, le dernier — « as-tu le "
                    + "droit ? ». Tout ce qui est entre les deux prepare l'un "
                    + "ou l'autre.");

            Console.titre(2, "QUI PASSE, QUI NE PASSE PAS");
            var anonyme = banc.anonyme();
            var karim = banc.comme("karim", "motdepasse");
            var awa = banc.comme("awa", "motdepasse");
            var lignes = new java.util.ArrayList<List<String>>();
            for (var route : List.of("/api/public/offres", "/actuator/health",
                    "/api/admin/tableau-de-bord", "/rapports/salaires")) {
                lignes.add(List.of(route,
                        String.valueOf(Banc.obtenir(anonyme, route).valeur()),
                        String.valueOf(Banc.obtenir(karim, route).valeur()),
                        String.valueOf(Banc.obtenir(awa, route).valeur())));
            }
            Console.tableau(List.of("route", "anonyme", "karim (USER)",
                    "awa (ADMIN)"), lignes, List.of(30, 10, 14, 14));
            System.out.println();
            Console.texte("La derniere ligne est la lecon du chapitre. "
                    + "`/rapports/salaires` n'apparait NULLE PART dans "
                    + "`SecurityConfig` : ni ouverte, ni reservee. Elle a ete "
                    + "ajoutee apres coup, comme dans la vraie vie, et elle "
                    + "rend la mediane reelle des salaires.");
            System.out.println();
            Console.texte("Elle repond 401 a l'anonyme parce que la derniere "
                    + "regle est `anyRequest().authenticated()`. Avec la "
                    + "configuration inverse — tout ouvert sauf une liste "
                    + "d'exceptions — elle aurait repondu 200, et la fuite "
                    + "serait passee inapercue jusqu'a ce que quelqu'un la "
                    + "trouve.");
            System.out.println();
            Console.texte("Le refus par defaut ne rend pas le code plus sur "
                    + "en soi. Il fait porter l'OUBLI du bon cote : on oublie "
                    + "d'ouvrir une route, et on s'en apercoit tout de suite.");

            Console.titre(3, "UNE PANNE QUI SE DEGUISE EN PROBLEME D'ACCES");
            var panne = Banc.obtenir(anonyme, "/api/public/panne");
            Console.ligne("GET /api/public/panne (route OUVERTE)",
                    panne.valeur() + " — " + panne.apercu(34), 42);
            Console.ligne("ce qu'on attendait", "500", 42);
            System.out.println();
            Console.texte("La route est dans `/api/public/**`, donc "
                    + "`permitAll`. Elle leve une exception que personne ne "
                    + "traite. Et le client recoit un 401.");
            System.out.println();
            Console.texte("Quand Spring MVC ne sait pas traiter une exception, "
                    + "il fait une SECONDE passe vers `/error` — et cette "
                    + "passe retraverse la chaine de filtres. `/error` n'est "
                    + "cite nulle part dans `SecurityConfig` : c'est donc "
                    + "`anyRequest().authenticated()` qui repond, et la vraie "
                    + "erreur disparait.");
            System.out.println();
            Console.texte("Consequence pratique : une panne de base se "
                    + "presente au client comme un probleme "
                    + "d'authentification. C'est une heure de recherche dans "
                    + "la mauvaise direction, et cela arrive a tout le monde "
                    + "une fois. Le correctif tient en une ligne — ouvrir "
                    + "`/error` — mais il faut d'abord savoir que la question "
                    + "se pose.");

            Console.titre(4, "401 ET 403 NE DISENT PAS LA MEME CHOSE");
            var sansJeton = Banc.obtenir(anonyme, "/api/admin/tableau-de-bord");
            var mauvaisRole = Banc.obtenir(karim, "/api/admin/tableau-de-bord");
            Console.ligne("sans identifiants",
                    sansJeton.valeur() + " — " + sansJeton.entetes()
                            .getOrDefault("WWW-Authenticate", ""), 30);
            Console.ligne("karim, authentifie mais USER",
                    mauvaisRole.valeur() + " — role insuffisant", 30);
            System.out.println();
            Console.texte("401 dit « je ne sais pas qui tu es » et propose une "
                    + "facon de le dire — c'est l'en-tete `WWW-Authenticate`. "
                    + "403 dit « je sais qui tu es, et non ». Renvoyer 401 a "
                    + "la place d'un 403 ferait boucler un client qui "
                    + "reessaierait de s'authentifier indefiniment.");

            Console.titre(5, "UN REFUS N'ATTEINT PAS LE CONTROLEUR");
            AdminController.remettreAZero();
            RouteOubliee.remettreAZero();
            for (int i = 0; i < 20; i++) {
                Banc.obtenir(anonyme, "/api/admin/tableau-de-bord");
                Banc.obtenir(karim, "/api/admin/tableau-de-bord");
                Banc.obtenir(anonyme, "/rapports/salaires");
            }
            Console.ligne("requetes refusees envoyees", "60", 38);
            Console.ligne("entrees dans AdminController",
                    String.valueOf(AdminController.entrees()), 38);
            Console.ligne("entrees dans RouteOubliee",
                    String.valueOf(RouteOubliee.entrees()), 38);
            System.out.println();
            var reussies = Banc.obtenir(awa, "/api/admin/tableau-de-bord");
            Console.ligne("une requete autorisee (awa)",
                    reussies.valeur() + " — " + reussies.apercu(40), 38);
            Console.ligne("entrees dans AdminController",
                    String.valueOf(AdminController.entrees()), 38);
            System.out.println();
            Console.texte("Zero, puis un. Le code metier n'a jamais vu les "
                    + "soixante requetes refusees : elles se sont arretees "
                    + "dans la chaine de filtres, avant Spring MVC. C'est ce "
                    + "que « devant vos controleurs » veut dire — et la "
                    + "raison pour laquelle on ne verifie pas les droits dans "
                    + "un `if` en debut de methode.");

            Console.titre(6, "BCRYPT : LE MEME MOT DE PASSE, DEUX EMPREINTES");
            var encodeur = banc.bean(PasswordEncoder.class);
            String premiere = encodeur.encode("motdepasse");
            String seconde = encodeur.encode("motdepasse");
            Console.texte(premiere, 6);
            Console.texte(seconde, 6);
            Console.ligne("identiques ?",
                    String.valueOf(premiere.equals(seconde)), 34);
            Console.ligne("les deux valident le mot de passe ?",
                    encodeur.matches("motdepasse", premiere)
                    && encodeur.matches("motdepasse", seconde) ? "oui" : "non", 40);
            Console.ligne("un mauvais mot de passe",
                    encodeur.matches("motdepass", premiere) ? "ACCEPTE" : "refuse", 40);
            System.out.println();
            Console.texte("Le sel est dans l'empreinte — c'est ce que "
                    + "signalent les caracteres qui suivent `$2a$10$`. Deux "
                    + "utilisateurs qui choisissent le meme mot de passe "
                    + "n'ont donc pas la meme ligne en base, et une table "
                    + "volee ne se compare pas a une table pre-calculee.");
            System.out.println();
            long debut = System.nanoTime();
            for (int i = 0; i < 5; i++) {
                encodeur.matches("motdepasse", premiere);
            }
            long parVerification = (System.nanoTime() - debut) / 5 / 1_000_000;
            Console.ligne("une verification coute",
                    "environ " + parVerification + " ms", 34);
            Console.ligne("soit, pour un attaquant",
                    "environ " + (parVerification == 0 ? "beaucoup"
                            : String.valueOf(1000 / parVerification))
                    + " essais par seconde et par cœur", 38);
            System.out.println();
            Console.texte("Cette lenteur EST la protection. Une empreinte "
                    + "SHA-256 se calcule par milliards par seconde sur une "
                    + "carte graphique ; le chiffre mesure ci-dessus est ce "
                    + "que BCrypt laisse a un attaquant qui aurait vole la "
                    + "table. Le cout est un parametre de l'algorithme — il "
                    + "s'augmente a mesure que le materiel s'ameliore, et "
                    + "l'empreinte porte le sien, ce qui permet de le changer "
                    + "sans invalider les anciennes.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Ce que pese cette application une fois empaquetee, "
                    + "et pourquoi la decouper en couches change la duree "
                    + "d'un deploiement.");
            System.out.println();
        }
    }
}
