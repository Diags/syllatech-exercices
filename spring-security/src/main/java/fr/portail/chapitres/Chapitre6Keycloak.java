package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.jeton.ServiceDeJetons;
import fr.portail.securite.ConvertisseurDeRoles;
import fr.portail.web.Controleurs;
import fr.portail.web.Proprietaire;
import java.util.List;
import org.springframework.security.oauth2.jwt.JwtDecoder;

/**
 * Chapitre 6 — KeyCloak et Authorization Server.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Keycloak
 * </pre>
 *
 * <p>« Un détail fait trébucher tout le monde : KeyCloak range les rôles dans
 * {@code realm_access.roles} et sans le préfixe {@code ROLE_}. » Ce chapitre
 * coupe le convertisseur, envoie le <strong>même</strong> jeton, et mesure le
 * 403. Puis il le remet, réenvoie le même jeton, et mesure le 200.
 *
 * <p>Puis il montre ce qu'une règle d'URL ne peut pas exprimer : « seulement
 * si cette offre vous appartient ». Même chemin, deux utilisateurs, deux
 * réponses — et un compteur qui dit que le contrôleur n'a pas été atteint.
 */
public final class Chapitre6Keycloak {

    private Chapitre6Keycloak() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var jetons = banc.bean(ServiceDeJetons.class);
            var convertisseur = banc.bean(ConvertisseurDeRoles.class);
            var decodeur = banc.bean(JwtDecoder.class);

            String jetonRh = jetons.acces("awa", List.of("RH", "USER"));

            Console.titre(1, "CE QUE LE JETON DIT, ET CE QUE SPRING COMPREND");
            var decode = decodeur.decode(jetonRh);
            Console.ligne("le claim `realm_access.roles`",
                    String.valueOf(ConvertisseurDeRoles.rolesDu(decode)), 34);
            Console.ligne("ce que `hasRole('RH')` attend", "ROLE_RH", 34);
            System.out.println();
            convertisseur.actif(false);
            Console.ligne("autorites SANS le convertisseur",
                    String.valueOf(convertisseur.autorites(decode)), 38);
            convertisseur.actif(true);
            Console.ligne("autorites AVEC le convertisseur",
                    String.valueOf(convertisseur.autorites(decode)), 38);
            System.out.println();
            Console.texte("Deux differences, et il faut les deux : le claim "
                    + "est IMBRIQUE — `realm_access` contient `roles` — et les "
                    + "roles n'ont pas le prefixe `ROLE_`. Spring ne devine ni "
                    + "l'un ni l'autre : hors convertisseur, il ne trouve "
                    + "aucune autorite dans un jeton pourtant complet.");

            Console.titre(2, "LE MEME JETON, DEUX REPONSES");
            var lignes = new java.util.ArrayList<List<String>>();
            for (boolean actif : new boolean[]{false, true}) {
                convertisseur.actif(actif);
                var parUrl = banc.obtenirAvecJeton("/api/rh/candidatures", jetonRh);
                var parMethode = banc.obtenirAvecJeton("/api/rh/statistiques", jetonRh);
                var moi = banc.obtenirAvecJeton("/api/moi", jetonRh);
                lignes.add(List.of(actif ? "convertisseur ACTIF" : "sans convertisseur",
                        String.valueOf(parUrl.code()),
                        String.valueOf(parMethode.code()),
                        String.valueOf(moi.code())));
            }
            Console.tableau(List.of("configuration", "/api/rh/… (URL)",
                    "@PreAuthorize", "/api/moi"), lignes,
                    List.of(24, 16, 16, 12));
            convertisseur.actif(true);
            System.out.println();
            Console.texte("La derniere colonne est celle qui trompe : "
                    + "`/api/moi` demande seulement d'etre authentifie, et il "
                    + "repond 200 dans les deux cas. Le jeton EST valide, "
                    + "l'identite EST etablie — il ne manque que les "
                    + "autorites. D'ou un 403 sur les deux autres routes, et "
                    + "un 401 nulle part.");
            System.out.println();
            Console.texte("C'est la raison pour laquelle ce bug est si long a "
                    + "trouver : tout marche, sauf les droits, et le jeton "
                    + "colle sur jwt.io montre bien le role. Devant un 403 "
                    + "inexplique avec un jeton KeyCloak, pensez au "
                    + "convertisseur en premier.");

