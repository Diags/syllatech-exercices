package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.plateforme.LectureDockerfile;
import fr.portail.plateforme.LectureYaml;
import fr.portail.plateforme.MiseAJourProgressive;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 5 — Kubernetes et Helm.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Kubernetes
 * </pre>
 *
 * <p>Ce chapitre lit deux manifestes du dépôt — l'un soigné, l'autre écrit
 * comme on en voit trop — et compte ce qui manque au second. Puis il déroule
 * l'<strong>arithmétique</strong> d'une mise à jour progressive : combien de
 * pods existent, combien servent du trafic, à chaque étape.
 *
 * <p>⚠️ Aucun cluster n'est joint, et ce n'est pas une limite gênante : ce qui
 * est calculé ici est ce que {@code maxSurge} et {@code maxUnavailable}
 * <em>garantissent</em>, et cela se calcule.
 */
public final class Chapitre5Kubernetes {

    private Chapitre5Kubernetes() {
    }

    private static final Path K8S = Path.of("deploiement", "k8s");
    private static final Path HELM = Path.of("deploiement", "helm");

    public static void main(String[] args) throws Exception {
        Console.utf8();

        var soigne = new LectureYaml(K8S.resolve("deployment.yaml"));
        var bacle = new LectureYaml(K8S.resolve("deployment-sans-sondes.yaml"));

        Console.titre(1, "DEUX MANIFESTES QUI DEMARRENT TOUS LES DEUX");
        Console.tableau(List.of("ce qui est declare", "manifeste soigne",
                "manifeste courant"), List.of(
                ligne("repliques", soigne, bacle, "spec.replicas"),
                ligne("sonde de vivacite", soigne, bacle,
                        "livenessProbe"),
                ligne("sonde de disponibilite", soigne, bacle,
                        "readinessProbe"),
                ligne("limites de ressources", soigne, bacle, "resources"),
                ligne("strategie de mise a jour", soigne, bacle,
                        "spec.strategy.rollingUpdate")),
                List.of(26, 18, 18));
        System.out.println();
        Console.ligne("image du manifeste soigne",
                image(soigne) + "  ("
                + (LectureDockerfile.versionPrecise(image(soigne))
                        ? "version precise" : "TAG MOBILE") + ")", 30);
        Console.ligne("image du manifeste courant",
                image(bacle) + "  ("
                + (LectureDockerfile.versionPrecise(image(bacle))
                        ? "version precise" : "TAG MOBILE") + ")", 30);
        System.out.println();
        Console.texte("Les deux manifestes sont valides, les deux se "
                + "deploient, et les deux font tourner l'application. Ce qui "
                + "les separe n'apparait qu'au premier incident.");
        System.out.println();
        Console.texte("⚠️ Sans SONDE DE DISPONIBILITE, Kubernetes envoie du "
                + "trafic a un pod des que son processus demarre — soit, "
                + "pour une application Spring Boot, plusieurs secondes avant "
                + "qu'elle ne sache repondre. Chaque deploiement produit donc "
                + "une salve d'erreurs 502, et personne ne comprend d'ou "
                + "elles viennent.");
        System.out.println();
        Console.texte("⚠️ Sans LIMITES DE RESSOURCES, un pod qui fuit consomme "
                + "toute la memoire du noeud et fait tomber ses voisins. Les "
                + "`requests`, elles, servent au placement : sans elles, "
                + "l'ordonnanceur entasse les pods au hasard.");
        System.out.println();
        Console.texte("La bonne nouvelle est que ces absences se detectent "
                + "par un outil, exactement comme ci-dessus. C'est le genre "
                + "de verification qui a sa place dans la CI, pas dans une "
                + "relecture.");

        Console.titre(2, "LES DEUX SONDES NE FONT PAS LA MEME CHOSE");
        var conteneur = soigne.premierConteneur();
        Console.tableau(List.of("la sonde", "chemin", "si elle echoue"),
                List.of(
                List.of("vivacite (liveness)",
                        chemin(conteneur, "livenessProbe"),
                        "le conteneur est REDEMARRE"),
                List.of("disponibilite (readiness)",
                        chemin(conteneur, "readinessProbe"),
                        "le pod sort du service")),
                List.of(26, 34, 26));
        System.out.println();
        Console.texte("La distinction est la plus mal comprise de Kubernetes, "
                + "et elle a une consequence directe : une sonde de VIVACITE "
                + "ne doit jamais tester une dependance. Si elle verifie la "
                + "base de donnees et que celle-ci ralentit, Kubernetes "
                + "redemarre tous les pods — ce qui n'aide pas la base, et "
                + "supprime le service.");
        System.out.println();
        Console.texte("La sonde de DISPONIBILITE, elle, doit en tenir compte : "
                + "un pod qui ne peut pas servir doit sortir du service, sans "
                + "etre tue. Spring Boot expose exactement ces deux "
                + "groupes — `/actuator/health/liveness` et "
                + "`/actuator/health/readiness` — et c'est ce que le "
                + "manifeste utilise.");

        Console.titre(3, "UNE MISE A JOUR PROGRESSIVE, POD PAR POD");
        int repliques = soigne.entier("spec.replicas");
        int surge = soigne.entier("spec.strategy.rollingUpdate.maxSurge");
        int indispo = soigne.entier(
                "spec.strategy.rollingUpdate.maxUnavailable");
        Console.ligne("repliques", String.valueOf(repliques), 22);
        Console.ligne("maxSurge", String.valueOf(surge), 22);
        Console.ligne("maxUnavailable", String.valueOf(indispo), 22);
        System.out.println();
        var etapes = MiseAJourProgressive.derouler(repliques, surge, indispo);
        var lignes = new ArrayList<List<String>>();
        for (var etape : etapes) {
            lignes.add(List.of(String.valueOf(etape.numero()),
                    String.valueOf(etape.anciens()),
                    String.valueOf(etape.nouveaux()),
                    String.valueOf(etape.disponibles()),
                    etape.action()));
        }
        Console.tableau(List.of("etape", "v1", "v2", "disponibles", "action"),
                lignes, List.of(8, 6, 6, 14, 20));
        System.out.println();
        Console.ligne("jamais moins de",
                pods(MiseAJourProgressive.creuxDeDisponibilite(etapes)) + " disponibles"
                , 22);
        Console.ligne("jamais plus de",
                pods(MiseAJourProgressive.picDePods(etapes)) + " au total", 22);
        System.out.println();
        Console.texte("Voila ce que ces deux nombres garantissent, et ce n'est "
                + "pas intuitif : `maxSurge` borne le pic de consommation — "
                + "le cluster doit avoir la place — et `maxUnavailable` borne "
                + "le creux de capacite, celui que vos utilisateurs "
                + "ressentent.");

        Console.titre(4, "LE MEME DEPLOIEMENT, TROIS REGLAGES");
        var comparaison = new ArrayList<List<String>>();
        for (var reglage : List.of(new int[] {1, 1}, new int[] {1, 0},
                new int[] {0, 4})) {
            var suite = MiseAJourProgressive.derouler(repliques,
                    reglage[0], reglage[1]);
            comparaison.add(List.of(
                    "surge=" + reglage[0] + " indispo=" + reglage[1],
                    String.valueOf(suite.size() - 1),
                    pods(MiseAJourProgressive.picDePods(suite)),
                    pods(MiseAJourProgressive.creuxDeDisponibilite(suite))));
        }
        Console.tableau(List.of("le reglage", "etapes", "pic de pods",
                "creux de capacite"), comparaison, List.of(24, 10, 14, 18));
        System.out.println();
        Console.texte("La derniere ligne est celle qu'on ecrit sans y penser : "
                + "`maxSurge: 0` et `maxUnavailable: 4` sur quatre "
                + "repliques. Elle ne demande aucune capacite "
                + "supplementaire — et elle descend a ZERO pod disponible. "
                + "C'est une interruption de service, deguisee en « mise a "
                + "jour progressive ».");
        System.out.println();
        Console.texte("La ligne du milieu, `maxUnavailable: 0`, est le reglage "
                + "sans interruption : on cree avant de detruire. Il demande "
                + "de la place dans le cluster, et c'est le seul qui garantit "
                + "la capacite pendant toute l'operation.");
        System.out.println();
        Console.texte("⚠️ Et rien de tout cela ne sert si les sondes de "
                + "disponibilite manquent. Kubernetes compte un pod comme "
                + "« disponible » des qu'il demarre, faute de mieux — les "
                + "garanties ci-dessus portent alors sur des pods qui ne "
                + "repondent pas encore.");

        Console.titre(5, "HELM : CE QUI CHANGE ENTRE DEUX ENVIRONNEMENTS");
        var valeurs = new LectureYaml(HELM.resolve("values.yaml"));
        var production = new LectureYaml(HELM.resolve("values-production.yaml"));
        Console.tableau(List.of("valeur", "recette", "production"), List.of(
                List.of("replicaCount", valeurs.texte("replicaCount"),
                        production.texte("replicaCount")),
                List.of("cpu demande", valeurs.texte("resources.requests.cpu"),
                        production.texte("resources.requests.cpu")),
                List.of("memoire limite",
                        valeurs.texte("resources.limits.memory"),
                        production.texte("resources.limits.memory")),
                List.of("profil Spring", valeurs.texte("profil"),
                        production.texte("profil")),
                List.of("version de l'image", valeurs.texte("image.tag"),
                        production.texte("image.tag") == null
                                ? "(heritee : " + valeurs.texte("image.tag")
                                  + ")" : production.texte("image.tag"))),
                List.of(22, 16, 22));
        System.out.println();
        Console.texte("Un seul chart, deux fichiers de valeurs. Le manifeste "
                + "n'est ecrit qu'une fois ; ce qui change d'un environnement "
                + "a l'autre tient en quelques lignes, et se relit en un coup "
                + "d'oeil.");
        System.out.println();
        Console.texte("Notez la derniere ligne : le fichier de production ne "
                + "redefinit PAS la version de l'image, donc elle est "
                + "heritee. C'est la force et le danger des valeurs Helm — "
                + "ce qui n'est pas ecrit vient d'ailleurs, et il faut "
                + "savoir d'ou.");
        System.out.println();
        Console.texte("⚠️ C'est aussi pourquoi `helm template` existe : il "
                + "rend le manifeste FINAL, valeurs appliquees, avant tout "
                + "deploiement. Le lire est le seul moyen de savoir ce qui "
                + "part vraiment — et c'est exactement ce que ce chapitre "
                + "fait a la main, sur les deux fichiers de valeurs.");

        Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("La securite a la passerelle et l'observabilite : une "
                + "requete sans jeton, la meme avec, et un identifiant de "
                + "correlation qui traverse tout le systeme.");
        System.out.println();
    }

