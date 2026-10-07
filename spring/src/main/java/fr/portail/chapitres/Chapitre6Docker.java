package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.zip.ZipFile;

/**
 * Chapitre 6 — Docker et AWS.
 *
 * <pre>
 * mvn -q package -DskipTests
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Docker
 * </pre>
 *
 * <p>« Chaque rebuild re-télécharge toutes les dépendances, car la moindre
 * modification de code invalide la couche entière. » C'est une affirmation
 * sur des <strong>tailles</strong> : ce chapitre les pèse. Si le jar
 * exécutable a été construit, il l'ouvre et lit le découpage en couches que
 * Spring Boot y a inscrit ; sinon, il pèse le classpath, ce qui donne le même
 * rapport.
 *
 * <p>Il vérifie aussi ce que la commande d'extraction est devenue : le
 * {@code -Djarmode=layertools} des tutoriels a été remplacé, et ce chapitre
 * le demande au jar lui-même plutôt qu'à une note de version.
 */
public final class Chapitre6Docker {

    private Chapitre6Docker() {
    }

    public static void main(String[] args) throws Exception {
        Console.utf8();

        Console.titre(1, "CE QUE PESE CETTE APPLICATION");
        var notre = new ArrayList<Path>();
        var dependances = new ArrayList<Path>();
        for (var entree : System.getProperty("java.class.path", "")
                .split(File.pathSeparator)) {
            var chemin = Path.of(entree);
            if (!Files.exists(chemin)) {
                continue;
            }
            (entree.endsWith(".jar") ? dependances : notre).add(chemin);
        }
        long octetsNotres = taille(notre);
        long octetsDependances = taille(dependances);
        Console.tableau(List.of("ce qui compose l'application", "elements",
                "taille"), List.of(
                List.of("notre code compile", String.valueOf(notre.size()),
                        enKio(octetsNotres)),
                List.of("les dependances (jars)", String.valueOf(dependances.size()),
                        enKio(octetsDependances))),
                List.of(30, 12, 14));
        System.out.println();
        Console.ligne("part de notre code dans le total",
                "%.2f %%".formatted(100.0 * octetsNotres
                        / (octetsNotres + octetsDependances)), 38);
        System.out.println();
        Console.texte("C'est tout l'argument du chapitre, en un pourcentage. "
                + "Ce qui change a chaque commit represente moins d'un "
                + "centieme de l'image ; ce qui ne change presque jamais en "
                + "represente le reste. Copier le tout dans une seule couche "
                + "Docker fait refaire 99 % du travail a chaque "
                + "modification.");

        Console.titre(2, "LE DECOUPAGE QUE SPRING BOOT INSCRIT DANS LE JAR");
        var jar = trouverLeJar();
        if (jar == null) {
            Console.texte("Le jar executable n'a pas ete construit. Lancez "
                    + "`mvn package -DskipTests`, puis relancez ce chapitre : "
                    + "il ouvrira le jar et lira son fichier `layers.idx`.");
        } else {
            Console.ligne("jar", jar.getFileName().toString(), 24);
            Console.ligne("taille", enKio(Files.size(jar)), 24);
            System.out.println();
            var couches = lireLesCouches(jar);
            if (couches.isEmpty()) {
                Console.texte("Pas de `layers.idx` dans ce jar : le decoupage "
                        + "en couches n'est pas actif.");
            } else {
                Console.tableau(List.of("couche", "change", "entrees"),
                        couches, List.of(20, 26, 12));
                System.out.println();
                Console.texte("L'ordre n'est pas alphabetique : il va du plus "
                        + "stable au plus volatil. Docker empile ses couches "
                        + "dans cet ordre, et n'invalide que celles qui "
                        + "suivent la premiere qui a bouge. Mettre "
                        + "`application` en dernier est donc la totalite de "
                        + "l'optimisation.");
            }

            Console.titre(3, "LA COMMANDE D'EXTRACTION A CHANGE DE NOM");
            var avecLayertools = lancerJava("-Djarmode=layertools", "-jar",
                    jar.toString(), "list");
            var avecTools = lancerJava("-Djarmode=tools", "-jar",
                    jar.toString(), "list-layers");
            Console.ligne("-Djarmode=layertools list",
                    resumer(avecLayertools), 34);
            Console.ligne("-Djarmode=tools list-layers",
                    resumer(avecTools), 34);
            System.out.println();
            Console.texte("`layertools` est le mode que citent la plupart des "
                    + "tutoriels — et les Dockerfile copies depuis ces "
                    + "tutoriels. Il a ete remplace par `-Djarmode=tools`, "
                    + "qui fait davantage : extraire les couches, mais aussi "
                    + "produire un jar « decompresse » plus rapide a demarrer. "
                    + "La sortie ci-dessus dit lequel des deux repond sur "
                    + "CETTE version.");
        }

        Console.titre(4, "LE DOCKERFILE QUI EN DECOULE");
        for (var ligne : DOCKERFILE) {
            Console.texte(ligne, 5);
        }
        System.out.println();
        Console.texte("Deux etapes : la premiere extrait, la seconde n'emporte "
                + "que le resultat. L'image finale ne contient donc ni le jar "
                + "d'origine, ni Maven, ni le code source — seulement ce qui "
                + "tourne. Et `JarLauncher` demarre l'application depuis les "
                + "repertoires extraits, sans reconstruire de jar.");

        Console.titre(5, "LA SONDE QUE L'ORCHESTRATEUR INTERROGE");
        try (var banc = Banc.demarrer()) {
            var client = banc.anonyme();
            var sante = Banc.obtenir(client, "/actuator/health");
            Console.ligne("GET /actuator/health",
                    sante.valeur() + " — " + sante.apercu(44), 30);
            var connecte = banc.comme("awa", "motdepasse");
            var vivantAnonyme = Banc.obtenir(client, "/actuator/health/liveness");
            var vivantConnecte = Banc.obtenir(connecte, "/actuator/health/liveness");
            var pretConnecte = Banc.obtenir(connecte, "/actuator/health/readiness");
            Console.ligne("GET /actuator/health/liveness (anonyme)",
                    String.valueOf(vivantAnonyme.valeur()), 42);
            Console.ligne("GET /actuator/health/liveness (authentifie)",
                    String.valueOf(vivantConnecte.valeur()), 42);
            Console.ligne("GET /actuator/health/readiness (authentifie)",
                    String.valueOf(pretConnecte.valeur()), 42);
            System.out.println();
            Console.texte("Deux causes differentes, et il faut les separer.");
            System.out.println();
            Console.texte("La premiere ligne repond 401 alors que "
                    + "`/actuator/health` est ouvert : la regle "
                    + "`requestMatchers(\"/actuator/health\")` designe ce "
                    + "chemin EXACTEMENT, pas ce qui est en dessous. Il "
                    + "faudrait ecrire `/actuator/health/**`. Un "
                    + "orchestrateur branche sur `/actuator/health/readiness` "
                    + "recevrait donc un 401 et conclurait que le service est "
                    + "mort.");
            System.out.println();
            Console.texte("Les deux suivantes repondent 404 une fois "
                    + "authentifiees : les sondes existent, mais ne sont pas "
                    + "actives par defaut hors Kubernetes. Il faut "
                    + "`management.endpoint.health.probes.enabled=true`. "
                    + "C'est la ligne qui manque au premier deploiement, avec "
                    + "pour symptome des redemarrages en boucle que rien "
                    + "n'explique.");
            System.out.println();
            Console.texte("La difference entre les deux sondes compte : "
                    + "`liveness` repond « faut-il me tuer et me relancer ? », "
                    + "`readiness` repond « peut-on m'envoyer du trafic ? ». "
                    + "Brancher l'orchestrateur sur la mauvaise fait tuer un "
                    + "service qui attendait simplement sa base.");
        }

        Console.titre(6, "CE QUE CE PROJET A MESURE");
        Console.tableau(List.of("chapitre", "la mesure qui compte"), List.of(
                List.of("1", "200 requetes : un singleton avec etat rend le nom d'un autre client"),
                List.of("2", "le rapport d'auto-configuration, decision par decision"),
                List.of("3", "l'entite publiee laisse fuir `salaireReel` et `noteInterne`"),
                List.of("4", "findAll() : 1+N requetes ; join fetch : 1"),
                List.of("5", "60 requetes refusees, 0 entree dans le controleur"),
                List.of("6", "notre code pese moins de 1 % de l'image")),
                List.of(12, 66));
        System.out.println();
        Console.texte("Aucune de ces six lignes n'est une opinion. Relancez "
                + "les chapitres : les chiffres bougeront un peu, les "
                + "conclusions non.");
        System.out.println();
    }

