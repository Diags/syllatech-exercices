package fr.portail.bac;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

/**
 * L'audit de l'IMAGE — la derniere ligne de defense, et la plus oubliee.
 *
 * <p>Les drapeaux de {@code docker run} ferment des portes autour du
 * conteneur. L'image, elle, decide de ce qu'il y a DEDANS : qui execute,
 * avec quels outils, et si un shell traine pour enchainer des commandes.
 *
 * <p>⚠️ MEME LIMITE QUE {@link AuditDurcissement} : ceci lit un texte. Rien
 * n'est construit, rien n'est lance. C'est un controle de configuration, et
 * il attrape l'oubli — pas la vulnerabilite. L'oubli reste le cas le plus
 * frequent, et {@code USER} est de tres loin la ligne qui manque.
 */
public final class AuditImage {

    /** Une regle, ce qui la satisfait, et ce qui arrive quand elle manque. */
    public record Regle(String nom, String attendu, String siAbsente,
                        Predicate<List<String>> satisfaite) {
    }

    private AuditImage() {
    }

    private static Predicate<List<String>> uneLigneCommence(String prefixe) {
        return lignes -> lignes.stream().anyMatch(l -> l.startsWith(prefixe));
    }

    /**
     * ⚠️ ENTREE DECLAREE. Cinq regles, et chacune dit ce qu'on risque —
     * ce qu'aucune documentation d'instruction Dockerfile ne fait.
     */
    public static final List<Regle> REGLES = List.of(
            new Regle("base minimale", "FROM …-jre… ou …-slim/alpine",
                      "l'image embarque un compilateur, un gestionnaire de "
                      + "paquets et des outils reseau — autant de marches "
                      + "pour qui s'y trouve",
                      lignes -> lignes.stream().anyMatch(l ->
                              l.startsWith("FROM ")
                              && (l.contains("-jre") || l.contains("slim")
                                  || l.contains("alpine")))),
            new Regle("utilisateur non privilegie", "USER",
                      "le code du candidat tourne en root DANS le conteneur, "
                      + "ce qui est le point de depart de toute evasion",
                      uneLigneCommence("USER ")),
            new Regle("repertoire de travail", "WORKDIR",
                      "le processus demarre a la racine de l'image, et y ecrit "
                      + "si `--read-only` venait a manquer",
                      uneLigneCommence("WORKDIR ")),
            new Regle("point d'entree en forme exec", "ENTRYPOINT [\"…\"]",
                      "PID 1 devient un shell, qui ne transmet pas les "
                      + "signaux : `docker stop` attend dix secondes avant "
                      + "de tuer",
                      lignes -> lignes.stream().anyMatch(l ->
                              l.startsWith("ENTRYPOINT") && l.contains("["))),
            new Regle("script hors de la commande", "pas de CMD de script",
                      "le script du candidat voyagerait dans `argv`, donc dans "
                      + "`ps`, dans `docker inspect` et dans les journaux du "
                      + "demon — c'est-a-dire archive",
                      lignes -> lignes.stream().noneMatch(l ->
                              l.startsWith("CMD "))));

    public record Constat(Regle regle, boolean satisfaite) {
    }

    /**
     * Normalise un Dockerfile : commentaires retires, continuations de ligne
     * recollees, espaces reduits.
     *
     * <p>Sans ce recollage, un {@code ENTRYPOINT} ecrit sur six lignes
     * passerait pour absent — et l'audit dirait le contraire de la verite.
     */
    public static List<String> instructions(String dockerfile) {
        List<String> lignes = new ArrayList<>();
        StringBuilder courante = new StringBuilder();
        for (String brute : dockerfile.split("\\R")) {
            String ligne = brute.strip();
            if (ligne.isEmpty() || ligne.startsWith("#")) {
                continue;
            }
            boolean continuee = ligne.endsWith("\\");
            if (continuee) {
                ligne = ligne.substring(0, ligne.length() - 1).strip();
            }
            courante.append(courante.isEmpty() ? "" : " ").append(ligne);
            if (!continuee) {
                lignes.add(courante.toString().replaceAll("\\s+", " "));
                courante.setLength(0);
            }
        }
        if (!courante.isEmpty()) {
            lignes.add(courante.toString().replaceAll("\\s+", " "));
        }
        return List.copyOf(lignes);
    }

    public static List<Constat> auditer(String dockerfile) {
        List<String> lignes = instructions(dockerfile);
        return REGLES.stream()
                .map(regle -> new Constat(regle, regle.satisfaite().test(lignes)))
                .toList();
    }

    public static List<Regle> manquantes(String dockerfile) {
        return auditer(dockerfile).stream()
                .filter(constat -> !constat.satisfaite())
                .map(Constat::regle)
                .toList();
    }

    public static boolean conforme(String dockerfile) {
        return manquantes(dockerfile).isEmpty();
    }

    /**
     * Le Dockerfile LIVRE dans ce projet, lu sur le disque.
     *
     * <p>Le chapitre 4 l'audite tel quel : retirez-en une ligne, relancez, il
     * le dit. C'est ce qui separe un controle d'une illustration.
     */
    public static String dockerfileDuProjet() {
        for (Path candidat : List.of(Path.of("deploiement", "Dockerfile"),
                                     Path.of("..", "deploiement", "Dockerfile"))) {
            if (Files.isReadable(candidat)) {
                try {
                    return Files.readString(candidat, StandardCharsets.UTF_8);
                } catch (IOException erreur) {
                    throw new IllegalStateException(
                            "Dockerfile illisible : " + erreur.getMessage());
                }
            }
        }
        throw new IllegalStateException(
                "deploiement/Dockerfile introuvable depuis "
                + Path.of("").toAbsolutePath());
    }

    /** Le compte-rendu, tel qu'une CI l'afficherait. */
    public static List<String> rendre(String dockerfile) {
        List<String> lignes = new ArrayList<>();
        lignes.add(String.format("%-32s %-30s %s",
                                 "REGLE", "ATTENDU", "ETAT"));
        for (Constat constat : auditer(dockerfile)) {
            lignes.add(String.format("%-32s %-30s %s",
                    constat.regle().nom(), constat.regle().attendu(),
                    constat.satisfaite() ? "satisfaite" : "⚠️ ABSENTE"));
        }
        List<Regle> manquantes = manquantes(dockerfile);
        lignes.add("");
        lignes.add(manquantes.isEmpty()
                ? "conforme : les " + REGLES.size() + " regles sont satisfaites"
                : "⚠️ " + manquantes.size() + " regle(s) non satisfaite(s) sur "
                  + REGLES.size());
        for (Regle regle : manquantes) {
            lignes.add("   " + regle.nom() + " → " + regle.siAbsente());
        }
        return lignes;
    }
}
