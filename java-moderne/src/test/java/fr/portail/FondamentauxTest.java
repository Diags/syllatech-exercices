package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.mesure.Compilateur;
import java.util.HashMap;
import java.util.Map;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.junit.jupiter.params.provider.ValueSource;

/** Chapitre 1 — ce que le chapitre affiche doit rester vrai. */
class FondamentauxTest {

    @Nested
    @DisplayName("le cache des enveloppes d'entiers")
    class Cache {

        @ParameterizedTest(name = "valueOf({0}) est mis en cache")
        @ValueSource(ints = {-128, -1, 0, 1, 100, 126, 127})
        void dansLeCache(int valeur) {
            assertSame(Integer.valueOf(valeur), Integer.valueOf(valeur));
        }

        @ParameterizedTest(name = "valueOf({0}) n'est PAS mis en cache")
        @ValueSource(ints = {-129, -1000, 128, 1000, 100_000})
        void horsDuCache(int valeur) {
            assertNotSame(Integer.valueOf(valeur), Integer.valueOf(valeur));
        }

        @Test
        @DisplayName("les bornes mesurees sont bien -128 et 127")
        void lesBornes() {
            int premierHaut = -1;
            for (int i = 0; i < 100_000; i++) {
                if (Integer.valueOf(i) != Integer.valueOf(i)) {
                    premierHaut = i;
                    break;
                }
            }
            int premierBas = 1;
            for (int i = 0; i > -100_000; i--) {
                if (Integer.valueOf(i) != Integer.valueOf(i)) {
                    premierBas = i;
                    break;
                }
            }
            assertEquals(128, premierHaut);
            assertEquals(-129, premierBas);
        }

        @Test
        @DisplayName("Long a le meme cache, Double n'en a aucun")
        void lesAutresEnveloppes() {
            assertSame(Long.valueOf(127), Long.valueOf(127));
            assertNotSame(Long.valueOf(128), Long.valueOf(128));
            assertSame(Character.valueOf('a'), Character.valueOf('a'));
            assertNotSame(Double.valueOf(1.0), Double.valueOf(1.0));
        }

        @Test
        @DisplayName("equals, lui, ne depend pas de la valeur")
        void equalsNeMentJamais() {
            assertEquals(Integer.valueOf(127), Integer.valueOf(127));
            assertEquals(Integer.valueOf(128), Integer.valueOf(128));
            assertEquals(Integer.valueOf(100_000), Integer.valueOf(100_000));
        }
    }

    @Nested
    @DisplayName("le deballage d'un null")
    class Deballage {

        @Test
        @DisplayName("un `int` qui recoit un Integer nul leve une NPE")
        void deballerUnNull() {
            Map<String, Integer> notes = new HashMap<>(Map.of("awa", 17));
            var erreur = assertThrows(NullPointerException.class, () -> {
                int note = notes.get("karim");
                assertEquals(0, note);
            });
            assertTrue(erreur.getMessage().contains("Integer.intValue()"),
                    "le message utile de Java >= 14 : " + erreur.getMessage());
        }

        @Test
        @DisplayName("le ternaire deballe des qu'une branche est primitive")
        void leTernaireDeballe() {
            Integer nul = null;
            assertThrows(NullPointerException.class, () -> {
                int x = false ? 1 : nul;
                assertEquals(0, x);
            });
        }

        @Test
        @DisplayName("mais `true ? null : 0` rend null, sans exception")
        void leTernaireQuiNeDeballePas() {
            Object resultat = true ? null : 0;
            org.junit.jupiter.api.Assertions.assertNull(resultat);
        }

        @Test
        @DisplayName("une garde `containsKey` evite le deballage")
        void laGardeFonctionne() {
            Map<String, Boolean> drapeaux = new HashMap<>(Map.of("a", true));
            boolean valeur = drapeaux.containsKey("z") ? drapeaux.get("z") : false;
            assertFalse(valeur);
        }
    }

    @Nested
    @DisplayName("les chaines")
    class Chaines {

        @Test
        @DisplayName("deux litteraux identiques sont le meme objet")
        void lesLitterauxSontPartages() {
            String a = "portail";
            String b = "portail";
            assertSame(a, b);
        }

