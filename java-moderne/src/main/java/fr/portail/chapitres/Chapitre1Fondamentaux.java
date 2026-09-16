package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.mesure.Chrono;
import fr.portail.mesure.Compilateur;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Chapitre 1 — Fondamentaux et syntaxe.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Fondamentaux
 * </pre>
 *
 * <p>Le cours dit : « primitif par valeur, objet par référence », « un
 * Integer peut valoir null », « String est immuable », « var ne perd rien du
 * typage statique ». Ce chapitre ne les répète pas : il les <strong>mesure</strong>,
 * et pour les deux dernières il fait <em>compiler</em> le contre-exemple par
 * le compilateur du JDK, en cours d'exécution.
 */
public final class Chapitre1Fondamentaux {

    private Chapitre1Fondamentaux() {
    }

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "LE CACHE DES ENTIERS : OU `==` MENT");
        int premierHorsCache = -1;
        for (int i = 0; i < 100_000; i++) {
            if (Integer.valueOf(i) != Integer.valueOf(i)) {
                premierHorsCache = i;
                break;
            }
        }
        int premierNegatifHorsCache = 1;
        for (int i = 0; i > -100_000; i--) {
            if (Integer.valueOf(i) != Integer.valueOf(i)) {
                premierNegatifHorsCache = i;
                break;
            }
        }
        Console.ligne("Integer.valueOf(127) == valueOf(127)",
                String.valueOf(Integer.valueOf(127) == Integer.valueOf(127)), 38);
        Console.ligne("Integer.valueOf(128) == valueOf(128)",
                String.valueOf(Integer.valueOf(128) == Integer.valueOf(128)), 38);
        Console.ligne("bornes mesurees du cache",
                "de " + (premierNegatifHorsCache + 1) + " a "
                        + (premierHorsCache - 1), 38);
        System.out.println();
        Console.texte("Le meme code rend `true` ou `false` selon la VALEUR "
                + "comparee. Personne n'ecrit ce bug volontairement : on ecrit "
                + "`==` sur deux Integer parce qu'on croit comparer des "
                + "nombres, et le code marche — jusqu'au jour ou une valeur "
                + "depasse 127. Le correctif tient en un mot : `equals`.");
        Console.sousTitre("Et les autres enveloppes ?");
        Console.ligne("    Long 127 / 128",
                Long.valueOf(127) == Long.valueOf(127) ? "true / "
                        + (Long.valueOf(128) == Long.valueOf(128)) : "?", 38);
        Console.ligne("    Character 'a'",
                String.valueOf(Character.valueOf('a') == Character.valueOf('a')), 38);
        Console.ligne("    Double 1.0",
                String.valueOf(Double.valueOf(1.0) == Double.valueOf(1.0)), 38);
        System.out.println();
        Console.texte("`Double` n'a aucun cache : la comparaison y est "
                + "toujours fausse, ce qui rend le bug plus visible. C'est le "
                + "cache d'`Integer` qui est piegeux, parce qu'il fait marcher "
                + "le mauvais code la plupart du temps.");

        Console.titre(2, "DEBALLER UN `null`");
        Map<String, Integer> notes = new HashMap<>(Map.of("awa", 17));
        try {
            int note = notes.get("karim");
            Console.ligne("note de karim", String.valueOf(note));
        } catch (NullPointerException erreur) {
            Console.ligne("`int note = notes.get(\"karim\")`", "NullPointerException");
            System.out.println();
            Console.texte("Le message que Java 25 donne :", 3);
            Console.texte(erreur.getMessage(), 6);
        }
        System.out.println();
        Integer nul = null;
        try {
            @SuppressWarnings("unused")
            int x = false ? 1 : nul;
        } catch (NullPointerException erreur) {
            Console.ligne("`false ? 1 : nul`", "NullPointerException");
        }
        Object alternative = true ? null : 0;
        Console.ligne("`true ? null : 0`", String.valueOf(alternative));
        System.out.println();
        Console.texte("Les deux lignes se ressemblent, une seule explose. Dans "
                + "la premiere, le type de l'expression est `int` — parce "
                + "qu'une branche est un `int` — donc `nul` est deballe. Dans "
                + "la seconde, le type est `Integer`, et `null` passe. Le "
                + "ternaire deballe des qu'une branche est primitive : c'est la "
                + "regle a retenir, et elle ne se lit pas dans le code.");

        Console.titre(3, "UNE `String` IMMUABLE, ET CE QUE CELA COUTE");
        int tours = 40_000;
        var parConcatenation = Chrono.une(() -> {
            String texte = "";
            for (int i = 0; i < tours; i++) {
                texte += "x";
            }
            return texte;
        });
        var parBuilder = Chrono.une(() -> {
            var b = new StringBuilder();
            for (int i = 0; i < tours; i++) {
                b.append('x');
            }
            return b.toString();
        });
        Console.ligne(tours + " fois `texte += \"x\"`", parConcatenation.lisible());
        Console.ligne(tours + " fois `builder.append`", parBuilder.lisible());
        Console.ligne("rapport", Chrono.rapport(parConcatenation, parBuilder));
        Console.ligne("meme resultat ?",
                String.valueOf(parConcatenation.resultat()
                        .equals(parBuilder.resultat())));
        System.out.println();
        Console.texte("Chaque `+=` fabrique une chaine neuve et recopie toute "
                + "la precedente : le cout total est quadratique. Le "
                + "compilateur sait optimiser `a + b + c` sur UNE ligne — il "
                + "le traduit en un appel unique — mais il ne peut rien pour "
                + "une boucle, ou chaque tour est une instruction separee.");

        Console.titre(4, "DEUX CHAINES EGALES, ET PARFOIS LE MEME OBJET");
        String litteral = "portail";
        String autreLitteral = "portail";
        String construite = new String("portail");
        String morceau = "por";
        String concatVariable = morceau + "tail";
        final String constante = "por";
        String concatConstante = constante + "tail";
        Console.tableau(List.of("expression", "== litteral", "equals"), List.of(
                List.of("\"portail\"", String.valueOf(litteral == autreLitteral), "true"),
                List.of("new String(...)", String.valueOf(litteral == construite),
                        String.valueOf(litteral.equals(construite))),
                List.of("variable + \"tail\"", String.valueOf(litteral == concatVariable),
                        String.valueOf(litteral.equals(concatVariable))),
                List.of("CONSTANTE + \"tail\"", String.valueOf(litteral == concatConstante),
                        String.valueOf(litteral.equals(concatConstante))),
                List.of(".intern()", String.valueOf(litteral == concatVariable.intern()),
                        "true")),
                List.of(24, 14, 10));
        System.out.println();
        Console.texte("La quatrieme ligne est celle qui surprend : ajouter "
                + "`final` devant `constante` change le resultat de `==`. Le "
                + "compilateur reconnait alors une expression constante et la "
                + "calcule lui-meme, a la compilation ; le resultat rejoint le "
                + "reservoir de chaines. Retirez `final`, et le calcul se fait "
                + "a l'execution, dans un objet neuf.");

        Console.titre(5, "LES ENTIERS DEBORDENT EN SILENCE");
        Console.ligne("Integer.MAX_VALUE", String.valueOf(Integer.MAX_VALUE));
        Console.ligne("Integer.MAX_VALUE + 1", String.valueOf(Integer.MAX_VALUE + 1));
        try {
            Math.addExact(Integer.MAX_VALUE, 1);
        } catch (ArithmeticException erreur) {
            Console.ligne("Math.addExact(MAX_VALUE, 1)",
                    "ArithmeticException : " + erreur.getMessage());
        }
        Console.ligne("Math.abs(Integer.MIN_VALUE)",
                String.valueOf(Math.abs(Integer.MIN_VALUE)));
        System.out.println();
        Console.texte("Une valeur absolue negative. Ce n'est pas un bug de la "
                + "bibliotheque : `MIN_VALUE` n'a pas d'oppose representable en "
                + "`int`, et la documentation le dit. Des qu'un calcul peut "
                + "sortir des bornes — un montant, un identifiant, une somme "
                + "de durees — `Math.addExact` transforme un resultat faux en "
                + "une exception.");

        Console.titre(6, "`var` : LE COMPILATEUR ARBITRE");
        if (!Compilateur.disponible()) {
            Console.texte("Pas de compilateur ici : ce programme tourne sur un "
                    + "JRE. Les trois mesures suivantes demandent un JDK.");
            return;
        }
        var essais = List.of(
                new Essai("var infere le type et le GARDE",
                        "public class Extrait { static void m() { var x = 1; x = 2; } }"),
                new Essai("var reaffecte avec un autre type",
                        "public class Extrait { static void m() { var x = 1; x = \"deux\"; } }"),
                new Essai("var comme champ d'une classe",
                        "public class Extrait { var x = 1; }"),
                new Essai("var sans valeur initiale",
                        "public class Extrait { static void m() { var x; x = 1; } }"),
                new Essai("var sur le parametre d'une lambda",
                        "public class Extrait { static Runnable m() { return () -> {}; } "
                        + "static java.util.function.Function<String,Integer> f() "
                        + "{ return (var s) -> s.length(); } }"));
        for (var essai : essais) {
            var verdict = Compilateur.compiler("Extrait", essai.source());
            Console.ligne("  " + essai.titre(),
                    verdict.compile() ? "compile" : "REFUSE", 40);
            if (verdict.refuse()) {
                Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
            }
        }
        System.out.println();
        Console.texte("Ce n'est pas ce projet qui refuse : c'est `javac`, "
                + "appele pendant l'execution par "
                + "`ToolProvider.getSystemJavaCompiler()`. `var` est une "
                + "abreviation d'ecriture, pas un type dynamique — la preuve "
                + "est le message du compilateur, pas une affirmation du "
                + "support de cours.");

        Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Un `record` qui ecrit `equals`, `hashCode` et "
                + "`toString` pour vous ; une classe ecrite a la main qui en "
                + "oublie un ; et un `switch` a qui il manque un cas, refuse "
                + "par le compilateur — mot pour mot.");
        System.out.println();
    }

    private record Essai(String titre, String source) {
    }
}
