package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/**
 * Chapitre 6 — ce que pèse l'application, et comment on l'empaquette.
 *
 * <p>Ces tests ne construisent pas d'image : Docker n'est pas une dépendance
 * de ce projet. Ils pèsent ce qui composerait l'image, et vérifient que le
 * {@code Dockerfile} livré n'utilise pas la commande d'extraction qui a été
 * retirée de Spring Boot 4.
 */
class EmpaquetageTest {

    @Nested
    @DisplayName("ce que pese l'application")
    class Poids {

        @Test
        @DisplayName("notre code pese moins de 2 % du total")
        void laProportion() {
            long notre = taille(false);
            long dependances = taille(true);
            double part = 100.0 * notre / (notre + dependances);
            assertThat(part)
                    .as("c'est tout l'argument du decoupage en couches : "
                        + "notre code = %.2f %% de l'image".formatted(part))
                    .isLessThan(2.0);
        }

        @Test
        @DisplayName("les dependances pesent plusieurs dizaines de mega-octets")
        void lesDependances() {
            assertThat(taille(true)).isGreaterThan(20L * 1024 * 1024);
        }

        private long taille(boolean jars) {
            long total = 0;
            for (var entree : System.getProperty("java.class.path", "")
                    .split(File.pathSeparator)) {
                var chemin = Path.of(entree);
                if (!Files.exists(chemin) || entree.endsWith(".jar") != jars) {
                    continue;
                }
                total += pese(chemin);
            }
            return total;
        }

        private long pese(Path chemin) {
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
    }

    @Nested
    @DisplayName("le Dockerfile livre")
    class Dockerfile {

        @Test
        @DisplayName("il existe a la racine du projet")
        void ilExiste() {
            assertThat(Files.isRegularFile(Path.of("Dockerfile"))).isTrue();
        }

        @Test
        @DisplayName("il n'utilise pas `layertools`, retire de Spring Boot 4")
        void pasDeLayertools() throws Exception {
            // Sur les lignes ACTIVES, pas sur le fichier entier : le
            // Dockerfile explique en commentaire pourquoi `layertools` n'est
            // plus la, et ce commentaire ne doit pas faire echouer le test
            // qui verifie son absence.
            assertThat(String.join(" | ", lignes()))
                    .as("`-Djarmode=layertools` est le mode que citent la "
                        + "plupart des tutoriels ; il a ete remplace par "
                        + "`-Djarmode=tools`")
                    .doesNotContain("layertools")
                    .contains("-Djarmode=tools");
        }

        @Test
        @DisplayName("il construit en deux etapes")
        void deuxEtapes() throws Exception {
            assertThat(lignes().stream()
                    .filter(l -> l.startsWith("FROM ")).toList())
                    .hasSize(2);
            assertThat(contenu()).contains("--from=");
        }

        @Test
        @DisplayName("il copie les couches dans l'ordre du plus stable au plus volatil")
        void lOrdreDesCouches() throws Exception {
            var copies = lignes().stream()
                    .filter(l -> l.startsWith("COPY --from="))
                    .toList();
            int dependances = indexContenant(copies, "dependencies/");
            int application = indexContenant(copies, "application/");
            assertThat(dependances).isNotNegative();
            assertThat(application)
                    .as("la couche qui change a chaque commit vient en dernier")
                    .isGreaterThan(dependances);
        }

        @Test
        @DisplayName("il lance JarLauncher, pas `java -jar`")
        void leLanceur() throws Exception {
            assertThat(contenu())
                    .contains("org.springframework.boot.loader.launch.JarLauncher");
        }

        @Test
        @DisplayName("l'image finale n'embarque ni Maven ni le code source")
        void lImageFinaleEstMince() throws Exception {
            var apresLeSecondFrom = new ArrayList<String>();
            boolean second = false;
            for (var ligne : lignes()) {
                if (ligne.startsWith("FROM ")) {
                    second = !ligne.contains(" AS ");
                    continue;
                }
                if (second) {
                    apresLeSecondFrom.add(ligne);
                }
            }
            assertThat(apresLeSecondFrom).isNotEmpty();
            assertThat(String.join("\n", apresLeSecondFrom))
                    .doesNotContain("maven")
                    .doesNotContain("src/");
        }

        @Test
        @DisplayName("l'image de base est un JRE, pas un JDK")
        void unJre() throws Exception {
            assertThat(lignes().stream().filter(l -> l.startsWith("FROM ")).toList())
                    .allMatch(l -> l.contains("-jre"),
                            "un JDK dans l'image finale ajoute 150 Mio pour rien");
        }

        private String contenu() throws java.io.IOException {
            return Files.readString(Path.of("Dockerfile"));
        }

        private List<String> lignes() throws java.io.IOException {
            return contenu().lines().map(String::strip)
                    .filter(l -> !l.isEmpty() && !l.startsWith("#")).toList();
        }

        private int indexContenant(List<String> lignes, String fragment) {
            for (int i = 0; i < lignes.size(); i++) {
                if (lignes.get(i).contains(fragment)) {
                    return i;
                }
            }
            return -1;
        }
    }
}
