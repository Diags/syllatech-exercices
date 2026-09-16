package fr.portail.plateforme;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

/**
 * Ce qu'un Dockerfile dit, lu par une machine.
 *
 * <p>⚠️ <strong>Pourquoi un lecteur écrit à la main plutôt que
 * {@code docker build}.</strong> Ce projet doit tourner après un clone, sans
 * démon Docker — et surtout, ce que le chapitre 4 veut montrer n'est pas
 * qu'une image se construit, mais <em>ce qu'un Dockerfile décide</em> : le
 * nombre d'étages, ce qui franchit la frontière entre eux, l'utilisateur
 * final, l'ordre des couches. Tout cela se lit dans le fichier.
 *
 * <p>Le lecteur est volontairement simple : il ne remplace pas Docker, il
 * répond à quelques questions précises. C'est exactement ce qu'un vérificateur
 * de CI fait — et c'est beaucoup plus utile qu'une revue humaine qui oublie
 * toujours la même chose.
 */
public final class LectureDockerfile {

    /** Un étage du Dockerfile : son image de base, son nom, ses instructions. */
    public record Etage(String base, String nom, List<String> instructions) {

        /** Les instructions d'un type donné, dans l'ordre. */
        public List<String> instructions(String mot) {
            return instructions.stream()
                    .filter(ligne -> ligne.startsWith(mot + " "))
                    .toList();
        }
    }

    private final List<Etage> etages = new ArrayList<>();

    public LectureDockerfile(Path fichier) throws IOException {
        String base = null;
        String nom = null;
        var courant = new ArrayList<String>();
        for (var brute : Files.readAllLines(fichier)) {
            String ligne = brute.strip();
            if (ligne.isEmpty() || ligne.startsWith("#")) {
                continue;
            }
            if (ligne.startsWith("FROM ")) {
                if (base != null) {
                    etages.add(new Etage(base, nom, List.copyOf(courant)));
                    courant.clear();
                }
                var morceaux = ligne.substring(5).split("\\s+");
                base = morceaux[0];
                nom = morceaux.length >= 3 && morceaux[1].equalsIgnoreCase("AS")
                        ? morceaux[2] : null;
                continue;
            }
            if (base != null) {
                courant.add(ligne);
            }
        }
        if (base != null) {
            etages.add(new Etage(base, nom, List.copyOf(courant)));
        }
    }

    public List<Etage> etages() {
        return List.copyOf(etages);
    }

    public Etage etageFinal() {
        return etages.getLast();
    }

    /** L'image tourne-t-elle sous un utilisateur non privilégié ? */
    public boolean nonRoot() {
        // TODO : repondre en lisant la DERNIERE instruction USER de l'etage final — absente ou « root » valent root
        return true;
    }

    /** L'entrée est-elle en forme exec (un tableau JSON) ? */
    public boolean entreeEnFormeExec() {
        var entrees = etageFinal().instructions("ENTRYPOINT");
        return !entrees.isEmpty() && entrees.getLast().contains("[");
    }

    /** Ce que l'étage final récupère des étages précédents. */
    public List<String> copiesDepuisUnAutreEtage() {
        return etageFinal().instructions("COPY").stream()
                .filter(ligne -> ligne.contains("--from="))
                .toList();
    }

    /**
     * Le pom (ou un fichier de dépendances) est-il copié AVANT le code ?
     *
     * <p>C'est la question qui décide du temps de construction. Copier tout
     * le projet d'un coup invalide le cache des dépendances à chaque ligne de
     * code modifiée.
     */
    public boolean cacheDesDependancesOptimise() {
        for (var etage : etages) {
            var copies = etage.instructions("COPY");
            int rangDuPom = -1;
            int rangDuCode = -1;
            for (int rang = 0; rang < copies.size(); rang++) {
                String copie = copies.get(rang);
                if (copie.contains("pom.xml") || copie.contains("build.gradle")
                        || copie.contains("package.json")) {
                    rangDuPom = rang;
                } else if (copie.contains("src") || copie.contains("COPY . ")) {
                    if (rangDuCode < 0) {
                        rangDuCode = rang;
                    }
                }
            }
            if (rangDuPom >= 0 && rangDuCode > rangDuPom) {
                return true;
            }
        }
        return false;
    }

    /** L'image est-elle taguée avec une version précise, et non `latest` ? */
    public static boolean versionPrecise(String image) {
        int deuxPoints = image.lastIndexOf(':');
        if (deuxPoints < 0) {
            return false;
        }
        String tag = image.substring(deuxPoints + 1);
        return !tag.isBlank() && !tag.equals("latest");
    }
}