    /** « 1 pod », « 4 pods » — le pluriel compte quand on lit un tableau. */
    private static String pods(int nombre) {
        return nombre + (nombre > 1 ? " pods" : " pod");
    }

    private static List<String> ligne(String quoi, LectureYaml soigne,
                                      LectureYaml bacle, String chemin) {
        return List.of(quoi, present(soigne, chemin), present(bacle, chemin));
    }

    /** Un réglage est-il présent ? Cherché dans le pod comme à la racine. */
    private static String present(LectureYaml manifeste, String chemin) {
        if (manifeste.existe(chemin)) {
            Object valeur = manifeste.valeur(chemin);
            return valeur instanceof Number nombre ? String.valueOf(nombre)
                    : "declare";
        }
        var conteneur = manifeste.premierConteneur();
        return conteneur.containsKey(chemin) ? "declare" : "ABSENT";
    }

    private static String image(LectureYaml manifeste) {
        Object image = manifeste.premierConteneur().get("image");
        return image == null ? "(aucune)" : String.valueOf(image);
    }

    @SuppressWarnings("unchecked")
    private static String chemin(Map<String, Object> conteneur, String sonde) {
        Object valeur = conteneur.get(sonde);
        if (!(valeur instanceof Map<?, ?> carte)) {
            return "(absente)";
        }
        Object http = ((Map<String, Object>) carte).get("httpGet");
        if (!(http instanceof Map<?, ?> requete)) {
            return "(pas HTTP)";
        }
        return String.valueOf(((Map<String, Object>) requete).get("path"));
    }
}
