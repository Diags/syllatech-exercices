package fr.portail.chapitres;

import fr.portail.domaine.Compte;
import fr.portail.domaine.CompteRepository;
import fr.portail.securite.FiltreJwt;
import fr.portail.securite.Jeton;
import java.time.Instant;
import java.util.Base64;
import java.util.Map;

/**
 * Chapitre 4 — Securite : Spring Security + JWT.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Jwt
 * </pre>
 *
 * <p>Un vrai portail, de vrais jetons signes en HMAC-SHA256. Ce chapitre
 * OUVRE la charge utile sans aucune cle, fabrique quatre attaques et les
 * soumet au verificateur, puis mesure ce qu'un JWT ne sait pas faire : se
 * revoquer.
 */
public final class Chapitre4Jwt {

    private Chapitre4Jwt() {
    }

    public static void main(String[] args) {
        try (Banc banc = Banc.demarrer()) {
            System.out.println("""
                    1. UN JWT N'EST PAS CHIFFRE : IL EST ENCODE
                    """);
            String jeton = banc.connecter("awa", "motdepasse");
            String[] parties = jeton.split("\\.");

            System.out.printf("   Le jeton recu, en trois parties :%n%n");
            System.out.printf("      en-tete   : %s%n", parties[0]);
            System.out.printf("      charge    : %s%n", couper(parties[1], 62));
            System.out.printf("      signature : %s%n%n", couper(parties[2], 62));

            System.out.println("   La charge utile, lue SANS AUCUNE CLE :\n");
            System.out.printf("      %s%n", new String(
                    Base64.getUrlDecoder().decode(parties[1])));
            System.out.printf("%n      (soit : %s)%n",
                    Jeton.chargeUtileSansVerification(jeton));

            System.out.println("""

                   ⚠️ TROIS LIGNES DE BASE64, ET C'EST LU. Rien n'est
                   chiffre : la signature garantit que le contenu n'a pas ete
                   MODIFIE, elle ne le cache pas. Collez n'importe quel JWT
                   sur jwt.io, vous verrez la meme chose.

                   La regle qui en decoule tient en une phrase : on ne met
                   jamais dans un JWT ce qu'on ne mettrait pas sur une carte
                   postale. Un identifiant, des roles, une expiration — oui.
                   Une adresse, un salaire, un numero de securite sociale —
                   jamais.
                """);

            System.out.println("""
                    2. QUATRE ATTAQUES, FABRIQUEES ET SOUMISES AU VERIFICATEUR
                    """);
            Jeton verificateur = new Jeton(
                    "cle-de-developpement-a-ne-jamais-utiliser-en-production");
            Instant maintenant = Instant.now();

            System.out.printf("   %-42s %-10s %s%n",
                              "JETON PRESENTE", "VERDICT", "MOTIF");
            verdict(verificateur, jeton, maintenant,
                    "le jeton, tel quel");

            // Attaque 1 : on change un role dans la charge utile.
            String chargeTrafiquee = Base64.getUrlEncoder().withoutPadding()
                    .encodeToString(new String(
                            Base64.getUrlDecoder().decode(parties[1]))
                            .replace("ROLE_USER", "ROLE_ADMIN")
                            .getBytes(java.nio.charset.StandardCharsets.UTF_8));
            verdict(verificateur,
                    parties[0] + "." + chargeTrafiquee + "." + parties[2],
                    maintenant, "un role change en Base64");

            // Attaque 2 : « alg: none », sans signature.
            String enteteNone = Base64.getUrlEncoder().withoutPadding()
                    .encodeToString("{\"alg\":\"none\",\"typ\":\"JWT\"}"
                            .getBytes(java.nio.charset.StandardCharsets.UTF_8));
            verdict(verificateur, enteteNone + "." + parties[1] + ".",
                    maintenant, "alg: none, sans signature");

            // Attaque 3 : signe avec une AUTRE cle.
            String autreCle = new Jeton("une-cle-que-l-attaquant-a-choisie")
                    .signer("awa", java.util.List.of("ROLE_ADMIN"), "access",
                            300, maintenant);
            verdict(verificateur, autreCle, maintenant,
                    "signe avec une autre cle");

            // Attaque 4 : un refresh token presente comme access token.
            String refresh = Banc.entre(banc.post("/api/auth/connexion",
                    """
                    {"identifiant":"awa","motDePasse":"motdepasse"}
                    """, null).corps(), "\"refreshToken\":\"", "\"");
            verdict(verificateur, refresh, maintenant,
                    "un REFRESH token comme access");

            System.out.println("""

                   ⚠️ LE VERDICT NE DEPEND JAMAIS DU JETON LUI-MEME.
                   L'algorithme est impose par le serveur, jamais lu dans
                   l'en-tete. Une bibliotheque qui fait confiance au champ
                   `alg` accepte un jeton qui se declare non signe — c'est
                   une faille reelle, publiee contre plusieurs implantations.

                   Remarquez d'ailleurs le motif de cette ligne-la : « format
                   invalide », et non « signature invalide ». Un jeton
                   « alg: none » se termine par un point suivi de RIEN ; il
                   n'a que deux parties, et il est refuse avant meme qu'on
                   calcule quoi que ce soit. Accepter un jeton de deux
                   parties est exactement ce que faisaient les
                   implantations vulnerables.

                   ⚠️ Et la derniere ligne merite un arret : un refresh token
                   est signe par la MEME cle qu'un access token. Sans un
                   champ `usage` verifie, il serait accepte partout — et
                   toute la logique des deux durees tomberait, puisque le
                   refresh vit des jours.

                   ⚠️ Enfin, la comparaison de signatures se fait en TEMPS
                   CONSTANT (`MessageDigest.isEqual`). Un `equals` ordinaire
                   s'arrete au premier octet different : le temps de reponse
                   dit alors combien d'octets sont justes.
                """);

            System.out.println("""
                    3. LA MESURE QUI FAIT MAL : CE QU'ON NE PEUT PAS REVOQUER
                    """);
            CompteRepository comptes = banc.bean(CompteRepository.class);
            FiltreJwt filtre = banc.bean(FiltreJwt.class);

            String jetonBilal = banc.connecter("bilal", "motdepasse");
            // ⚠️ On mesure sur `/api/moi`, qui EXIGE une identite. Le
            // faire sur `/api/offres`, route publique, ne prouverait rien :
            // elle repond 200 avec ou sans jeton.
            int avant = banc.get("/api/moi", jetonBilal).statut();

            // Le compte est desactive cote serveur — comme le ferait un
            // administrateur devant un depart ou un incident.
            Compte bilal = comptes.findByIdentifiant("bilal").orElseThrow();
            bilal.desactiver();
            comptes.save(bilal);
            banc.bean(fr.portail.securite.ServiceAuthentification.class)
                    .revoquer("bilal");

            int apres = banc.get("/api/moi", jetonBilal).statut();
            int connexion = banc.post("/api/auth/connexion", """
                    {"identifiant":"bilal","motDePasse":"motdepasse"}
                    """, null).statut();
            int rafraichissement = banc.post("/api/auth/rafraichir", """
                    {"refreshToken":"peu-importe"}
                    """, null).statut();

            System.out.printf("   %-46s %s%n", "APPEL", "STATUT");
            System.out.printf("   %-46s %d%n",
                              "GET /api/moi, avant la desactivation", avant);
            System.out.printf("   %-46s %d%n",
                              "POST /api/auth/connexion, apres", connexion);
            System.out.printf("   %-46s %d%n",
                              "POST /api/auth/rafraichir, apres", rafraichissement);
            System.out.printf("   %-46s %d   ⚠️%n",
                              "GET /api/moi avec l'ANCIEN access token", apres);

            System.out.println("""

                   ⚠️ LE COMPTE EST DESACTIVE, LE REFRESH EST REVOQUE — ET
                   L'ACCESS TOKEN CONTINUE DE FONCTIONNER. Ce n'est pas un
                   defaut de ce projet : c'est la definition meme d'un jeton
                   auto-porteur. Le serveur ne consulte aucune base pour le
                   valider ; il verifie une signature. Il ne PEUT donc pas
                   savoir que le compte a change.

                   On ne peut pas revoquer ce qu'on ne stocke pas.

                   La reponse n'est pas « stocker les access tokens » — cela
                   annulerait l'interet du sans-etat. C'est de les faire
                   vivre COURT : quelques minutes. La fenetre d'exposition
                   devient alors la duree de vie du jeton, et c'est un
                   arbitrage qu'on assume, pas un oubli.
                """);

            System.out.printf("      duree de l'access token de ce portail : %d s%n",
                    banc.bean(fr.portail.securite.ServiceAuthentification.class)
                            .dureeAccess());

            System.out.println("""
                    4. CE QUE LE FILTRE A VU, ET CE QU'AUCUN CONTROLEUR N'A EU A FAIRE
                    """);
            System.out.printf("      requetes traversees    : %d%n",
                              filtre.requetesVues());
            System.out.printf("      jetons acceptes        : %d%n",
                              filtre.jetonsAcceptes());
            System.out.printf("      jetons refuses         : %d%n",
                              filtre.jetonsRefuses());
            System.out.println("""

                   Aucun controleur de ce projet ne lit l'en-tete
                   `Authorization`. Quand le controleur s'execute, l'identite
                   est deja posee — ou la requete a deja ete refusee. Un
                   `if (token == null)` dans un controleur est le signe que
                   ce filtre manque.

                   ⚠️ Et le filtre ne refuse RIEN lui-meme : un jeton absent
                   laisse simplement le contexte vide, et c'est la chaine
                   qui decide si la route l'exige. Melanger les deux roles
                   fabrique des routes publiques qui reclament un jeton sans
                   que personne comprenne pourquoi.
                """);
        }
    }

    private static void verdict(Jeton verificateur, String jeton,
                                Instant maintenant, String libelle) {
        Jeton.Verdict verdict = verificateur.verifier(jeton, "access", maintenant);
        System.out.printf("   %-42s %-10s %s%n", libelle,
                verdict.valide() ? "ACCEPTE" : "⚠️ refuse",
                verdict.motif());
    }

    private static String couper(String texte, int largeur) {
        return texte.length() <= largeur ? texte
                : texte.substring(0, largeur - 1) + "…";
    }
}
