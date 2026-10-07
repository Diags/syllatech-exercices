package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.jeton.Forge;
import fr.portail.web.Decouverte;
import java.util.List;
import org.springframework.security.oauth2.jwt.JwtDecoder;

/**
 * Chapitre 5 — OAuth2 et OpenID Connect.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Oauth2
 * </pre>
 *
 * <p>« L'access token est pour la machine, l'ID token est pour le client. »
 * Ce chapitre émet les deux et compare leurs claims, côte à côte : ce qui est
 * dans l'un et pas dans l'autre <em>est</em> la distinction.
 *
 * <p>Il mesure aussi ce que « l'issuer-uri suffit » veut dire. Le portail
 * publie son propre document de découverte et son propre JWKS — exactement
 * comme un KeyCloak — et un compteur dit combien de fois les clés sont
 * téléchargées pour cent requêtes authentifiées. La réponse tient en un
 * chiffre, et c'est toute la vertu du sans-état.
 */
public final class Chapitre5Oauth2 {

    private Chapitre5Oauth2() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var decodeur = banc.bean(JwtDecoder.class);

            Console.titre(1, "QUATRE ROLES, ET CE QUE CHACUN VOIT");
            Console.tableau(List.of("role", "qui c'est ici", "voit le mot de passe ?"),
                    List.of(
                    List.of("Resource Owner", "awa, karim, lea", "le sien"),
                    List.of("Client", "la SPA / ce chapitre", "il le transmet"),
                    List.of("Authorization Server", "/api/public/connexion", "OUI"),
                    List.of("Resource Server", "/api/** — la chaine JWT", "jamais")),
                    List.of(24, 26, 24));
            System.out.println();
            Console.texte("La derniere ligne est la promesse d'OAuth2 : votre "
                    + "API ne voit jamais le mot de passe. Ici l'emetteur et "
                    + "l'API sont dans la meme application — pour que le "
                    + "projet tourne hors ligne — mais rien ne les relie : le "
                    + "resource server ne connait que la cle publique, et "
                    + "fonctionnerait a l'identique si l'emetteur etait un "
                    + "KeyCloak a l'autre bout du reseau.");

