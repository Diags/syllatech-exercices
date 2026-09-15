package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.web.Controleurs;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.Executors;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.AuthorityUtils;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.FilterChainProxy;

/**
 * Chapitre 1 — Les fondamentaux et la chaîne de filtres.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Chaine
 * </pre>
 *
 * <p>« Comprendre l'ordre de ces filtres, c'est comprendre 90 % de Spring
 * Security. » Ce chapitre imprime les <strong>deux</strong> chaînes de
 * l'application, filtre par filtre, et montre ce que change le fait d'en
 * avoir deux. Puis il mesure ce que « stateless » veut dire : aucun cookie,
 * aucune session, un contexte reconstruit et jeté à chaque requête.
 */
public final class Chapitre1Chaine {

    private Chapitre1Chaine() {
    }

    public static void main(String[] args) throws Exception {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var proxy = banc.bean(FilterChainProxy.class);
            var chaines = proxy.getFilterChains();

            Console.titre(1, "DEUX CHAINES, ET CELLE QUI REPOND");
            Console.ligne("chaines configurees", String.valueOf(chaines.size()), 30);
            for (int i = 0; i < chaines.size(); i++) {
                var chaine = chaines.get(i);
                Console.ligne("  chaine " + (i + 1),
                        chaine.getFilters().size() + " filtres — "
                        + description(chaine), 30);
            }
            System.out.println();
            Console.texte("Une application a rarement une seule chaine. "
                    + "Spring les essaie DANS L'ORDRE et s'arrete a la "
                    + "premiere dont le `securityMatcher` correspond : les "
                    + "suivantes ne sont jamais consultees, meme si la "
                    + "premiere refuse. Une regle ecrite dans la mauvaise "
                    + "chaine ne s'applique donc jamais — et rien ne le "
                    + "signale.");

            Console.titre(2, "LA CHAINE DE L'API, FILTRE PAR FILTRE");
            var filtres = chaines.getLast().getFilters().stream()
                    .map(f -> f.getClass().getSimpleName()).toList();
            int rang = 1;
            for (var filtre : filtres) {
                String role = ROLES.getOrDefault(filtre, "");
                Console.texte(String.format("%2d. %-42s %s", rang++, filtre, role), 5);
            }
            System.out.println();
            Console.ligne("le jeton est lu au rang",
                    String.valueOf(filtres.indexOf(
                            "BearerTokenAuthenticationFilter") + 1), 34);
            Console.ligne("les droits sont verifies au rang",
                    String.valueOf(filtres.indexOf("AuthorizationFilter") + 1), 34);
            System.out.println();
            Console.texte("L'ordre n'est pas negociable : on ne peut pas "
                    + "verifier les droits de quelqu'un qu'on n'a pas encore "
                    + "identifie. Quand une configuration « ne marche pas », "
                    + "c'est presque toujours un filtre au mauvais rang ou un "
                    + "filtre absent — pas un bug du cadre.");

            Console.titre(3, "SANS ETAT : CE QUI NE SORT PAS DE L'API");
            var jeton = seConnecter(banc, "awa");
            var surLApi = banc.obtenirAvecJeton("/api/moi", jeton);
            var surLaSession = banc.obtenir("/session/connexion",
                    "Authorization", basic("awa", "motdepasse"));
            Console.tableau(List.of("requete", "code", "Set-Cookie"), List.of(
                    List.of("GET /api/moi (Bearer)", String.valueOf(surLApi.code()),
                            raccourcir(surLApi.entete("Set-Cookie"))),
                    List.of("GET /session/connexion (Basic)",
                            String.valueOf(surLaSession.code()),
                            raccourcir(surLaSession.entete("Set-Cookie")))),
                    List.of(34, 8, 34));
            System.out.println();
            Console.ligne("session HTTP vue par /api/moi",
                    surLApi.valeur("sessionHttp"), 34);
            System.out.println();
            Console.texte("La chaine de l'API est en `STATELESS` : aucune "
                    + "session n'est creee, aucun cookie ne sort, et le "
                    + "serveur ne retient rien entre deux requetes. C'est ce "
                    + "qui permet de multiplier les instances derriere un "
                    + "repartiteur sans « session collante » — et c'est aussi "
                    + "ce qui rend un jeton vole si genant, faute de rien a "
                    + "invalider.");

            Console.titre(4, "LE CONTEXTE EST LIE AU THREAD");
            SecurityContextHolder.getContext().setAuthentication(
                    new UsernamePasswordAuthenticationToken("chapitre", "n/a",
                            AuthorityUtils.createAuthorityList("ROLE_TEST")));
            Console.ligne("depuis le thread principal",
                    nomDuContexte(), 34);
            var vuAilleurs = new ArrayList<String>();
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                executeur.submit(() -> vuAilleurs.add(nomDuContexte()));
            }
            Console.ligne("depuis un autre thread",
                    vuAilleurs.isEmpty() ? "?" : vuAilleurs.getFirst(), 34);
            SecurityContextHolder.clearContext();
            Console.ligne("apres clearContext()", nomDuContexte(), 34);
            System.out.println();
            Console.texte("`SecurityContextHolder` tient le contexte dans un "
                    + "`ThreadLocal`. Une tache lancee dans un autre thread ne "
                    + "voit donc AUCUNE identite : un `@Async`, un "
                    + "`CompletableFuture` ou un executeur perdent "
                    + "l'utilisateur en route, et le code appele s'execute "
                    + "sans droits au lieu d'echouer bruyamment.");
            System.out.println();
            Console.texte("C'est le meme mecanisme qui rend l'API sans etat : "
                    + "le filtre pose le contexte au debut de la requete et le "
                    + "vide a la fin. Rien ne survit, et c'est voulu.");

