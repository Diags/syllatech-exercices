package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.mesure.Compilateur;
import fr.portail.pieges.CleMuable;
import fr.portail.pieges.PanierSansCopie;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.ConcurrentModificationException;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.TreeMap;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Chapitre 3 — le contrat des clés, l'immuabilité, les génériques. */
class CollectionsTest {

    @Nested
    @DisplayName("une cle qui bouge apres son rangement")
    class CleQuiBouge {

        @Test
        @DisplayName("apres modification, get rend null")
        void introuvable() {
            var cle = new CleMuable("java");
            var map = new HashMap<CleMuable, String>();
            map.put(cle, "OFF-014");
            assertEquals("OFF-014", map.get(cle));
            cle.changer("java17");
            assertNull(map.get(cle), "PIECE A CONVICTION : la cle a change de casier");
        }

        @Test
        @DisplayName("l'entree existe pourtant toujours")
        void jamaisPerdue() {
            var cle = new CleMuable("java");
            var map = new HashMap<CleMuable, String>();
            map.put(cle, "OFF-014");
            cle.changer("java17");
            assertEquals(1, map.size());
            assertTrue(map.containsValue("OFF-014"));
            assertEquals(1, map.entrySet().size());
        }

        @Test
        @DisplayName("remettre l'ancienne valeur la fait reapparaitre")
        void reapparait() {
            var cle = new CleMuable("java");
            var map = new HashMap<CleMuable, String>();
            map.put(cle, "OFF-014");
            cle.changer("java17");
            cle.changer("java");
            assertEquals("OFF-014", map.get(cle),
                    "la preuve que rien n'etait perdu, seulement mal range");
        }

        @Test
        @DisplayName("equals et hashCode restent coherents : le defaut est ailleurs")
        void leContratEstRespecte() {
            var a = new CleMuable("java");
            var b = new CleMuable("java");
            assertEquals(a, b);
            assertEquals(a.hashCode(), b.hashCode());
        }
    }

    @Nested
    @DisplayName("un record sans copie defensive")
    class RecordSansCopie {

        @Test
        @DisplayName("son hashCode change quand la liste d'origine change")
        void leHashCodeBouge() {
            var articles = new ArrayList<>(List.of("cv.pdf"));
            var panier = new PanierSansCopie("Awa", articles);
            int avant = panier.hashCode();
            articles.add("lettre.pdf");
            assertNotEquals(avant, panier.hashCode(),
                    "PIECE A CONVICTION : le record garde la liste telle quelle");
        }

        @Test
        @DisplayName("il se perd dans l'ensemble ou il se trouve")
        void ilSePerd() {
            var articles = new ArrayList<>(List.of("cv.pdf"));
            var panier = new PanierSansCopie("Awa", articles);
            var ensemble = new HashSet<PanierSansCopie>();
            ensemble.add(panier);
            assertTrue(ensemble.contains(panier));
            articles.add("lettre.pdf");
            assertFalse(ensemble.contains(panier));
        }

        @Test
        @DisplayName("son toString reflete la mutation : le record a bien change")
        void leToStringSuit() {
            var articles = new ArrayList<>(List.of("cv.pdf"));
            var panier = new PanierSansCopie("Awa", articles);
            articles.add("lettre.pdf");
            assertTrue(panier.toString().contains("lettre.pdf"), panier.toString());
        }

        @Test
        @DisplayName("la reference, elle, n'a pas change : c'est le sens d'« immuable »")
        void laReferenceNeChangePas() {
            var articles = new ArrayList<>(List.of("cv.pdf"));
            var panier = new PanierSansCopie("Awa", articles);
            articles.add("lettre.pdf");
            assertSame(articles, panier.articles());
        }
    }

    @Nested
    @DisplayName("cinq facons de dire « non modifiable »")
    class NonModifiable {

        @Test
        @DisplayName("List.of refuse add et set")
        void listOf() {
            var liste = List.of("a");
            assertThrows(UnsupportedOperationException.class, () -> liste.add("b"));
            assertThrows(UnsupportedOperationException.class, () -> liste.set(0, "z"));
        }

        @Test
        @DisplayName("Arrays.asList refuse add mais ACCEPTE set")
        void arraysAsList() {
            var liste = Arrays.asList("a", "b");
            assertThrows(UnsupportedOperationException.class, () -> liste.add("c"));
            liste.set(0, "z");
            assertEquals(List.of("z", "b"), liste,
                    "c'est une vue sur un tableau, de taille fixe mais ecrivable");
        }

        @Test
        @DisplayName("List.copyOf est une copie : la source peut changer")
        void copyOfEstUneCopie() {
            var source = new ArrayList<>(List.of("a"));
            var copie = List.copyOf(source);
            source.add("b");
            assertEquals(List.of("a"), copie);
        }

        @Test
        @DisplayName("unmodifiableList est une VUE : la source la change")
        void unmodifiableEstUneVue() {
            var source = new ArrayList<>(List.of("a"));
            var vue = Collections.unmodifiableList(source);
            source.add("b");
            assertEquals(List.of("a", "b"), vue,
                    "une vue non modifiable n'est pas une liste immuable");
        }

        @Test
        @DisplayName("List.of refuse null, Arrays.asList l'accepte")
        void lesNulls() {
            assertThrows(NullPointerException.class, () -> List.of("a", null));
            assertEquals(2, Arrays.asList("a", null).size());
        }

        @Test
        @DisplayName("Map.of refuse deux fois la meme cle")
        void mapOfRefuseLesDoublons() {
            assertThrows(IllegalArgumentException.class,
                    () -> java.util.Map.of("a", 1, "a", 2));
        }
    }