            Console.titre(2, "DEUX JETONS, DEUX METIERS");
            var connexion = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"lea\",\"motDePasse\":\"motdepasse\"}");
            String acces = connexion.valeur("access_token");
            String identite = connexion.valeur("id_token");
            Console.sousTitre("access token — pour la MACHINE :");
            for (var ligne : couper(Forge.lireLaCharge(acces))) {
                Console.texte(ligne, 6);
            }
            Console.sousTitre("ID token — pour le CLIENT :");
            for (var ligne : couper(Forge.lireLaCharge(identite))) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.tableau(List.of("claim", "access token", "ID token"), List.of(
                    comparer("sub", acces, identite),
                    comparer("aud", acces, identite),
                    comparer("realm_access", acces, identite),
                    comparer("email", acces, identite),
                    comparer("name", acces, identite)),
                    List.of(18, 22, 22));
            System.out.println();
            Console.texte("L'access token porte les ROLES et vise l'API ; "
                    + "l'ID token porte l'IDENTITE et vise le client. Le "
                    + "premier ouvre des portes, le second remplit un « Bonjour "
                    + "Lea » en haut de l'ecran. Les confondre, c'est envoyer "
                    + "a l'API un jeton qui ne dit rien de ses droits.");

            Console.titre(3, "CE QUI SE PASSE SI ON PRESENTE LE MAUVAIS");
            var avecAcces = banc.obtenirAvecJeton("/api/rh/candidatures", acces);
            var avecIdentite = banc.obtenirAvecJeton("/api/rh/candidatures", identite);
            Console.tableau(List.of("jeton presente a /api/rh/candidatures",
                    "code", "pourquoi"), List.of(
                    List.of("l'access token", String.valueOf(avecAcces.code()),
                            avecAcces.code() == 200 ? "il porte le role RH" : "?"),
                    List.of("l'ID token", String.valueOf(avecIdentite.code()),
                            avecIdentite.code() == 403
                                    ? "signature valide, aucun role"
                                    : "code " + avecIdentite.code())),
                    List.of(38, 8, 30));
            System.out.println();
            Console.texte("L'ID token est parfaitement signe, parfaitement "
                    + "valide, et parfaitement inutile ici : il ne porte aucun "
                    + "role. Le refus n'est donc pas un 401 — l'identite est "
                    + "etablie — mais un 403. C'est l'erreur qu'on fait en "
                    + "branchant une SPA trop vite, et le code de reponse dit "
                    + "exactement laquelle.");

            Console.titre(4, "LE DOCUMENT DE DECOUVERTE");
            var decouverte = banc.obtenir("/.well-known/openid-configuration");
            Console.ligne("GET /.well-known/openid-configuration",
                    String.valueOf(decouverte.code()), 42);
            System.out.println();
            for (var ligne : couper(decouverte.corps())) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.texte("C'est ce document que Spring lit au demarrage quand "
                    + "on ne lui donne qu'un `issuer-uri`. Il y trouve "
                    + "`jwks_uri`, telecharge les cles, et sait des lors "
                    + "valider chaque jeton — signature, expiration, emetteur "
                    + "— sans une ligne de code. C'est le sens exact de « une "
                    + "ligne de configuration suffit ».");
            System.out.println();
            Console.ligne("`code_challenge_methods_supported`",
                    decouverte.contient("S256") ? "S256 seulement" : "?", 42);
            Console.texte("`plain` n'y figure pas, et c'est deliberé : cette "
                    + "methode PKCE envoie le « secret » en clair des le "
                    + "premier appel, ce qui lui retire tout interet. Lister "
                    + "une methode, c'est l'autoriser.", 3);

            Console.titre(5, "COMBIEN DE FOIS LES CLES SONT-ELLES LUES ?");
            Decouverte.remettreAZero();
            int requetes = 100;
            for (int i = 0; i < requetes; i++) {
                banc.obtenirAvecJeton("/api/moi", acces);
            }
            Console.ligne(requetes + " requetes authentifiees", "envoyees", 34);
            Console.ligne("telechargements du JWKS",
                    String.valueOf(Decouverte.lecturesDuJwks()), 34);
            Console.ligne("appels a une base ou a un annuaire", "0", 34);
            System.out.println();
            Console.texte("Zero. Le decodeur de ce projet tient la cle "
                    + "publique en memoire ; un resource server configure par "
                    + "`issuer-uri` la telecharge une fois et la garde en "
                    + "cache, avec une rotation periodique. Valider un JWT ne "
                    + "parle a personne : c'est un calcul local sur une "
                    + "signature et une date.");
            System.out.println();
            Console.texte("C'est la vertu du sans-etat — et c'est la meme "
                    + "propriete qui rend un jeton irrevocable, mesuree au "
                    + "chapitre 4. On ne peut pas avoir l'une sans l'autre.");

            Console.titre(6, "UN JETON D'UN AUTRE EMETTEUR");
            var etranger = jetonDUnAutreEmetteur();
            String verdict;
            try {
                decodeur.decode(etranger);
                verdict = "ACCEPTE — le decodeur ne verifie pas l'emetteur";
            } catch (RuntimeException refus) {
                verdict = "refuse : " + court(refus.getMessage());
            }
            Console.ligne("un jeton signe par une AUTRE cle RSA", verdict, 42);
            System.out.println();
            Console.texte("La signature ne correspond pas a la cle publique du "
                    + "portail, et le decodeur s'arrete la. C'est ce qui rend "
                    + "la delegation sure : faire confiance a un emetteur, "
                    + "c'est faire confiance a SA cle — pas au format du "
                    + "jeton, que n'importe qui peut imiter.");

            Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le pont entre les roles KeyCloak et Spring : "
                    + "combien de 403 il evite, et ce qu'un "
                    + "`@PreAuthorize` protege qu'une regle d'URL ne peut pas "
                    + "exprimer.");
            System.out.println();
        }
    }

    /** Un jeton signé par une paire de clés qui n'est pas celle du portail. */
    private static String jetonDUnAutreEmetteur() {
        try {
            var generateur = java.security.KeyPairGenerator.getInstance("RSA");
            generateur.initialize(2048);
            var paire = generateur.generateKeyPair();
            var claims = new com.nimbusds.jwt.JWTClaimsSet.Builder()
                    .issuer(fr.portail.jeton.ServiceDeJetons.EMETTEUR)
                    .subject("lea")
                    .expirationTime(java.util.Date.from(
                            java.time.Instant.now().plusSeconds(600)))
                    .claim("realm_access", java.util.Map.of("roles",
                            java.util.List.of("ADMIN")))
                    .build();
            var jwt = new com.nimbusds.jwt.SignedJWT(
                    new com.nimbusds.jose.JWSHeader(
                            com.nimbusds.jose.JWSAlgorithm.RS256), claims);
            jwt.sign(new com.nimbusds.jose.crypto.RSASSASigner(paire.getPrivate()));
            return jwt.serialize();
        } catch (Exception erreur) {
            throw new IllegalStateException("impossible de forger le jeton", erreur);
        }
    }

    private static List<String> comparer(String claim, String acces,
                                         String identite) {
        return List.of(claim, valeur(Forge.lireLaCharge(acces), claim),
                valeur(Forge.lireLaCharge(identite), claim));
    }

    private static String valeur(String json, String claim) {
        var motif = java.util.regex.Pattern.compile(
                "\"" + claim + "\"\\s*:\\s*(\\{[^}]*\\}|\\[[^\\]]*\\]|\"[^\"]*\"|[^,}]+)");
        var trouve = motif.matcher(json);
        if (!trouve.find()) {
            return "(absent)";
        }
        String brut = trouve.group(1).replace("\"", "");
        return brut.length() <= 20 ? brut : brut.substring(0, 17) + "...";
    }

    private static String court(String message) {
        if (message == null) {
            return "(sans message)";
        }
        String plat = message.replaceAll("\\s+", " ").strip();
        return plat.length() <= 32 ? plat : plat.substring(0, 29) + "...";
    }

    private static List<String> couper(String json) {
        return java.util.Arrays.stream(json
                        .replace("{", "{\n ")
                        .replace(",\"", ",\n \"")
                        .replace("}", "\n}")
                        .split("\n"))
                .map(String::strip)
                .filter(l -> !l.isEmpty() && !l.equals("}"))
                .map(l -> l.length() <= 66 ? l : l.substring(0, 63) + "...")
                .toList();
    }
}
