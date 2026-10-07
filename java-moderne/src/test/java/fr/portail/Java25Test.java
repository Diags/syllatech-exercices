package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.domaine.Dossier;
import fr.portail.domaine.Evenement;
import fr.portail.mesure.Compilateur;
import java.time.LocalDate;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Chapitre 6 — ce que Java 21 à 25 apportent.
 *
 * <p>Ces tests sont datés : ils décrivent ce que <em>ce</em> JDK accepte. Si
 * l'un d'eux échoue après une mise à jour, ce n'est pas forcément un bug —
 * c'est peut-être une fonctionnalité devenue définitive. Chaque test le dit
 * dans son message.
 */
class Java25Test {

    @Test
    @DisplayName("ce projet tourne bien sur Java 21 ou plus recent")
    void laVersionMinimale() {
        assertTrue(Runtime.version().feature() >= 21,
                "les motifs de record et les switchs scelles exigent Java 21");
    }

    @Nested
    @DisplayName("pattern matching")
    class Motifs {

        @Test
        @DisplayName("instanceof lie la variable")
        void instanceofLie() {
            Object objet = new Evenement.Entretien(
                    LocalDate.of(2026, 3, 11), "Karim B.", 17);
            assertTrue(objet instanceof Evenement.Entretien entretien
                    && entretien.note() == 17);
        }

        @Test
        @DisplayName("la portee de la liaison suit le flot du programme")
        void laPorteeSuitLeFlot() {
            assertEquals("Karim B.", interlocuteur(new Evenement.Entretien(
                    LocalDate.of(2026, 3, 11), "Karim B.", 17)));
            assertEquals("-", interlocuteur("pas un evenement"));
        }

        private String interlocuteur(Object objet) {
            if (!(objet instanceof Evenement.Entretien entretien)) {
                return "-";
            }
            return entretien.interlocuteur();
        }

        @Test
        @DisplayName("un motif de record deconstruit ses composants")
        void leMotifDeconstruit() {
            Object objet = new Evenement.Entretien(
                    LocalDate.of(2026, 3, 11), "Karim B.", 17);
            String resume = switch (objet) {
                case Evenement.Entretien(LocalDate date, String qui, int note) ->
                        qui + "/" + note + " le " + date;
                default -> "autre";
            };
            assertEquals("Karim B./17 le 2026-03-11", resume);
        }

        @Test
        @DisplayName("les motifs s'imbriquent")
        void lesMotifsSImbriquent() {
            Object objet = Dossier.exemple().evenements().getFirst();
            String qui = switch (objet) {
                case Evenement.Deposee(var date, var candidat, var offre) ->
                        candidat.prenom() + "@" + offre.reference();
                default -> "autre";
            };
            assertEquals("Awa@OFF-2026-014", qui);
        }

        @Test
        @DisplayName("un motif imbrique peut lier un composant d'un composant")
        void deuxNiveaux() {
            record Point(int x, int y) { }
            record Ligne(Point depart, Point arrivee) { }
            Object objet = new Ligne(new Point(1, 2), new Point(3, 4));
            int somme = switch (objet) {
                case Ligne(Point(int x1, int y1), Point(int x2, int y2)) ->
                        x1 + y1 + x2 + y2;
                default -> -1;
            };
            assertEquals(10, somme);
        }
    }

    @Nested
    @DisplayName("les gardes et la domination")
    class Gardes {

        @ParameterizedTest(name = "note {0} -> {1}")
        @CsvSource({"19, a recevoir", "16, a recevoir", "15, a revoir",
                    "10, a revoir", "9, sans suite"})
        void lesGardesFiltrent(int note, String attendu) {
            assertEquals(attendu, apprecier(note));
        }

        private String apprecier(int note) {
            Evenement evenement = new Evenement.Entretien(
                    LocalDate.of(2026, 3, 11), "Karim B.", note);
            return switch (evenement) {
                case Evenement.Entretien e when e.note() >= 16 -> "a recevoir";
                case Evenement.Entretien e when e.note() >= 10 -> "a revoir";
                case Evenement.Entretien e -> "sans suite";
                case Evenement.Deposee d -> "deposee";
                case Evenement.Triee t -> "triee";
                case Evenement.Decision d -> "close";
            };
        }

