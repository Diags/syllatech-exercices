package fr.portail.chapitres;

import fr.portail.deploiement.AuditImage;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 6 — Deploiement complet.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Deploiement
 * </pre>
 *
 * <p>⚠️ AUCUNE IMAGE N'EST CONSTRUITE, ET AUCUN DOCKER N'EST REQUIS. Ce
 * chapitre AUDITE les deux Dockerfile livres dans ce depot, regle par regle.
 * C'est un controle de configuration — comme un linter — et il attrape ce
 * qui manque le plus souvent : l'oubli.
 */
public final class Chapitre6Deploiement {

    private Chapitre6Deploiement() {
    }

    public static void main(String[] args) {
        System.out.println("""
                1. LE DOCKERFILE LIVRE DANS CE DEPOT, AUDITE
                """);
        String bon = AuditImage.lire("Dockerfile");
        System.out.println("   `deploiement/Dockerfile`, lu sur le disque :\n");
        for (String instruction : AuditImage.instructions(bon)) {
            System.out.printf("      %s%n", couper(instruction, 68));
        }
        System.out.println();
        for (String ligne : AuditImage.rendre(bon)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   ⚠️ Ce n'est pas une illustration : l'audit lit LE FICHIER
                   livre ici. Retirez-en la ligne `USER`, relancez ce
                   chapitre — il le dit.
                """);

        System.out.println("""
                2. LA MESURE QUI TRANCHE : LE MEME PROJET, SANS MULTI-STAGE
                """);
        String naif = AuditImage.lire("Dockerfile.naif");
        System.out.println("   `deploiement/Dockerfile.naif` :\n");
        for (String instruction : AuditImage.instructions(naif)) {
            System.out.printf("      %s%n", couper(instruction, 68));
        }
        System.out.println();
        for (String ligne : AuditImage.rendre(naif)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   Il FONCTIONNE. L'application demarre et repond — c'est ce
                   qui le rend dangereux : rien n'echoue, rien n'avertit.

                   ⚠️ Et ce que l'audit ne dit pas, parce qu'il ne construit
                   rien : la difference de TAILLE. `maven:3-eclipse-temurin-25`
                   pese pres de 800 Mo, `eclipse-temurin:25-jre-alpine` une
                   centaine. Le premier embarque un compilateur, Maven, et le
                   depot `.m2` telecharge pendant le build — tout cela dans
                   l'image livree, sur chaque noeud, dans chaque registre.
                """);

        System.out.println("""
                3. LE SECRET DANS L'IMAGE : CE QU'IL EN COUTE VRAIMENT
                """);
        System.out.printf("   %-52s %s%n", "INSTRUCTION", "VERDICT DE L'AUDIT");
        for (String instruction : List.of(
                "ENV PORTAIL_JWT_CLE=cle-de-production-tres-secrete",
                "ENV SPRING_PROFILES_ACTIVE=production",
                "ARG DB_PASSWORD=motdepasse",
                "ENV PORTAIL_JWT_CLE",
                "ENV TZ=Europe/Paris")) {
            boolean secret = AuditImage.sentLeSecret(instruction);
            System.out.printf("   %-52s %s%n", couper(instruction, 50),
                    secret ? "⚠️ SECRET DANS L'IMAGE" : "acceptable");
        }

        System.out.println("""

                   ⚠️ UN SECRET DANS UNE IMAGE N'EST PAS « CACHE DEDANS » : il
                   est dans les METADONNEES. `docker history` le montre en une
                   commande, sans meme demarrer le conteneur — et cela vaut
                   pour un `ARG` autant que pour un `ENV`, y compris quand la
                   couche suivante l'efface.

                   La consequence pratique : pousser l'image dans un registre,
                   c'est publier le secret. Le retirer du Dockerfile plus tard
                   ne change rien — l'ancienne couche reste, et elle se tire.
                   Il faut faire TOURNER la cle.

                   La regle, c'est celle du manifeste 12-factor : la
                   configuration arrive au LANCEMENT, par des variables
                   d'environnement ou un gestionnaire de secrets. L'artefact
                   reste le meme de dev en prod ; seul le contexte change.
                """);

        System.out.println("""
                4. LE MEME ARTEFACT PARTOUT, ET CE QUE CELA SUPPOSE
                """);
        Map<String, String> configuration = new LinkedHashMap<>();
        configuration.put("SPRING_DATASOURCE_URL", "l'URL de la base");
        configuration.put("PORTAIL_JWT_CLE", "la cle de signature des jetons");
        configuration.put("PORTAIL_STRIPE_WEBHOOK", "le secret du webhook");
        configuration.put("PORTAIL_ORIGINES", "les origines CORS autorisees");

        System.out.printf("   %-30s %s%n", "VARIABLE", "CE QU'ELLE PORTE");
        configuration.forEach((nom, role) ->
                System.out.printf("   %-30s %s%n", nom, role));

        System.out.printf("%n   Et telles qu'elles sont lues dans "
                          + "`application.properties` :%n%n");
        System.out.println("""
                      portail.jwt.cle=${PORTAIL_JWT_CLE:cle-de-developpement-…}

                   ⚠️ La valeur apres les deux-points est un REPLI de
                   developpement, pas une valeur de production. Elle rend le
                   projet demarrable apres un clone — et c'est precisement ce
                   qui la rend dangereuse : une application qui demarre avec
                   une cle par defaut ne se plaint jamais.

                   La parade se pose en une ligne : sur le profil
                   `production`, on RETIRE le repli. L'application refuse
                   alors de demarrer sans la variable — et un refus de
                   demarrage vaut mille fois mieux qu'un portail signant ses
                   jetons avec la cle qui figure dans le depot public.
                """);

        System.out.println("""
                5. CE QUE CET AUDIT NE PROUVE PAS
                """);
        System.out.println("""
                   Il lit un texte. Il ne construit rien, ne lance rien, et
                   ne mesure aucune taille d'image. C'est un controle de
                   CONFIGURATION, au meme titre qu'un linter — il attrape
                   l'oubli, jamais la vulnerabilite.

                   Ce qui le rend utile malgre cela : l'oubli est de tres
                   loin le cas le plus frequent, et cet audit tient dans une
                   integration continue en dix lignes. Un `USER` retire
                   « juste pour deboguer » un vendredi soir arrive en
                   production le lundi — sauf s'il fait echouer la CI.

                   Ce qu'il faudrait en plus, et qui demande un demon :
                   scanner l'image (Trivy, Grype) pour les CVE de sa base,
                   et verifier sa taille reelle. Les deux se branchent au
                   meme endroit du pipeline.
                """);
    }

    private static String couper(String texte, int largeur) {
        return texte.length() <= largeur ? texte
                : texte.substring(0, largeur - 1) + "…";
    }
}