            Console.titre(5, "UN REFUS N'ATTEINT PAS LE CODE METIER");
            Controleurs.remettreAZero();
            for (int i = 0; i < 20; i++) {
                banc.obtenir("/api/moi");
                banc.obtenir("/api/rh/candidatures");
            }
            Console.ligne("40 requetes sans jeton", "envoyees", 34);
            Console.ligne("entrees dans les controleurs",
                    String.valueOf(Controleurs.entrees()), 34);
            var avecJeton = banc.obtenirAvecJeton("/api/rh/candidatures", jeton);
            Console.ligne("une requete avec le jeton d'awa (RH)",
                    avecJeton.code() + " — entrees : " + Controleurs.entrees(), 38);
            System.out.println();
            Console.texte("Zero, puis un. Les quarante requetes refusees se "
                    + "sont arretees dans la chaine, avant Spring MVC. C'est "
                    + "ce que « la securite vit au bord du systeme » veut "
                    + "dire : le code metier n'a jamais a se demander qui "
                    + "parle.");

            Console.titre(6, "CE QU'UNE PANNE MONTRE DE LA CHAINE");
            Controleurs.remettreAZero();
            var panne = banc.obtenir("/api/public/panne");
            var panneAvecJeton = banc.obtenirAvecJeton("/api/public/panne", jeton);
            Console.ligne("GET /api/public/panne, anonyme",
                    panne.code() + " — " + panne.apercu(30), 38);
            Console.ligne("   la meme, avec un jeton valide",
                    panneAvecJeton.code() + " — " + panneAvecJeton.apercu(30), 38);
            Console.ligne("entrees dans le controleur",
                    String.valueOf(Controleurs.entrees()), 38);
            System.out.println();
            Console.texte("La route est `permitAll`, le controleur a bien ete "
                    + "atteint deux fois, et pourtant l'anonyme recoit un 401. "
                    + "Quand Spring MVC ne sait pas traiter une exception, il "
                    + "fait une seconde passe vers `/error` — qui RETRAVERSE "
                    + "la chaine de filtres. `/error` n'etant liste nulle "
                    + "part, c'est `anyRequest().authenticated()` qui repond.");
            System.out.println();
            Console.texte("Consequence : une panne d'annuaire se presente au "
                    + "client comme un probleme d'authentification. Une heure "
                    + "de recherche dans la mauvaise direction, et cela "
                    + "arrive a tout le monde une fois.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le trio de l'authentification, et une fuite que le "
                    + "message d'erreur generique ne bouche pas : le TEMPS de "
                    + "reponse.");
            System.out.println();
        }
    }

    private static final java.util.Map<String, String> ROLES =
            java.util.Map.ofEntries(
                java.util.Map.entry("DisableEncodeUrlFilter",
                        "empeche de coller la session dans l'URL"),
                java.util.Map.entry("SecurityContextHolderFilter",
                        "pose et vide le contexte"),
                java.util.Map.entry("CorsFilter",
                        "ecrit les en-tetes CORS (chapitre 3)"),
                java.util.Map.entry("BearerTokenAuthenticationFilter",
                        "lit le jeton — « qui es-tu ? »"),
                java.util.Map.entry("ExceptionTranslationFilter",
                        "traduit les refus en 401 / 403"),
                java.util.Map.entry("AuthorizationFilter",
                        "decide — « as-tu le droit ? »"));

    private static String seConnecter(Banc banc, String identifiant) {
        var reponse = banc.poster("/api/public/connexion",
                "{\"identifiant\":\"" + identifiant
                + "\",\"motDePasse\":\"motdepasse\"}");
        return reponse.valeur("access_token");
    }

    private static String basic(String utilisateur, String motDePasse) {
        return "Basic " + java.util.Base64.getEncoder().encodeToString(
                (utilisateur + ":" + motDePasse)
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8));
    }

    private static String nomDuContexte() {
        var authentification = SecurityContextHolder.getContext().getAuthentication();
        return authentification == null ? "aucune identite"
                : authentification.getName();
    }

    /** Ce que cette chaîne couvre, lu dans son propre {@code RequestMatcher}. */
    private static String description(
            org.springframework.security.web.SecurityFilterChain chaine) {
        if (chaine instanceof org.springframework.security.web
                .DefaultSecurityFilterChain defaut) {
            String motif = defaut.getRequestMatcher().toString();
            return motif.contains("any request")
                    ? "toutes les requetes restantes" : motif;
        }
        return "(motif inconnu)";
    }

    private static String raccourcir(String valeur) {
        return valeur.length() <= 32 ? valeur : valeur.substring(0, 29) + "...";
    }
}
