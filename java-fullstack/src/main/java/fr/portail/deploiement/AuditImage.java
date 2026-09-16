package fr.portail.deploiement;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Predicate;

/**
 * L'audit du Dockerfile — le controle de deploiement qui tourne hors ligne.
 *
 * <p>⚠️ CE QU'IL EST, ET N'EST PAS. Il lit un texte : il ne construit rien
 * et ne lance rien. C'est un controle de CONFIGURATION, comme un linter. Il
 * attrape l'oubli, jamais la vulnerabilite — et l'oubli est de tres loin le
 * cas le plus frequent.
 *
 * <p>Ce qui le rend utile : il se met dans une integration continue en dix
 * lignes, et il echoue le jour ou quelqu'un ajoute un secret « juste pour
 * tester ».
 */
public final class AuditImage {

    /** Une regle, ce qu'elle exige, et ce qu'on risque sans elle. */
    public record Regle(String nom, String attendu, String siAbsente,
                        Predicate<List<String>> satisfaite) {
    }

    private AuditImage() {
    }

    private static Predicate<List<String>> uneLigneCommence(String prefixe) {
        return lignes -> lignes.stream().anyMatch(l -> l.startsWith(prefixe));
    }

    /**
     * ⚠️ ENTREE DECLAREE. Six regles, et chacune dit ce qu'elle coute.
     */
    public static final List<Regle> REGLES = List.of(
            new Regle("build multi-stage", "au moins deux FROM … AS …",
                      "l'outillage de compilation part en production : "
                      + "l'image pese dix fois plus, et embarque un "
                      + "compilateur pour qui s'y trouve",
                      lignes -> lignes.stream()
                              .filter(l -> l.startsWith("FROM "))
                              .count() >= 2),
            new Regle("image finale minimale", "FROM …-jre… en derniere etape",
                      "le JDK, Maven ou Node restent dans l'image livree",
                      AuditImage::finaleMinimale),
            new Regle("utilisateur non privilegie", "USER",
                      "l'application tourne en root DANS le conteneur, ce qui "
                      + "est le point de depart de toute evasion",
                      uneLigneCommence("USER ")),
            new Regle("point d'entree en forme exec", "ENTRYPOINT [\"…\"]",
                      "PID 1 devient un shell, qui ne transmet pas les "
                      + "signaux : `docker stop` attend dix secondes avant de "
                      + "tuer, et les connexions en cours sont coupees net",
                      lignes -> lignes.stream().anyMatch(l ->
                              l.startsWith("ENTRYPOINT") && l.contains("["))),
            new Regle("aucun secret dans l'image", "pas d'ENV de secret",
                      "la valeur est visible par `docker history`, et elle "
                      + "part avec l'image dans chaque registre ou elle est "
                      + "poussee",
                      lignes -> lignes.stream().noneMatch(AuditImage::sentLeSecret)),
            new Regle("controle de sante", "HEALTHCHECK",
                      "l'orchestrateur sait que le conteneur TOURNE, jamais "
                      + "s'il REPOND : un processus fige reste en service",
                      uneLigneCommence("HEALTHCHECK")));

    /** Les mots qui trahissent un secret ecrit dans l'image. */
    private static final List<String> MOTS_DE_SECRET =
            List.of("secret", "password", "motdepasse", "token", "apikey",
                    "api_key", "cle", "key");

    /** Cette instruction ecrit-elle un secret dans l'image ? */
    public static boolean sentLeSecret(String instruction) {
        // TODO : detecter un secret ecrit dans l'image — un ENV ou un ARG dont le NOM evoque un secret ET qui porte une valeur. Une variable sans valeur n'ecrit rien
        return false;
    }

    private static boolean finaleMinimale(List<String> instructions) {
        String derniereBase = null;
        for (String instruction : instructions) {
            if (instruction.startsWith("FROM ")) {
                derniereBase = instruction;
            }
        }
        if (derniereBase == null) {
            return false;
        }
        String bas = derniereBase.toLowerCase();
        return bas.contains("-jre") || bas.contains("slim")
               || bas.contains("alpine") || bas.contains("distroless")
               || bas.contains("nginx");
    }

    public record Constat(Regle regle, boolean satisfaite) {
    }

    /**
     * Normalise un Dockerfile : commentaires retires, continuations
     * recollees.
     *
     * <p>⚠️ Sans ce recollage, un {@code ENTRYPOINT} ecrit sur quatre lignes
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
        List<String> instructions = instructions(dockerfile);
        return REGLES.stream()
                .map(regle -> new Constat(regle,
                        regle.satisfaite().test(instructions)))
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

    /** Un fichier du dossier `deploiement/`, lu sur le disque. */
    public static String lire(String nom) {
        for (Path candidat : List.of(Path.of("deploiement", nom),
                                     Path.of("..", "deploiement", nom))) {
            if (Files.isReadable(candidat)) {
                try {
                    return Files.readString(candidat, StandardCharsets.UTF_8);
                } catch (IOException erreur) {
                    throw new IllegalStateException(
                            nom + " illisible : " + erreur.getMessage());
                }
            }
        }
        throw new IllegalStateException("deploiement/" + nom
                + " introuvable depuis " + Path.of("").toAbsolutePath());
    }

    /** Le compte-rendu, tel qu'une CI l'afficherait. */
    public static List<String> rendre(String dockerfile) {
        List<String> lignes = new ArrayList<>();
        lignes.add(String.format("%-28s %-30s %s", "REGLE", "ATTENDU", "ETAT"));
        for (Constat constat : auditer(dockerfile)) {
            lignes.add(String.format("%-28s %-30s %s",
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