    private static final List<String> DOCKERFILE = List.of(
            "FROM eclipse-temurin:25-jre AS extraction",
            "WORKDIR /extrait",
            "COPY target/spring-portail-1.0.0.jar app.jar",
            "RUN java -Djarmode=tools -jar app.jar extract --layers --launcher",
            "",
            "FROM eclipse-temurin:25-jre",
            "WORKDIR /app",
            "COPY --from=extraction /extrait/app/dependencies/ ./",
            "COPY --from=extraction /extrait/app/spring-boot-loader/ ./",
            "COPY --from=extraction /extrait/app/snapshot-dependencies/ ./",
            "COPY --from=extraction /extrait/app/application/ ./",
            "ENTRYPOINT [\"java\", "
                    + "\"org.springframework.boot.loader.launch.JarLauncher\"]");

    private static Path trouverLeJar() throws java.io.IOException {
        var cible = Path.of("target");
        if (!Files.isDirectory(cible)) {
            return null;
        }
        try (var fichiers = Files.list(cible)) {
            return fichiers
                    .filter(p -> p.getFileName().toString().endsWith(".jar"))
                    .filter(p -> !p.getFileName().toString().endsWith("-plain.jar"))
                    .findFirst().orElse(null);
        }
    }

    /** Lit le {@code layers.idx} que le plugin Spring Boot a écrit dans le jar. */
    private static List<List<String>> lireLesCouches(Path jar) throws Exception {
        var explications = java.util.Map.of(
                "dependencies", "presque jamais",
                "spring-boot-loader", "jamais",
                "snapshot-dependencies", "rarement",
                "application", "a chaque commit");
        var couches = new ArrayList<List<String>>();
        try (var archive = new ZipFile(jar.toFile())) {
            var entree = archive.getEntry("BOOT-INF/layers.idx");
            if (entree == null) {
                return List.of();
            }
            String courante = null;
            int entrees = 0;
            try (var lecteur = new java.io.BufferedReader(
                    new java.io.InputStreamReader(archive.getInputStream(entree),
                            java.nio.charset.StandardCharsets.UTF_8))) {
                String ligne;
                while ((ligne = lecteur.readLine()) != null) {
                    if (ligne.startsWith("- \"")) {
                        if (courante != null) {
                            couches.add(List.of(courante,
                                    explications.getOrDefault(courante, "?"),
                                    String.valueOf(entrees)));
                        }
                        courante = ligne.substring(3, ligne.indexOf('"', 3));
                        entrees = 0;
                    } else if (!ligne.isBlank()) {
                        entrees++;
                    }
                }
            }
            if (courante != null) {
                couches.add(List.of(courante,
                        explications.getOrDefault(courante, "?"),
                        String.valueOf(entrees)));
            }
        }
        return couches;
    }

