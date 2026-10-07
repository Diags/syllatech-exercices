package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.domaine.Dossier;
import fr.portail.domaine.Evenement;
import fr.portail.mesure.Compilateur;
import java.time.LocalDate;
import java.util.List;

/**
 * Chapitre 6 — Java 21 à 25 : les nouveautés.
 *
 * <p>Un chapitre sur « les nouveautés » vieillit mal : ce qui était en
 * <em>preview</em> devient définitif, et l'inverse n'arrive jamais. Celui-ci
 * ne recopie donc aucune note de version — il <strong>demande au
 * compilateur</strong>, extrait par extrait, ce qu'il accepte sur la JVM qui
 * exécute ce programme. La réponse est datée du jour où vous le lancez.
 */
public final class Chapitre6Java25 {

    private Chapitre6Java25() {
    }

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "TESTER ET EXTRAIRE D'UN SEUL GESTE");
        Object inconnu = new Evenement.Entretien(
                LocalDate.of(2026, 3, 11), "Karim B.", 17);
        Console.ligne("l'ancienne facon", ancienneFacon(inconnu), 22);
        Console.ligne("`instanceof` avec liaison", nouvelleFacon(inconnu), 30);
        Console.ligne("la garde inversee", gardeInversee(inconnu), 30);
        System.out.println();
        Console.texte("La troisieme ligne est celle qu'on remarque le moins "
                + "et qui change le plus de code : `if (!(o instanceof "
                + "Entretien e)) return;` — apres ce `return`, `e` est "
                + "utilisable dans TOUT le reste de la methode. La portee de "
                + "la liaison suit le flot, pas les accolades.");

        Console.titre(2, "DECONSTRUIRE AU LIEU D'ACCEDER");
        var dossier = Dossier.exemple();
        for (var evenement : dossier.evenements()) {
            Console.ligne("   " + evenement.date(), decrire(evenement), 16);
        }
        System.out.println();
        Console.ligne("l'issue, lue par motif imbrique",
                dossier.issue().map(Enum::name).orElse("en cours"), 36);
        System.out.println();
        Console.texte("`case Deposee(var date, var candidat, var offre)` "
                + "remplace un test de type, une conversion et trois appels "
                + "d'accesseurs. Et le motif s'imbrique : `case "
                + "Decision(LocalDate d, Issue issue, String c)` va chercher "
                + "un composant a l'interieur d'un composant, sans variable "
                + "intermediaire.");

        Console.titre(3, "UN `switch` QUI ACCEPTE `null`");
        for (String entree : new String[]{"CDI", "stage", null}) {
            Console.ligne("   contrat = " + (entree == null ? "null" : entree),
                    classer(entree), 26);
        }
        System.out.println();
        String ancien;
        try {
            ancien = ancienSwitch(null);
        } catch (NullPointerException erreur) {
            ancien = "NullPointerException";
        }
        Console.ligne("le meme switch sans `case null`", ancien, 34);
        System.out.println();
        Console.texte("Avant Java 21, un `switch` sur une chaine nulle levait "
                + "une `NullPointerException` — un cas qu'il fallait traiter "
                + "AVANT, dans un `if`. `case null` le ramene dans le "
                + "switch, a cote des autres. Sans lui, le comportement "
                + "historique est conserve : ecrire `case null` est un choix, "
                + "pas un defaut.");

        Console.titre(4, "LES GARDES, ET L'ORDRE QUI COMPTE");
        for (int note : new int[]{19, 14, 8}) {
            Console.ligne("   note " + note + "/20",
                    apprecier(new Evenement.Entretien(
                            LocalDate.of(2026, 3, 11), "Karim B.", note)), 20);
        }
        System.out.println();
        if (Compilateur.disponible()) {
            var verdict = Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static String m(Object o) {
                        return switch (o) {
                          case Integer i          -> "un entier";
                          case Integer i when i > 5 -> "un grand entier";
                          default                 -> "autre chose";
                        };
                      }
                    }
                    """);
            Console.ligne("le cas garde place APRES le cas general",
                    verdict.compile() ? "compile" : "REFUSE", 44);
            if (verdict.refuse()) {
                Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
            }
            System.out.println();
            Console.texte("Le compilateur refuse un cas qui ne pourra jamais "
                    + "etre atteint. C'est le meme raisonnement que "
                    + "l'exhaustivite : il connait la forme des motifs, donc "
                    + "il sait lequel couvre lequel. Dans une cascade de `if`, "
                    + "personne ne vous aurait prevenu.");
        }

        Console.titre(5, "LES BLOCS DE TEXTE, ET LEURS TROIS SIGNES");
        String requete = """
                SELECT reference, intitule
                  FROM offre
                 WHERE ville = ?
                   AND experience_minimale <= ?
                """;
        Console.ligne("lignes", String.valueOf(requete.lines().count()), 26);
        Console.ligne("caracteres", String.valueOf(requete.length()), 26);
        Console.ligne("commence par", "[" + requete.lines().findFirst().orElse("") + "]", 26);
        System.out.println();
        String avecEspaceFinal = """
                colonne\s
                suivante""";
        String surUneLigne = """
                une phrase coupee \
                dans le fichier""";
        Console.ligne("`\\s` garde l'espace de fin",
                "[" + avecEspaceFinal.replace(" ", "·").replace("\n", "|") + "]", 34);
        Console.ligne("`\\` joint les deux lignes",
                "[" + surUneLigne + "]", 34);
        System.out.println();
        Console.texte("L'indentation commune est retiree automatiquement — "
                + "c'est la position du `\"\"\"` de fermeture qui la fixe. Les "
                + "espaces en fin de ligne, eux, sont TOUJOURS supprimes, "
                + "sauf si on ecrit `\\s`. Les blocs de texte sont stables "
                + "depuis Java 15, pas 21 : le cours le precise, et c'est "
                + "utile quand on cible une version plus ancienne.");

        Console.titre(6, "CE QUE JAVA " + Runtime.version().feature()
                + " REND DEFINITIF");
        if (!Compilateur.disponible()) {
            Console.texte("Pas de compilateur ici : ce programme tourne sur "
                    + "un JRE. Les mesures suivantes demandent un JDK.");
            return;
        }
        for (var essai : DEFINITIFS) {
            var verdict = Compilateur.compiler(essai.classe(), essai.source());
            Console.ligne("  " + essai.titre(),
                    verdict.compile() ? "compile sans --enable-preview" : "REFUSE", 40);
            if (verdict.refuse()) {
                Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
            }
        }
        System.out.println();
        Console.texte("Le premier essai merite un mot : un fichier source "
                + "COMPACT n'a ni paquet, ni classe, ni `public static void "
                + "main(String[])`. Ce projet ne peut donc pas en contenir — "
                + "il vit dans des paquets. Il peut en revanche en compiler "
                + "un, et l'executer :");
        System.out.println();
        String sortie = Compilateur.compilerEtExecuter("Accueil", """
                void main() {
                  var offres = java.util.List.of("OFF-014", "OFF-021");
                  IO.println("Le portail publie " + offres.size() + " offres.");
                  for (var reference : offres) {
                    IO.println("  - " + reference);
                  }
                }
                """);
        for (var ligne : sortie.lines().toList()) {
            Console.texte(ligne, 6);
        }
        System.out.println();
        Console.texte("Ce programme a ete ecrit, compile, charge et execute "
                + "pendant que vous lisiez cette page. `IO.println` et le "
                + "`void main()` sans classe sont definitifs depuis Java 25 : "
                + "c'est ce que la sortie ci-dessus demontre, sans avoir a "
                + "vous croire sur parole.");

        Console.titre(7, "CE QUI EST ENCORE EN PREVIEW");
        for (var essai : PREVIEWS) {
            var verdict = Compilateur.compiler(essai.classe(), essai.source());
            Console.ligne("  " + essai.titre(),
                    verdict.compile() ? "compile" : "REFUSE sans --enable-preview", 40);
            if (verdict.refuse()) {
                Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
            }
        }
        System.out.println();
        Console.texte("Java 25 est une LTS et ces deux-la n'y sont pas "
                + "definitifs. Une note de version vous l'aurait dit ; cette "
                + "commande vous le dit pour LA machine qui fera tourner "
                + "votre code, ce qui est une garantie differente.");

        Console.titre(8, "CE QUE CE PROJET A MESURE");
        Console.tableau(List.of("chapitre", "la mesure qui compte"), List.of(
                List.of("1", "le cache d'`Integer` : de -128 a 127, et `==` ment au-dela"),
                List.of("2", "`addAll` de 3 elements, compteur a 6 — la classe de base fragile"),
                List.of("3", "une cle modifiee apres son `put` : introuvable, jamais perdue"),
                List.of("4", "`peek(...).count()` : zero element traverse le pipeline"),
                List.of("5", "5 000 taches bloquantes : pool de 16 contre threads virtuels"),
                List.of("6", "un `switch` incomplet, refuse par `javac` pendant l'execution")),
                List.of(12, 62));
        System.out.println();
        Console.texte("Aucune de ces six lignes n'est une opinion. Relancez "
                + "les chapitres : les chiffres bougeront, les conclusions "
                + "non. C'est la seule facon honnete de dire « le compilateur "
                + "refusera » dans un support de cours — le montrer refuser.");
        System.out.println();
    }

    // ── chapitre 1 : trois facons d'ecrire la meme chose ─────────────────

    private static String ancienneFacon(Object objet) {
        if (objet instanceof Evenement.Entretien) {
            Evenement.Entretien entretien = (Evenement.Entretien) objet;
            return entretien.interlocuteur() + " — " + entretien.note() + "/20";
        }
        return "autre chose";
    }

    private static String nouvelleFacon(Object objet) {
        if (objet instanceof Evenement.Entretien entretien) {
            return entretien.interlocuteur() + " — " + entretien.note() + "/20";
        }
        return "autre chose";
    }

    private static String gardeInversee(Object objet) {
        if (!(objet instanceof Evenement.Entretien entretien)) {
            return "autre chose";
        }
        // `entretien` existe ici : la portee de la liaison suit le flot du
        // programme. C'est ce qui permet d'ecrire les gardes en premier et
        // de garder le corps de la methode a plat.
        return entretien.interlocuteur() + " — " + entretien.note() + "/20";
    }

    // ── chapitre 2 : les motifs de record ────────────────────────────────

    private static String decrire(Evenement evenement) {
        return switch (evenement) {
            case Evenement.Deposee(LocalDate ignore, var candidat, var offre) ->
                    candidat.prenom() + " postule sur " + offre.reference();
            case Evenement.Triee(LocalDate ignore, boolean retenue, String motif) ->
                    (retenue ? "retenue" : "ecartee") + " — " + motif;
            case Evenement.Entretien(LocalDate ignore, String qui, int note) ->
                    "vue par " + qui + ", note " + note + "/20";
            case Evenement.Decision(LocalDate ignore, var issue, String mot) ->
                    issue + " — " + mot;
        };
    }

    // ── chapitre 3 : `case null` ─────────────────────────────────────────

    private static String classer(String contrat) {
        return switch (contrat) {
            case null -> "non renseigne";
            case "CDI", "CDD" -> "un emploi";
            case "stage", "alternance" -> "une formation";
            default -> "a verifier : " + contrat;
        };
    }

    private static String ancienSwitch(String contrat) {
        return switch (contrat) {
            case "CDI", "CDD" -> "un emploi";
            default -> "autre";
        };
    }

    // ── chapitre 4 : les gardes ──────────────────────────────────────────

    private static String apprecier(Evenement evenement) {
        return switch (evenement) {
            case Evenement.Entretien e when e.note() >= 16 -> "a recevoir vite";
            case Evenement.Entretien e when e.note() >= 10 -> "a revoir";
            case Evenement.Entretien e -> "sans suite";
            case Evenement.Deposee d -> "pas encore vue";
            case Evenement.Triee t -> "au tri";
            case Evenement.Decision d -> "close";
        };
    }

    // ── les extraits soumis au compilateur ───────────────────────────────

    private record Essai(String titre, String classe, String source) {
    }

    private static final List<Essai> DEFINITIFS = List.of(
            new Essai("fichier source compact + `void main()` (JEP 512)", "Accueil", """
                    void main() {
                      IO.println("bonjour");
                    }
                    """),
            new Essai("corps de constructeur flexible (JEP 513)", "Extrait", """
                    public class Extrait {
                      static class Offre {
                        Offre(int salaire) {}
                      }
                      static class OffreCadre extends Offre {
                        OffreCadre(int salaire) {
                          if (salaire < 45000) {
                            throw new IllegalArgumentException("pas un poste de cadre");
                          }
                          super(salaire);
                        }
                      }
                    }
                    """),
            new Essai("import de module entier (JEP 511)", "Extrait", """
                    import module java.base;
                    public class Extrait {
                      static List<String> m() { return List.of("OFF-014"); }
                    }
                    """),
            new Essai("`switch` scelle exhaustif, sans `default`", "Extrait", """
                    public class Extrait {
                      sealed interface Etat permits Ouvert, Clos {}
                      record Ouvert(int candidatures) implements Etat {}
                      record Clos(String motif) implements Etat {}
                      static String m(Etat e) {
                        return switch (e) {
                          case Ouvert(int n) -> n + " candidatures";
                          case Clos(String motif) -> "close : " + motif;
                        };
                      }
                    }
                    """));

    private static final List<Essai> PREVIEWS = List.of(
            new Essai("`StructuredTaskScope` (JEP 505)", "Extrait", """
                    import java.util.concurrent.StructuredTaskScope;
                    public class Extrait {
                      static void m() throws Exception {
                        try (var portee = StructuredTaskScope.open()) { portee.join(); }
                      }
                    }
                    """),
            new Essai("motif sur un type PRIMITIF (JEP 507)", "Extrait", """
                    public class Extrait {
                      static String m(Object o) {
                        return switch (o) {
                          case int i -> "un int : " + i;
                          default -> "autre";
                        };
                      }
                    }
                    """));
}