        @Test
        @DisplayName("un cas garde apres le cas general est refuse")
        void laDomination() {
            var verdict = Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static String m(Object o) {
                        return switch (o) {
                          case Integer i -> "entier";
                          case Integer i when i > 5 -> "grand";
                          default -> "autre";
                        };
                      }
                    }
                    """);
            assertTrue(verdict.refuse());
            assertTrue(verdict.mentionne("dominated by a preceding case label"),
                    verdict.erreurs().toString());
        }
    }

    @Nested
    @DisplayName("`case null`")
    class CasNul {

        @Test
        @DisplayName("un switch sans `case null` leve une NPE sur null")
        void sansCaseNull() {
            assertThrows(NullPointerException.class, () -> sansNull(null));
        }

        @Test
        @DisplayName("avec `case null`, il le traite comme les autres")
        void avecCaseNull() {
            assertEquals("non renseigne", avecNull(null));
            assertEquals("un emploi", avecNull("CDI"));
            assertEquals("autre", avecNull("freelance"));
        }

        @Test
        @DisplayName("`case null, default` regroupe les deux")
        void nullEtDefautEnsemble() {
            assertEquals("inconnu", groupe(null));
            assertEquals("inconnu", groupe("freelance"));
            assertEquals("un emploi", groupe("CDI"));
        }

        private String sansNull(String contrat) {
            return switch (contrat) {
                case "CDI" -> "un emploi";
                default -> "autre";
            };
        }

        private String avecNull(String contrat) {
            return switch (contrat) {
                case null -> "non renseigne";
                case "CDI" -> "un emploi";
                default -> "autre";
            };
        }

        private String groupe(String contrat) {
            return switch (contrat) {
                case "CDI" -> "un emploi";
                case null, default -> "inconnu";
            };
        }
    }

    @Nested
    @DisplayName("les blocs de texte")
    class BlocsDeTexte {

        @Test
        @DisplayName("l'indentation commune est retiree")
        void lIndentationEstRetiree() {
            String bloc = """
                    SELECT *
                      FROM offre
                    """;
            assertEquals("SELECT *", bloc.lines().findFirst().orElseThrow());
            assertEquals("  FROM offre", bloc.lines().skip(1).findFirst().orElseThrow());
        }

        @Test
        @DisplayName("les espaces de fin de ligne sont supprimes")
        void lesEspacesDeFinDisparaissent() {
            String bloc = """
                    a
                    b""";
            assertEquals("a\nb", bloc);
        }

        @Test
        @DisplayName("`\\s` retient l'espace de fin")
        void lEchappementSRetient() {
            String bloc = """
                    a\s
                    b""";
            assertEquals("a \nb", bloc);
        }

        @Test
        @DisplayName("`\\` joint deux lignes du fichier")
        void laBarreJoint() {
            String bloc = """
                    une phrase \
                    sur deux lignes""";
            assertEquals("une phrase sur deux lignes", bloc);
        }

        @Test
        @DisplayName("le bloc se termine par un saut si le `\"\"\"` est sur sa ligne")
        void leSautFinal() {
            String avec = """
                    a
                    """;
            String sans = """
                    a""";
            assertEquals("a\n", avec);
            assertEquals("a", sans);
        }
    }

    @Nested
    @DisplayName("ce que Java 25 rend definitif")
    class Definitifs {

        @Test
        @DisplayName("un fichier source compact avec `void main()` compile")
        void leFichierCompact() {
            assertTrue(Compilateur.compiler("Accueil",
                    "void main() { IO.println(\"bonjour\"); }\n").compile(),
                    "JEP 512, definitif en Java 25");
        }

        @Test
        @DisplayName("et il s'execute")
        void leFichierCompactSExecute() {
            assertEquals("bonjour", Compilateur.compilerEtExecuter("Accueil",
                    "void main() { IO.println(\"bonjour\"); }\n"));
        }

        @Test
        @DisplayName("un constructeur peut valider avant d'appeler super()")
        void leConstructeurFlexible() {
            assertTrue(Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static class Base { Base(int n) {} }
                      static class Fille extends Base {
                        Fille(int n) {
                          if (n < 0) throw new IllegalArgumentException("negatif");
                          super(n);
                        }
                      }
                    }
                    """).compile(), "JEP 513, definitif en Java 25");
        }

        @Test
        @DisplayName("un module entier peut etre importe d'une ligne")
        void lImportDeModule() {
            assertTrue(Compilateur.compiler("Extrait", """
                    import module java.base;
                    public class Extrait {
                      static List<String> m() { return List.of("a"); }
                    }
                    """).compile(), "JEP 511, definitif en Java 25");
        }
    }

    @Nested
    @DisplayName("ce qui est encore en preview")
    class Previews {

        @Test
        @DisplayName("un motif sur un type primitif est refuse")
        void lesMotifsPrimitifs() {
            var verdict = Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static String m(Object o) {
                        return switch (o) {
                          case int i -> "int " + i;
                          default -> "autre";
                        };
                      }
                    }
                    """);
            assertTrue(verdict.refuse(),
                    "si ce test echoue, JEP 507 est devenu definitif : "
                    + "mettez a jour le chapitre 6");
            assertTrue(verdict.mentionne("preview"), verdict.erreurs().toString());
        }

        @Test
        @DisplayName("`--enable-preview` les accepterait, mais ce projet s'en passe")
        void leProjetNUtilisePasPreview() {
            // Le pom ne pose ni --enable-preview a la compilation, ni a
            // l'execution. Une classe compilee avec preview refuserait de
            // tourner sur une autre JVM du meme numero, ce qui n'est pas un
            // compromis acceptable pour un projet de cours.
            assertEquals(-1, System.getProperty("java.class.path", "")
                    .indexOf("--enable-preview"));
        }
    }
}