        @Test
        @DisplayName("new String fabrique un objet distinct, mais egal")
        void newStringEstDistinct() {
            String a = "portail";
            String b = new String("portail");
            assertNotSame(a, b);
            assertEquals(a, b);
        }

        @Test
        @DisplayName("`final` change le resultat de `==` sur une concatenation")
        void finalChangeLIdentite() {
            String cible = "portail";
            String morceau = "por";
            final String constante = "por";
            assertNotSame(cible, morceau + "tail");
            assertSame(cible, constante + "tail",
                    "une expression constante est calculee a la compilation");
        }

        @Test
        @DisplayName("intern() ramene la chaine au reservoir commun")
        void internRamene() {
            String morceau = "por";
            assertSame("portail", (morceau + "tail").intern());
        }

        @Test
        @DisplayName("StringBuilder et += donnent le meme resultat")
        void memeResultat() {
            int tours = 2_000;
            String parConcat = "";
            for (int i = 0; i < tours; i++) {
                parConcat += "x";
            }
            var builder = new StringBuilder();
            for (int i = 0; i < tours; i++) {
                builder.append('x');
            }
            assertEquals(parConcat, builder.toString());
            assertEquals(tours, parConcat.length());
        }

        @Test
        @DisplayName("une String ne change jamais : toUpperCase rend une autre")
        void immuable() {
            String origine = "offre";
            String majuscules = origine.toUpperCase(java.util.Locale.ROOT);
            assertEquals("offre", origine);
            assertEquals("OFFRE", majuscules);
            assertNotSame(origine, majuscules);
        }
    }

    @Nested
    @DisplayName("les debordements d'entiers")
    class Debordements {

        @Test
        @DisplayName("MAX_VALUE + 1 vaut MIN_VALUE, en silence")
        void leDebordementEstSilencieux() {
            assertEquals(Integer.MIN_VALUE, Integer.MAX_VALUE + 1);
        }

        @Test
        @DisplayName("addExact transforme le silence en exception")
        void addExactProteste() {
            var erreur = assertThrows(ArithmeticException.class,
                    () -> Math.addExact(Integer.MAX_VALUE, 1));
            assertEquals("integer overflow", erreur.getMessage());
        }

        @Test
        @DisplayName("Math.abs(MIN_VALUE) est negatif")
        void laValeurAbsolueNegative() {
            assertEquals(Integer.MIN_VALUE, Math.abs(Integer.MIN_VALUE));
            assertTrue(Math.abs(Integer.MIN_VALUE) < 0);
        }

        @Test
        @DisplayName("la division entiere tronque vers zero")
        void laDivisionTronque() {
            assertEquals(-2, -5 / 2);
            assertEquals(2, 5 / 2);
            assertEquals(-1, -5 % 2);
        }
    }

    @Nested
    @DisplayName("`var` sous l'arbitrage du compilateur")
    class Var {

        @ParameterizedTest(name = "{1}")
        @CsvSource(delimiter = '|', textBlock = """
            public class Extrait { static void m() { var x = 1; x = 2; } }                              | une reaffectation du meme type compile
            public class Extrait { static void m() { var l = new java.util.ArrayList<String>(); } }     | var sur un generique compile
            public class Extrait { static void m() { for (var i = 0; i < 3; i++) {} } }                 | var dans un for compile
            """)
        void cequiCompile(String source, String quoi) {
            assertTrue(Compilateur.compiler("Extrait", source).compile(), quoi);
        }

        @ParameterizedTest(name = "{2}")
        @CsvSource(delimiter = '|', textBlock = """
            public class Extrait { static void m() { var x = 1; x = "deux"; } } | incompatible types            | var garde le type infere
            public class Extrait { var champ = 1; }                             | 'var' is not allowed here     | var n'est pas permis sur un champ
            public class Extrait { static void m() { var x; x = 1; } }          | cannot infer type             | var exige une valeur initiale
            public class Extrait { static void m() { var x = null; } }          | variable initializer is 'null'| var ne peut pas inferer depuis null
            """)
        void ceQuiEstRefuse(String source, String fragment, String quoi) {
            var verdict = Compilateur.compiler("Extrait", source);
            assertTrue(verdict.refuse(), quoi);
            assertTrue(verdict.mentionne(fragment.strip()),
                    quoi + " — obtenu " + verdict.erreurs());
        }
    }
}
