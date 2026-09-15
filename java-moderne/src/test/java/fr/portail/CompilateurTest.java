package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.mesure.Compilateur;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * L'outil de mesure avant les mesures.
 *
 * <p>Tout ce projet affirme « le compilateur refuse ceci ». Si le harnais qui
 * pose la question se trompait — en rendant « refusé » pour du code correct,
 * ou « accepté » pour du code fautif — chaque chapitre mentirait poliment.
 * Ces tests vérifient d'abord l'instrument.
 */
class CompilateurTest {

    @Test
    @DisplayName("le compilateur du JDK est accessible : ce projet a besoin d'un JDK")
    void leCompilateurEstLa() {
        assertTrue(Compilateur.disponible(),
                "ce projet demande un JDK, pas un JRE : "
                + "ToolProvider.getSystemJavaCompiler() rend null sur un JRE");
    }

    @Test
    @DisplayName("une classe correcte compile, et sans erreur")
    void uneClasseCorrecteCompile() {
        var verdict = Compilateur.compiler("Bon",
                "public class Bon { static int deux() { return 2; } }");
        assertTrue(verdict.compile());
        assertTrue(verdict.erreurs().isEmpty());
        assertFalse(verdict.refuse());
    }

    @Test
    @DisplayName("une classe fautive est refusee, avec le message de javac")
    void uneClasseFautiveEstRefusee() {
        var verdict = Compilateur.compiler("Mauvais",
                "public class Mauvais { static int deux() { return \"2\"; } }");
        assertTrue(verdict.refuse());
        assertFalse(verdict.erreurs().isEmpty());
        assertTrue(verdict.mentionne("incompatible types"),
                "le message attendu vient de javac : " + verdict.erreurs());
    }

    @Test
    @DisplayName("le verdict rend la premiere erreur, pas une reformulation")
    void laPremiereErreurEstCelleDeJavac() {
        var verdict = Compilateur.compiler("Trois", """
                public class Trois {
                  static int a() { return "x"; }
                  static int b() { return "y"; }
                }
                """);
        assertTrue(verdict.refuse());
        assertEquals(2, verdict.erreurs().size(),
                "deux erreurs distinctes attendues : " + verdict.erreurs());
        assertTrue(verdict.premiereErreur().contains("incompatible types"));
    }

    @Test
    @DisplayName("une classe sans erreur mais introuvable n'est pas confondue avec un succes")
    void uneReferenceInconnueEstUneErreur() {
        var verdict = Compilateur.compiler("Inconnu",
                "public class Inconnu { static Object m() { return new Fantome(); } }");
        assertTrue(verdict.refuse());
        assertTrue(verdict.mentionne("cannot find symbol"));
    }

    @ParameterizedTest(name = "{0} compile")
    @ValueSource(strings = {
        "public class Extrait { record R(int a) {} }",
        "public class Extrait { sealed interface I permits A {} record A() implements I {} }",
        "public class Extrait { static String m() { return \"\"\"\n  bloc\n  \"\"\"; } }",
        "public class Extrait { static void m() { var x = new java.util.ArrayList<String>(); } }",
        "public class Extrait { enum E { UN, DEUX } }",
    })
    @DisplayName("les constructions modernes du cours compilent toutes")
    void lesConstructionsModernesCompilent(String source) {
        assertTrue(Compilateur.compiler("Extrait", source).compile());
    }

    @ParameterizedTest(name = "refuse : {0}")
    @CsvSource(delimiter = '|', textBlock = """
        public class Extrait { static void m() { var x = 1; x = "deux"; } }      | incompatible types
        public class Extrait { var champ = 1; }                                  | 'var' is not allowed here
        public class Extrait { static void m() { final int a = 1; a = 2; } }     | cannot assign a value to final variable
        public class Extrait { static int m() { } }                              | missing return statement
        """)
    @DisplayName("les fautes du cours sont refusees, avec le bon message")
    void lesFautesSontRefusees(String source, String fragment) {
        var verdict = Compilateur.compiler("Extrait", source);
        assertTrue(verdict.refuse(), source);
        assertTrue(verdict.mentionne(fragment.strip()),
                "attendu « " + fragment.strip() + " », obtenu " + verdict.erreurs());
    }

    @Test
    @DisplayName("compiler n'ecrit aucun fichier : les .class restent en memoire")
    void rienNEstEcritSurLeDisque() throws Exception {
        var avant = fichiersClassDuDossier();
        Compilateur.compiler("Ephemere", "public class Ephemere { }");
        assertEquals(avant, fichiersClassDuDossier(),
                "la compilation ne doit rien laisser dans le dossier de travail");
    }

    @Test
    @DisplayName("compilerEtExecuter fait tourner le code produit")
    void leCodeCompileSExecute() {
        String sortie = Compilateur.compilerEtExecuter("Salut", """
                public class Salut {
                  public static void main(String[] args) {
                    System.out.println("deux offres");
                  }
                }
                """);
        assertEquals("deux offres", sortie);
    }

    @Test
    @DisplayName("compilerEtExecuter trouve aussi un `void main()` d'instance")
    void leMainDInstanceEstTrouve() {
        String sortie = Compilateur.compilerEtExecuter("Compact", """
                void main() {
                  IO.println("fichier compact");
                }
                """);
        assertEquals("fichier compact", sortie,
                "JEP 512 : le lanceur accepte un main() d'instance sans arguments");
    }

    @Test
    @DisplayName("une exception dans le code compile est rapportee, pas propagee")
    void uneExceptionEstRapportee() {
        String sortie = Compilateur.compilerEtExecuter("Casse", """
                public class Casse {
                  public static void main(String[] args) {
                    throw new IllegalStateException("dossier vide");
                  }
                }
                """);
        assertTrue(sortie.contains("IllegalStateException"), sortie);
        assertTrue(sortie.contains("dossier vide"), sortie);
    }

    @Test
    @DisplayName("du code refuse ne s'execute pas, et le dit")
    void duCodeRefuseNeSExecutePas() {
        String sortie = Compilateur.compilerEtExecuter("Refuse", """
                public class Refuse {
                  public static void main(String[] args) { return "x"; }
                }
                """);
        assertTrue(sortie.startsWith("REFUSE"), sortie);
    }

    @Test
    @DisplayName("la sortie du code compile ne fuit pas dans la console du test")
    void laSortieEstCapturee() {
        String sortie = Compilateur.compilerEtExecuter("Bavard", """
                public class Bavard {
                  public static void main(String[] args) {
                    System.out.println("ligne 1");
                    System.out.println("ligne 2");
                  }
                }
                """);
        assertEquals(2, sortie.lines().count(), sortie);
        // System.out doit avoir ete rendu : si la capture fuyait, ce message
        // partirait dans le vide et les tests suivants perdraient leur sortie.
        assertTrue(Compilateur.compiler("Apres", "public class Apres {}").compile());
    }

    private static long fichiersClassDuDossier() throws java.io.IOException {
        var racine = java.nio.file.Path.of(".");
        try (var chemins = java.nio.file.Files.list(racine)) {
            return chemins.filter(p -> p.toString().endsWith(".class")).count();
        }
    }
}