    private static String lancerJava(String... arguments) {
        var commande = new ArrayList<String>();
        commande.add(Path.of(System.getProperty("java.home"), "bin", "java")
                .toString());
        commande.addAll(List.of(arguments));
        try {
            var processus = new ProcessBuilder(commande)
                    .redirectErrorStream(true).start();
            String sortie = new String(processus.getInputStream().readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
            processus.waitFor();
            return processus.exitValue() == 0 ? sortie : "ECHEC — " + sortie;
        } catch (Exception erreur) {
            return "ECHEC — " + erreur.getMessage();
        }
    }

    private static String resumer(String sortie) {
        String plat = sortie.replaceAll("\\s+", " ").strip();
        if (plat.startsWith("ECHEC")) {
            int deuxPoints = plat.indexOf("Unsupported");
            return deuxPoints >= 0 ? "REFUSE — " + plat.substring(deuxPoints,
                    Math.min(plat.length(), deuxPoints + 46))
                    : "REFUSE — " + plat.substring(0, Math.min(plat.length(), 52));
        }
        return plat.length() <= 54 ? plat : plat.substring(0, 51) + "...";
    }

    private static long taille(List<Path> chemins) {
        long total = 0;
        for (var chemin : chemins) {
            total += pese(chemin);
        }
        return total;
    }

    private static long pese(Path chemin) {
        try {
            if (Files.isRegularFile(chemin)) {
                return Files.size(chemin);
            }
            try (var contenu = Files.walk(chemin)) {
                return contenu.filter(Files::isRegularFile).mapToLong(p -> {
                    try {
                        return Files.size(p);
                    } catch (java.io.IOException ignore) {
                        return 0L;
                    }
                }).sum();
            }
        } catch (java.io.IOException ignore) {
            return 0L;
        }
    }

    private static String enKio(long octets) {
        return octets < 1024 * 1024
                ? "%d Kio".formatted(octets / 1024)
                : "%.1f Mio".formatted(octets / (1024.0 * 1024.0));
    }
}