            Console.titre(3, "POURQUOI `JwtGrantedAuthoritiesConverter` NE SUFFIT PAS");
            var standard = new org.springframework.security.oauth2.server.resource
                    .authentication.JwtGrantedAuthoritiesConverter();
            standard.setAuthoritiesClaimName("realm_access.roles");
            standard.setAuthorityPrefix("ROLE_");
            Console.ligne("avec `setAuthoritiesClaimName(\"realm_access.roles\")`",
                    String.valueOf(standard.convert(decode)), 48);
            Console.ligne("avec le convertisseur de ce projet",
                    String.valueOf(convertisseur.autorites(decode)), 48);
            System.out.println();
            Console.texte("Vide. `setAuthoritiesClaimName` cherche un claim "
                    + "NOMME `realm_access.roles`, avec un point dans son nom "
                    + "— pas un claim `roles` a l'interieur de `realm_access`. "
                    + "L'exemple qui circule le plus sur ce sujet ne marche "
                    + "donc pas, et il ne produit aucune erreur : juste "
                    + "aucune autorite.");
            System.out.println();
            Console.texte("Il faut descendre a la main dans la carte, comme le "
                    + "fait `ConvertisseurDeRoles`. Quinze lignes, et le pont "
                    + "est pose.");

            Console.titre(4, "CE QU'UNE REGLE D'URL NE PEUT PAS DIRE");
            String jetonAwa = jetons.acces("awa", List.of("USER"));
            String jetonKarim = jetons.acces("karim", List.of("USER"));
            Controleurs.remettreAZero();
            Proprietaire.remettreAZero();
            var parLAuteur = banc.obtenirAvecJeton(
                    "/api/offres/OFF-014/brouillon", jetonAwa);
            var parUnAutre = banc.obtenirAvecJeton(
                    "/api/offres/OFF-014/brouillon", jetonKarim);
            Console.tableau(List.of("GET /api/offres/OFF-014/brouillon", "code",
                    "reponse"), List.of(
                    List.of("awa — l'auteur de OFF-014",
                            String.valueOf(parLAuteur.code()),
                            parLAuteur.apercu(34)),
                    List.of("karim — auteur de OFF-021",
                            String.valueOf(parUnAutre.code()),
                            parUnAutre.apercu(34))),
                    List.of(34, 8, 38));
            System.out.println();
            Console.ligne("regle consultee", Proprietaire.consultations()
                    + " fois", 34);
            Console.ligne("entrees dans le controleur",
                    String.valueOf(Controleurs.entrees()), 34);
            System.out.println();
            Console.texte("Le chemin est le MEME, les deux utilisateurs ont le "
                    + "MEME role, et les reponses different. Aucune regle "
                    + "d'URL ne peut exprimer cela : « seulement si l'offre "
                    + "vous appartient » depend de la ressource, pas du "
                    + "chemin.");
            System.out.println();
            Console.texte("Les deux compteurs le disent : la regle a ete "
                    + "evaluee deux fois, le controleur n'a ete atteint "
                    + "qu'une. `@PreAuthorize` s'execute AVANT la methode — "
                    + "le corps de `brouillon` n'a jamais tourne pour karim, "
                    + "et la note « salaire reel negociable » n'a jamais ete "
                    + "construite.");

            Console.titre(5, "LES DEUX COUCHES, ET CE QU'ELLES COUTENT");
            Console.tableau(List.of("couche", "protege", "granularite",
                    "s'execute"), List.of(
                    List.of("chaine de filtres", "des URL", "gros grain",
                            "avant Spring MVC"),
                    List.of("@PreAuthorize", "des methodes", "fin",
                            "avant le corps")),
                    List.of(22, 16, 14, 20));
            System.out.println();
            Console.texte("Les deux se combinent, et c'est le bon reflexe : "
                    + "les filtres ferment les grandes portes — `/api/rh/**` "
                    + "aux RH — et les annotations decident au plus pres de "
                    + "la donnee. Une regle d'URL seule laisserait karim lire "
                    + "le brouillon d'awa ; une annotation seule obligerait a "
                    + "annoter chaque methode, y compris celles qu'on "
                    + "oubliera.");

            Console.titre(6, "CE QUE CE PROJET A MESURE");
            Console.tableau(List.of("chapitre", "la mesure qui compte"), List.of(
                    List.of("1", "14 filtres ; 40 requetes refusees, 0 entree dans le code"),
                    List.of("2", "compte inconnu : instantane chez nous, 78 ms chez Spring"),
                    List.of("3", "sans en-tete `Origin`, l'API repond tout"),
                    List.of("4", "`alg: none`, signature HMAC, charge alteree : trois refus"),
                    List.of("4", "compte supprime, jeton revoque — l'access token passe encore"),
                    List.of("5", "100 requetes authentifiees, 0 telechargement de cle"),
                    List.of("6", "le meme jeton : 403 sans le convertisseur, 200 avec")),
                    List.of(12, 64));
            System.out.println();
            Console.texte("Aucune de ces sept lignes n'est une opinion. "
                    + "Relancez les chapitres : les durees bougeront, les "
                    + "codes de reponse non.");
            System.out.println();
        }
    }
}