    @Nested
    @DisplayName("les generiques et l'effacement de type")
    class Generiques {

        @Test
        @DisplayName("List<String> et List<Integer> sont la meme classe a l'execution")
        void lEffacement() {
            assertSame(new ArrayList<String>().getClass(),
                    new ArrayList<Integer>().getClass());
        }

        @Test
        @DisplayName("le compilateur refuse un int dans une List<String>")
        void leCompilateurRefuse() {
            var verdict = Compilateur.compiler("Extrait", """
                    import java.util.*;
                    public class Extrait {
                      static void m() { List<String> l = new ArrayList<>(); l.add(42); }
                    }
                    """);
            assertTrue(verdict.refuse());
            assertTrue(verdict.mentionne("incompatible types"));
        }

        @Test
        @DisplayName("un type brut, lui, compile — et explose a la lecture")
        void leTypeBrutCompile() {
            var verdict = Compilateur.compiler("Extrait", """
                    import java.util.*;
                    public class Extrait {
                      static Object m() {
                        List<String> l = new ArrayList<>();
                        List brut = l;
                        brut.add(42);
                        return l.get(0);
                      }
                    }
                    """);
            assertTrue(verdict.compile(),
                    "un type brut desactive la verification : javac avertit, mais accepte");
        }

        @Test
        @DisplayName("et l'exception sort sur un `get` correct")
        @SuppressWarnings({"unchecked", "rawtypes"})
        void laClassCastExceptionSortAilleurs() {
            var liste = new ArrayList<String>();
            List brut = liste;
            brut.add(42);
            var erreur = assertThrows(ClassCastException.class, () -> {
                String premier = liste.get(0);
                assertNotEquals("", premier);
            });
            assertTrue(erreur.getMessage().contains("Integer"), erreur.getMessage());
        }

        @Test
        @DisplayName("instanceof sur un type generique est refuse")
        void instanceofGenerique() {
            var verdict = Compilateur.compiler("Extrait", """
                    import java.util.*;
                    public class Extrait {
                      static boolean m(Object o) { return o instanceof List<String>; }
                    }
                    """);
            assertTrue(verdict.refuse());
        }
    }

    @Nested
    @DisplayName("l'ordre, et l'illusion d'un ordre")
    class Ordre {

        @Test
        @DisplayName("LinkedHashMap garde l'ordre d'insertion")
        void insertion() {
            var map = new LinkedHashMap<String, Integer>();
            map.put("Tom", 1);
            map.put("Awa", 6);
            map.put("Lea", 9);
            assertEquals(List.of("Tom", "Awa", "Lea"), List.copyOf(map.keySet()));
        }

        @Test
        @DisplayName("TreeMap trie les cles")
        void trie() {
            var map = new TreeMap<String, Integer>();
            map.put("Tom", 1);
            map.put("Awa", 6);
            map.put("Lea", 9);
            assertEquals(List.of("Awa", "Lea", "Tom"), List.copyOf(map.keySet()));
        }

        @Test
        @DisplayName("HashMap ne promet rien, mais rend le meme ordre a chaque fois")
        void hashMapEstStableSansEtreTriee() {
            var premier = clesDansUnHashMap();
            var second = clesDansUnHashMap();
            assertEquals(premier, second,
                    "stable pour ces cles — ce qui n'est pas une garantie de l'API");
            assertNotEquals(List.of("Awa", "Lea", "Tom"), premier,
                    "et ce n'est pas l'ordre alphabetique");
        }

        private List<String> clesDansUnHashMap() {
            var map = new HashMap<String, Integer>();
            map.put("Tom", 1);
            map.put("Awa", 6);
            map.put("Lea", 9);
            return List.copyOf(map.keySet());
        }
    }

    @Nested
    @DisplayName("deux signatures trop proches")
    class Signatures {

        @Test
        @DisplayName("remove(int) retire par indice")
        void parIndice() {
            var liste = new ArrayList<>(List.of(3, 2, 1));
            liste.remove(1);
            assertEquals(List.of(3, 1), liste);
        }

        @Test
        @DisplayName("remove(Object) retire par valeur")
        void parValeur() {
            var liste = new ArrayList<>(List.of(3, 2, 1));
            liste.remove(Integer.valueOf(1));
            assertEquals(List.of(3, 2), liste);
        }

        @ParameterizedTest(name = "retirer \"{0}\" pendant un for-each")
        @ValueSource(strings = {"a", "c"})
        @DisplayName("modifier pendant l'iteration leve une exception...")
        void laModificationConcurrente(String cible) {
            var liste = new ArrayList<>(List.of("a", "b", "c"));
            assertThrows(ConcurrentModificationException.class, () -> {
                for (var x : liste) {
                    if (x.equals(cible)) {
                        liste.remove(x);
                    }
                }
            });
        }

        @Test
        @DisplayName("...sauf pour l'avant-dernier element, ou elle se tait")
        void leCasSilencieux() {
            var liste = new ArrayList<>(List.of("a", "b", "c"));
            for (var x : liste) {
                if (x.equals("b")) {
                    liste.remove(x);
                }
            }
            assertEquals(List.of("a", "c"), liste,
                    "aucune exception : la boucle s'est arretee une position trop tot");
        }

        @Test
        @DisplayName("removeIf fait le meme travail, sans piege")
        void removeIf() {
            var liste = new ArrayList<>(List.of("a", "b", "c"));
            liste.removeIf(x -> x.equals("b"));
            assertEquals(List.of("a", "c"), liste);
        }
    }
}
