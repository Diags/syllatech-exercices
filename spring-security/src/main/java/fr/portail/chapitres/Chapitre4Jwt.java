package fr.portail.chapitres;

import fr.portail.cles.Cles;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.comptes.ServiceDUtilisateurs;
import fr.portail.jeton.Forge;
import fr.portail.jeton.ServiceDeJetons;
import java.time.Duration;
import java.util.List;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.oauth2.jwt.JwtException;

/**
 * Chapitre 4 — JWT : les tokens en pratique.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jwt
 * </pre>
 *
 * <p>Trois affirmations du cours, et chacune se mesure : « le payload est
 * lisible par n'importe qui », « la signature garantit l'intégrité », « on ne
 * peut pas révoquer ce qu'on ne stocke pas ».
 *
 * <p>Les attaques ne sont pas décrites : elles sont <strong>fabriquées</strong>
 * — charge utile altérée, {@code alg: none}, substitution d'algorithme — et
 * soumises au vrai {@code NimbusJwtDecoder} de Spring Security. Ce qu'il en
 * dit est imprimé mot pour mot.
 */
public final class Chapitre4Jwt {

    private Chapitre4Jwt() {
    }

    public static void main(String[] args) throws Exception {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var jetons = banc.bean(ServiceDeJetons.class);
            var decodeur = banc.bean(JwtDecoder.class);
            var cles = banc.bean(Cles.class);
            var utilisateurs = banc.bean(ServiceDUtilisateurs.class);

            String jeton = jetons.acces("awa", List.of("RH", "USER"));

            Console.titre(1, "SIGNE, PAS CHIFFRE");
            var morceaux = jeton.split("\\.");
            Console.ligne("longueur du jeton", jeton.length() + " caracteres", 30);
            Console.ligne("parties separees par un point",
                    String.valueOf(morceaux.length), 30);
            System.out.println();
            Console.sousTitre("L'en-tete, decode sans aucune cle :");
            Console.texte(Forge.lireLEntete(jeton), 6);
            Console.sousTitre("La charge utile, decodee sans aucune cle :");
            for (var ligne : couper(Forge.lireLaCharge(jeton))) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.texte("Tout cela s'est lu avec un decodeur Base64 de "
                    + "quinze lignes. Un JWT n'est pas chiffre : sa signature "
                    + "garantit que PERSONNE NE L'A MODIFIE, pas que personne "
                    + "ne le lira. On n'y met donc jamais un secret — ni un "
                    + "numero de securite sociale, ni un jeton d'API, ni une "
                    + "adresse qu'on ne publierait pas.");

            Console.titre(2, "TROIS ATTAQUES, ET CE QUE LE DECODEUR EN DIT");
            var essais = new java.util.ArrayList<List<String>>();
            essais.add(essayer(decodeur, "le jeton, tel quel", jeton));
            essais.add(essayer(decodeur, "un role change en Base64",
                    Forge.chargeUtileAlteree(jeton, "\"RH\"", "\"ADMIN\"")));
            essais.add(essayer(decodeur, "le sujet change en Base64",
                    Forge.chargeUtileAlteree(jeton, "\"awa\"", "\"lea\"")));
            essais.add(essayer(decodeur, "`alg: none`, sans signature",
                    Forge.sansSignature(jeton)));
            essais.add(essayer(decodeur, "signe en HMAC avec la cle PUBLIQUE",
                    Forge.signeEnHmacAvecLaClePublique("lea", cles.publique())));
            essais.add(essayer(decodeur, "expire il y a cinq minutes",
                    jetons.accesExpire("awa", List.of("RH"))));
            Console.tableau(List.of("jeton presente", "verdict", "ce que dit le decodeur"),
                    essais, List.of(36, 10, 40));
            System.out.println();
            Console.texte("La signature couvre l'en-tete ET la charge utile : "
                    + "changer un seul caractere de l'un ou de l'autre la rend "
                    + "invalide. C'est pourquoi un attaquant qui LIT un jeton "
                    + "ne peut pas le MODIFIER — et pourquoi le lire lui "
                    + "suffit s'il se contente de le rejouer.");
            System.out.println();
            Console.texte("L'avant-derniere ligne est la plus instructive. "
                    + "Signer en HMAC avec la cle publique RSA est une "
                    + "attaque reelle contre les bibliotheques qui lisent "
                    + "l'algorithme DANS le jeton : la cle publique etant "
                    + "publique, n'importe qui fabrique alors un jeton "
                    + "valide. Spring impose l'algorithme a la construction "
                    + "du decodeur, et la question ne se pose pas.");

            Console.titre(3, "CE QUE LE DECODEUR VERIFIE VRAIMENT");
            var valide = decodeur.decode(jeton);
            Console.ligne("signature", "RS256, contre la cle publique", 24);
            Console.ligne("emetteur (iss)", String.valueOf(valide.getIssuer()), 24);
            Console.ligne("sujet (sub)", valide.getSubject(), 24);
            Console.ligne("emis le (iat)", String.valueOf(valide.getIssuedAt()), 24);
            Console.ligne("expire le (exp)", String.valueOf(valide.getExpiresAt()), 24);
            Console.ligne("duree de vie",
                    Duration.between(valide.getIssuedAt(), valide.getExpiresAt())
                            .toMinutes() + " minutes", 24);
            Console.ligne("identifiant (jti)", String.valueOf(valide.getId()), 24);
            System.out.println();
            Console.texte("Le `jti` est l'identifiant unique du jeton. Il ne "
                    + "sert a rien tant qu'on ne tient pas une liste — et "
                    + "tenir une liste, c'est justement renoncer au sans-etat. "
                    + "C'est le compromis de la section suivante.");

            Console.titre(4, "LE TALON D'ACHILLE : REVOQUER L'IRREVOCABLE");
            var connexion = banc.poster("/api/public/connexion",
                    "{\"identifiant\":\"karim\",\"motDePasse\":\"motdepasse\"}");
            String acces = connexion.valeur("access_token");
            String rafraichissement = connexion.valeur("refresh_token");
            Console.ligne("karim se connecte",
                    "un access token + un refresh token", 34);
            Console.ligne("   GET /api/moi",
                    String.valueOf(banc.obtenirAvecJeton("/api/moi", acces).code()), 34);
            System.out.println();
            Console.sousTitre("On supprime le compte de karim — il est renvoye, "
                    + "banni, compromis :");
            utilisateurs.retirer("karim");
            jetons.revoquer(rafraichissement);
            Console.ligne("le compte existe encore ?",
                    utilisateurs.existe("karim") ? "oui" : "non", 34);
            Console.ligne("son refresh token est-il valable ?",
                    jetons.porteurDu(rafraichissement).isPresent() ? "oui" : "non", 38);
            System.out.println();
            var apresRevocation = banc.obtenirAvecJeton("/api/moi", acces);
            var rafraichir = banc.poster("/api/public/rafraichir",
                    "{\"refresh_token\":\"" + rafraichissement + "\"}");
            Console.tableau(List.of("apres la revocation", "code", "verdict"),
                    List.of(
                    List.of("GET /api/moi, avec l'access token",
                            String.valueOf(apresRevocation.code()),
                            apresRevocation.code() == 200
                                    ? "PASSE ENCORE" : "refuse"),
                    List.of("POST /api/public/rafraichir",
                            String.valueOf(rafraichir.code()),
                            rafraichir.code() == 200 ? "passe" : "refuse")),
                    List.of(38, 8, 16));
            System.out.println();
            Console.texte("Le compte n'existe plus, le refresh token est "
                    + "revoque — et l'access token continue de fonctionner. "
                    + "Il le fera jusqu'a son expiration, parce que le "
                    + "serveur ne consulte RIEN pour le valider : il verifie "
                    + "une signature et lit une date. On ne peut pas revoquer "
                    + "ce qu'on ne stocke pas.");
            System.out.println();
            Console.ligne("duree de vie de l'access token",
                    ServiceDeJetons.DUREE_ACCES.toMinutes() + " minutes", 34);
            Console.ligne("fenetre d'exploitation d'un jeton vole",
                    "au pire " + ServiceDeJetons.DUREE_ACCES.toMinutes()
                    + " minutes", 40);
            System.out.println();
            Console.texte("C'est pour cela que l'access token est court, et "
                    + "que le refresh token — long — est stocke et donc "
                    + "revocable. La duree de l'access token EST la fenetre "
                    + "d'exploitation : cinq minutes est un choix, une heure "
                    + "en est un autre, et « une semaine » n'en est pas un.");

            Console.titre(5, "LE JWKS : CE QUI SORT, ET CE QUI NE SORT PAS");
            var jwks = banc.obtenir("/oauth2/jwks");
            Console.ligne("GET /oauth2/jwks", String.valueOf(jwks.code()), 30);
            System.out.println();
            for (var ligne : couper(jwks.corps())) {
                Console.texte(ligne, 6);
            }
            System.out.println();
            Console.tableau(List.of("le document contient", "present ?"), List.of(
                    List.of("n — le modulo de la cle publique",
                            jwks.contient("\"n\"") ? "oui" : "non"),
                    List.of("e — l'exposant public",
                            jwks.contient("\"e\"") ? "oui" : "non"),
                    List.of("d — l'exposant PRIVE",
                            jwks.contient("\"d\"") ? "OUI — FUITE" : "non"),
                    List.of("p, q — les facteurs premiers",
                            jwks.contient("\"p\"") ? "OUI — FUITE" : "non")),
                    List.of(38, 14));
            System.out.println();
            Console.texte("Un JWKS publie la cle PUBLIQUE, et rien d'autre. "
                    + "C'est ce qui permet a dix services de valider les "
                    + "jetons d'un meme emetteur sans qu'aucun puisse en "
                    + "fabriquer. Verifier une signature ne demande jamais la "
                    + "cle privee — la ligne `d` ci-dessus doit rester "
                    + "absente, et le test qui le verifie est le plus court "
                    + "du projet.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La difference entre un access token et un ID "
                    + "token, ce que Spring fait d'un `issuer-uri`, et "
                    + "combien de fois il telecharge les cles pour cent "
                    + "requetes.");
            System.out.println();
        }
    }

    /** Soumet un jeton au décodeur et rend ce qu'il en dit. */
    private static List<String> essayer(JwtDecoder decodeur, String quoi,
                                        String jeton) {
        try {
            var decode = decodeur.decode(jeton);
            return List.of(quoi, "ACCEPTE",
                    "sujet " + decode.getSubject() + ", roles "
                    + fr.portail.securite.ConvertisseurDeRoles.rolesDu(decode));
        } catch (JwtException refus) {
            return List.of(quoi, "refuse", court(refus.getMessage()));
        }
    }

    private static String court(String message) {
        if (message == null) {
            return "(sans message)";
        }
        String plat = message.replaceAll("\\s+", " ").strip();
        return plat.length() <= 38 ? plat : plat.substring(0, 35) + "...";
    }

    /** Coupe un JSON plat en lignes lisibles, sans bibliothèque. */
    private static List<String> couper(String json) {
        return java.util.Arrays.stream(json
                        .replace("{", "{\n ")
                        .replace(",\"", ",\n \"")
                        .replace("}", "\n}")
                        .split("\n"))
                .map(String::strip)
                .filter(l -> !l.isEmpty())
                .map(l -> l.length() <= 66 ? l : l.substring(0, 63) + "...")
                .toList();
    }
}
