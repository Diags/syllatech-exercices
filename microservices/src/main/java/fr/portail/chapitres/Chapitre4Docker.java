package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.plateforme.LectureDockerfile;
import fr.portail.plateforme.LectureYaml;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 4 — Docker : conteneuriser les services.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Docker
 * </pre>
 *
 * <p>« Le build multi-stage garde ces images minces et sûres. » Ce chapitre
 * <strong>lit le Dockerfile du projet</strong> et répond aux questions qui
 * comptent : combien d'étages, ce qui franchit la frontière entre eux, sous
 * quel utilisateur le processus tourne, et si l'ordre des couches permet à
 * Docker de réutiliser son cache.
 *
 * <p>⚠️ Aucun démon Docker n'est nécessaire, et c'est voulu : ce qui est
 * examiné est ce que le fichier <em>décide</em>. Un vérificateur de CI fait
 * exactement cela, et il attrape ce qu'une revue humaine laisse toujours
 * passer.
 */
public final class Chapitre4Docker {

    private Chapitre4Docker() {
    }

    private static final Path DEPLOIEMENT = Path.of("deploiement");

    public static void main(String[] args) throws Exception {
        Console.utf8();

        var dockerfile = new LectureDockerfile(DEPLOIEMENT.resolve("Dockerfile"));

        Console.titre(1, "CE QUE LE MULTI-ETAPES CHANGE VRAIMENT");
        var lignes = new ArrayList<List<String>>();
        for (var etage : dockerfile.etages()) {
            lignes.add(List.of(
                    etage.nom() == null ? "(final)" : etage.nom(),
                    etage.base(),
                    String.valueOf(etage.instructions().size())));
        }
        Console.tableau(List.of("etage", "image de base", "instructions"),
                lignes, List.of(14, 34, 14));
        System.out.println();
        Console.sousTitre("Ce que l'etage final recupere du precedent :");
        for (var copie : dockerfile.copiesDepuisUnAutreEtage()) {
            Console.texte("→ " + copie, 5);
        }
        System.out.println();
        Console.texte("Une seule ligne franchit la frontiere : le jar. Tout le "
                + "reste — Maven, le JDK complet, le cache des dependances, "
                + "les sources — reste dans l'etage de construction et "
                + "n'existe pas dans l'image livree.");
        System.out.println();
        Console.texte("Ce n'est pas qu'une question de taille. Une image qui "
                + "embarque un compilateur et des sources embarque aussi leurs "
                + "failles : chaque paquet present est une surface d'attaque "
                + "et une ligne dans un rapport de vulnerabilites. Le "
                + "multi-etapes est une mesure de SECURITE autant que de "
                + "poids.");

        Console.titre(2, "QUATRE DECISIONS QUE LE FICHIER PREND POUR VOUS");
        var naif = new LectureDockerfile(
                DEPLOIEMENT.resolve("Dockerfile.naif"));
        Console.tableau(List.of("la question", "ce projet", "l'ecriture naive",
                "pourquoi"), List.of(
                List.of("etages", String.valueOf(dockerfile.etages().size()),
                        String.valueOf(naif.etages().size()),
                        "le JDK reste-t-il en prod ?"),
                List.of("non-root ?", oui(dockerfile.nonRoot()),
                        oui(naif.nonRoot()),
                        "une evasion donne root sur l'hote"),
                List.of("forme exec ?", oui(dockerfile.entreeEnFormeExec()),
                        oui(naif.entreeEnFormeExec()),
                        "sinon pas de SIGTERM pour la JVM"),
                List.of("cache optimise ?",
                        oui(dockerfile.cacheDesDependancesOptimise()),
                        oui(naif.cacheDesDependancesOptimise()),
                        "sinon on retelecharge tout")),
                List.of(20, 12, 18, 34));
        System.out.println();
        Console.texte("Les deux fichiers sont dans ce depot, et les deux "
                + "construisent une image qui tourne. C'est bien la le "
                + "probleme : aucune de ces quatre decisions n'est obligatoire "
                + "pour Docker, et leurs consequences ne se voient qu'en "
                + "production — ou dans un rapport d'audit.");
        System.out.println();
        Console.texte("⚠️ Celui de la forme EXEC est le plus vicieux. En forme "
                + "shell, c'est `/bin/sh` qui devient PID 1 : il recoit le "
                + "SIGTERM de l'orchestrateur, ne le transmet pas, et la JVM "
                + "est tuee au bout du delai de grace — sans arret propre, "
                + "sans vidage des files, sans desinscription de l'annuaire.");

        Console.titre(3, "LES VERSIONS D'IMAGE, ET LE PIEGE DE `latest`");
        var bonne = "registre.interne/portail/offres-service:1.4.0";
        var mauvaise = "registre.interne/portail/offres-service:latest";
        Console.tableau(List.of("l'image demandee", "version precise ?"),
                List.of(
                List.of(bonne, LectureDockerfile.versionPrecise(bonne)
                        ? "oui" : "NON"),
                List.of(mauvaise, LectureDockerfile.versionPrecise(mauvaise)
                        ? "oui" : "NON")),
                List.of(48, 20));
        System.out.println();
        Console.texte("`latest` n'est pas une version : c'est un tag mobile. "
                + "Deux pods demarres a une heure d'intervalle peuvent tourner "
                + "sur deux images differentes, et rien dans le cluster ne le "
                + "dira. Revenir en arriere devient impossible, puisque "
                + "l'ancienne image n'a plus de nom.");
        System.out.println();
        Console.texte("La regle du cours est exacte, et elle merite d'etre "
                + "verifiee par un outil plutot que par une relecture : une "
                + "image se tague avec une version precise, et l'outil de CI "
                + "refuse `latest`.");

        Console.titre(4, "CE QUE `depends_on` GARANTIT, ET CE QU'IL NE GARANTIT PAS");
        var compose = new LectureYaml(DEPLOIEMENT.resolve("compose.yaml"));
        var services = compose.racine().get("services");
        var suivi = new ArrayList<List<String>>();
        if (services instanceof Map<?, ?> carte) {
            for (var entree : carte.entrySet()) {
                String nom = String.valueOf(entree.getKey());
                Object valeur = entree.getValue();
                String dependances = "-";
                String attenteReelle = "non";
                if (valeur instanceof Map<?, ?> service) {
                    Object depends = service.get("depends_on");
                    if (depends != null) {
                        dependances = String.valueOf(depends)
                                .replaceAll("[{}\\[\\]]", "");
                        attenteReelle = String.valueOf(depends)
                                .contains("service_healthy") ? "OUI" : "non";
                    }
                }
                suivi.add(List.of(nom, court(dependances, 30), attenteReelle));
            }
        }
        Console.tableau(List.of("service", "depends_on",
                "attend la DISPONIBILITE"), suivi, List.of(22, 32, 12));
        System.out.println();
        Console.texte("`depends_on: [eureka]` attend que le conteneur soit "
                + "DEMARRE — c'est-a-dire que son processus existe. Pas qu'il "
                + "reponde. Un service Spring Boot met plusieurs secondes a "
                + "ouvrir son port : pendant ce temps, ses dependants sont "
                + "deja partis.");
        System.out.println();
        Console.texte("La colonne de droite montre la difference : seule la "
                + "forme longue, avec `condition: service_healthy` et un "
                + "`healthcheck`, attend vraiment. C'est aussi la seule qui "
                + "coute quelque chose a ecrire — d'ou sa rarete.");
        System.out.println();
        Console.texte("⚠️ Et meme avec elle, la regle reste : un service doit "
                + "savoir REESSAYER. C'est la raison d'etre du `optional:` "
                + "devant l'import de configuration que le chapitre 2 "
                + "montrait — un service qui refuse de demarrer parce que sa "
                + "dependance n'est pas prete transforme un redemarrage en "
                + "panne generale.");

        Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Kubernetes : ce qu'un manifeste declare, ce qu'il "
                + "oublie, et le calcul exact d'une mise a jour progressive "
                + "— pod par pod.");
        System.out.println();
    }

    private static String oui(boolean vrai) {
        return vrai ? "oui" : "NON";
    }

    private static String court(String texte, int largeur) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= largeur ? plat
                : plat.substring(0, largeur - 3) + "...";
    }
}
