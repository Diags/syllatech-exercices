package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.mesure.Compilateur;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.TreeMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.stream.Collectors;
import java.util.stream.IntStream;
import java.util.stream.Stream;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.RepeatedTest;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Chapitre 4 — la paresse, le parallèle, et ce que `peek` ne voit pas. */
class StreamsTest {

    private static final List<Candidat> VIVIER = List.of(
            Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING),
            Candidat.de("Karim Bensaid", 3, Competence.PYTHON),
            Candidat.de("Lea Marchand", 9, Competence.JAVA, Competence.SQL),
            Candidat.de("Tom Nkosi", 1, Competence.REACT));

    @Nested
    @DisplayName("la paresse, mesuree")
    class Paresse {

        @Test
        @DisplayName("sans terminale, rien ne s'execute")
        void rienSansTerminale() {
            var vus = new AtomicInteger();
            VIVIER.stream().peek(c -> vus.incrementAndGet()).filter(c -> true);
            assertEquals(0, vus.get());
        }

        @Test
        @DisplayName("findFirst s'arrete au premier trouve")
        void findFirstCourtCircuite() {
            var vus = new AtomicInteger();
            var premier = VIVIER.stream()
                    .peek(c -> vus.incrementAndGet())
                    .filter(c -> c.anneesExperience() >= 5)
                    .findFirst();
            assertEquals(1, vus.get());
            assertEquals("Awa Diallo", premier.orElseThrow().nom());
        }

        @Test
        @DisplayName("un flux infini se termine si la terminale court-circuite")
        void leFluxInfiniSeTermine() {
            var vus = new AtomicInteger();
            var premier = Stream.iterate(1, n -> n + 1)
                    .peek(n -> vus.incrementAndGet())
                    .filter(n -> n % 7 == 0)
                    .findFirst();
            assertEquals(7, premier.orElseThrow());
            assertEquals(7, vus.get());
        }

        @Test
        @DisplayName("anyMatch court-circuite aussi")
        void anyMatchCourtCircuite() {
            var vus = new AtomicInteger();
            assertTrue(VIVIER.stream().peek(c -> vus.incrementAndGet())
                    .anyMatch(c -> c.anneesExperience() >= 5));
            assertEquals(1, vus.get());
        }

        @Test
        @DisplayName("allMatch s'arrete au premier contre-exemple")
        void allMatchCourtCircuite() {
            var vus = new AtomicInteger();
            org.junit.jupiter.api.Assertions.assertFalse(
                    VIVIER.stream().peek(c -> vus.incrementAndGet())
                            .allMatch(c -> c.anneesExperience() >= 5));
            assertEquals(2, vus.get(), "le deuxieme candidat a 3 ans");
        }
    }

    @Nested
    @DisplayName("le pipeline que count() saute")
    class CountSauteLePipeline {

        @Test
        @DisplayName("stream().peek(...).count() ne voit aucun element")
        void zeroElement() {
            var vus = new AtomicInteger();
            long taille = VIVIER.stream().peek(c -> vus.incrementAndGet()).count();
            assertEquals(VIVIER.size(), taille);
            assertEquals(0, vus.get(),
                    "la taille est connue : le pipeline n'est pas execute");
        }

        @Test
        @DisplayName("un filter rend la taille inconnue, et le pipeline tourne")
        void avecUnFiltre() {
            var vus = new AtomicInteger();
            long taille = VIVIER.stream().filter(c -> true)
                    .peek(c -> vus.incrementAndGet()).count();
            assertEquals(VIVIER.size(), taille);
            assertEquals(VIVIER.size(), vus.get());
        }

        @Test
        @DisplayName("map ne change pas la taille : le pipeline est saute aussi")
        void avecUnMap() {
            var vus = new AtomicInteger();
            long taille = VIVIER.stream().map(Candidat::nom)
                    .peek(n -> vus.incrementAndGet()).count();
            assertEquals(VIVIER.size(), taille);
            assertEquals(0, vus.get());
        }
    }

    @Nested
    @DisplayName("sorted, limit, et l'ordre des operations")
    class SortedEtLimit {

        @Test
        @DisplayName("sorted avant limit consomme toute la source")
        void sortedConsommeTout() {
            var vus = new AtomicInteger();
            var trois = IntStream.rangeClosed(1, 100).boxed()
                    .peek(n -> vus.incrementAndGet())
                    .sorted(Comparator.reverseOrder())
                    .limit(3)
                    .toList();
            assertEquals(List.of(100, 99, 98), trois);
            assertEquals(100, vus.get());
        }

        @Test
        @DisplayName("limit seul s'arrete a trois")
        void limitSeulCourtCircuite() {
            var vus = new AtomicInteger();
            var trois = IntStream.rangeClosed(1, 100).boxed()
                    .peek(n -> vus.incrementAndGet())
                    .limit(3)
                    .toList();
            assertEquals(List.of(1, 2, 3), trois);
            assertEquals(3, vus.get());
        }
    }

    @Nested
    @DisplayName("un flux est a usage unique")
    class UsageUnique {

        @Test
        @DisplayName("le second appel leve IllegalStateException")
        void deuxiemeAppel() {
            var flux = VIVIER.stream();
            flux.count();
            var erreur = assertThrows(IllegalStateException.class, flux::count);
            assertTrue(erreur.getMessage().contains("already been operated upon"),
                    erreur.getMessage());
        }

        @Test
        @DisplayName("un Supplier permet de le rejouer")
        void leSupplierRejoue() {
            java.util.function.Supplier<Stream<Candidat>> source = VIVIER::stream;
            assertEquals(VIVIER.size(), source.get().count());
            assertEquals(VIVIER.size(), source.get().count());
        }
    }

    @Nested
    @DisplayName("les Collectors")
    class Collecteurs {

        @Test
        @DisplayName("groupingBy accepte les cles en double")
        void groupingByAccepte() {
            var parNiveau = VIVIER.stream().collect(Collectors.groupingBy(
                    c -> c.anneesExperience() >= 5, Collectors.counting()));
            assertEquals(2L, parNiveau.get(true));
            assertEquals(2L, parNiveau.get(false));
        }

        @Test
        @DisplayName("toMap les refuse")
        void toMapRefuse() {
            var erreur = assertThrows(IllegalStateException.class,
                    () -> VIVIER.stream().collect(Collectors.toMap(
                            c -> c.anneesExperience() >= 5, Candidat::nom)));
            assertTrue(erreur.getMessage().contains("Duplicate key"), erreur.getMessage());
        }

        @Test
        @DisplayName("toMap a trois arguments prend une regle de fusion")
        void toMapAvecFusion() {
            var fusionne = VIVIER.stream().collect(Collectors.toMap(
                    c -> c.anneesExperience() >= 5, Candidat::nom,
                    (premier, second) -> premier + " / " + second));
            assertEquals("Awa Diallo / Lea Marchand", fusionne.get(true));
        }

        @Test
        @DisplayName("groupingBy peut choisir sa Map")
        void groupingByAvecTreeMap() {
            var parCompetence = VIVIER.stream()
                    .flatMap(c -> c.competences().stream())
                    .collect(Collectors.groupingBy(Competence::libelle,
                            TreeMap::new, Collectors.counting()));
            assertEquals(TreeMap.class, parCompetence.getClass());
            assertEquals("Java", parCompetence.firstKey());
        }

        @Test
        @DisplayName("partitioningBy remplit toujours ses deux cases")
        void partitioningByEstComplet() {
            var partage = VIVIER.stream().collect(
                    Collectors.partitioningBy(c -> c.anneesExperience() > 100));
            assertEquals(2, partage.size());
            assertTrue(partage.get(true).isEmpty());
            assertEquals(VIVIER.size(), partage.get(false).size());
        }

        @Test
        @DisplayName("teeing combine deux collecteurs en une passe")
        void teeing() {
            var extremes = VIVIER.stream().collect(Collectors.teeing(
                    Collectors.minBy(Comparator.comparingInt(Candidat::anneesExperience)),
                    Collectors.maxBy(Comparator.comparingInt(Candidat::anneesExperience)),
                    (min, max) -> min.orElseThrow().prenom() + ".."
                            + max.orElseThrow().prenom()));
            assertEquals("Tom..Lea", extremes);
        }

        @Test
        @DisplayName("joining assemble sans boucle")
        void joining() {
            assertEquals("Awa, Karim, Lea, Tom",
                    VIVIER.stream().map(Candidat::prenom)
                            .collect(Collectors.joining(", ")));
        }
    }

    @Nested
    @DisplayName("Optional : orElse contre orElseGet")
    class Optionnels {

        @Test
        @DisplayName("orElse calcule son defaut meme quand l'Optional est plein")
        void orElseEstAvide() {
            var appels = new AtomicInteger();
            Optional.of("present").orElse(defaut(appels));
            assertEquals(1, appels.get());
        }

        @Test
        @DisplayName("orElseGet ne l'appelle pas")
        void orElseGetEstParesseux() {
            var appels = new AtomicInteger();
            Optional.of("present").orElseGet(() -> defaut(appels));
            assertEquals(0, appels.get());
        }

        @Test
        @DisplayName("sur un Optional vide, les deux calculent")
        void surUnOptionnelVide() {
            var avide = new AtomicInteger();
            var paresseux = new AtomicInteger();
            Optional.<String>empty().orElse(defaut(avide));
            Optional.<String>empty().orElseGet(() -> defaut(paresseux));
            assertEquals(1, avide.get());
            assertEquals(1, paresseux.get());
        }

        @Test
        @DisplayName("orElseThrow sur un Optional vide leve NoSuchElementException")
        void orElseThrow() {
            assertThrows(java.util.NoSuchElementException.class,
                    () -> Optional.empty().orElseThrow());
        }

        private String defaut(AtomicInteger compteur) {
            compteur.incrementAndGet();
            return "aucun";
        }
    }

    @Nested
    @DisplayName("le parallele et ses conditions")
    class Parallele {

        @RepeatedTest(value = 3, name = "essai {currentRepetition}/{totalRepetitions}")
        @DisplayName("un accumulateur partage perd des elements")
        void lAccumulateurPartageEstFaux() {
            var partagee = new ArrayList<Integer>();
            try {
                IntStream.range(0, 10_000).parallel().boxed().forEach(partagee::add);
            } catch (RuntimeException attendu) {
                // ArrayList peut aussi lever : l'un ou l'autre, jamais un resultat juste
                assertTrue(partagee.size() < 10_000);
                return;
            }
            assertNotEquals(10_000, partagee.size(),
                    "une ArrayList partagee entre threads perd des ecritures");
        }

        @Test
        @DisplayName("toList, lui, est correct en parallele")
        void toListEstCorrect() {
            assertEquals(10_000,
                    IntStream.range(0, 10_000).parallel().boxed().toList().size());
        }

        @Test
        @DisplayName("un reduce non associatif donne un autre resultat en parallele")
        void leReduceNonAssociatif() {
            var sequentiel = IntStream.rangeClosed(1, 20).boxed()
                    .reduce(0, (a, b) -> a - b);
            var parallele = IntStream.rangeClosed(1, 20).boxed().parallel()
                    .reduce(0, (a, b) -> a - b);
            assertEquals(-210, sequentiel);
            assertNotEquals(sequentiel, parallele);
        }

        @ParameterizedTest(name = "somme de 1 a {0}, en parallele")
        @ValueSource(ints = {10, 100, 1000})
        @DisplayName("un reduce associatif donne le meme resultat")
        void leReduceAssociatif(int jusqua) {
            int attendu = jusqua * (jusqua + 1) / 2;
            assertEquals(attendu, IntStream.rangeClosed(1, jusqua).sum());
            assertEquals(attendu, IntStream.rangeClosed(1, jusqua).parallel().sum());
        }
    }

    @Nested
    @DisplayName("ce qu'une lambda peut capturer")
    class Capture {

        @Test
        @DisplayName("une variable qui ne change plus se capture")
        void effectivementFinale() {
            assertTrue(Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static Runnable m() {
                        int seuil = 5;
                        return () -> System.out.println(seuil);
                      }
                    }
                    """).compile());
        }

        @Test
        @DisplayName("une variable modifiee ensuite est refusee")
        void modifieeEnsuite() {
            var verdict = Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static Runnable m() {
                        int seuil = 5;
                        Runnable r = () -> System.out.println(seuil);
                        seuil = 6;
                        return r;
                      }
                    }
                    """);
            assertTrue(verdict.refuse());
            assertTrue(verdict.mentionne("must be final or effectively final"));
        }

        @Test
        @DisplayName("un tableau d'un element contourne la regle — et compile")
        void leContournementCompile() {
            assertTrue(Compilateur.compiler("Extrait", """
                    public class Extrait {
                      static Runnable m() {
                        int[] seuil = {5};
                        Runnable r = () -> System.out.println(seuil[0]);
                        seuil[0] = 6;
                        return r;
                      }
                    }
                    """).compile(),
                    "la regle porte sur la variable, pas sur ce qu'elle designe");
        }
    }
}
