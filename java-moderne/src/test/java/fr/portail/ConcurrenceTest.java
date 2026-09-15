package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.mesure.Compilateur;
import fr.portail.pieges.Guichet;
import java.nio.file.Files;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutionException;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Chapitre 5 — threads virtuels, courses, et ce que `close()` avale. */
class ConcurrenceTest {

    @Nested
    @DisplayName("les threads virtuels")
    class Virtuels {

        @Test
        @DisplayName("un thread virtuel se declare comme tel")
        void ilSeDeclare() {
            var thread = Thread.ofVirtual().unstarted(() -> { });
            assertTrue(thread.isVirtual());
            assertTrue(thread.isDaemon(), "un thread virtuel est toujours daemon");
        }

        @Test
        @DisplayName("on ne peut pas rendre un thread virtuel non-daemon")
        void onNePeutPasLeRendreNonDaemon() {
            var thread = Thread.ofVirtual().unstarted(() -> { });
            assertThrows(IllegalArgumentException.class, () -> thread.setDaemon(false));
        }

        @ParameterizedTest(name = "{0} taches bloquantes tiennent sur une poignee de porteurs")
        @ValueSource(ints = {200, 1_000})
        @Timeout(30)
        @DisplayName("beaucoup de threads virtuels, peu de porteurs")
        void peuDePorteurs(int combien) throws Exception {
            var porteurs = ConcurrentHashMap.<String>newKeySet();
            var lances = new AtomicInteger();
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < combien; i++) {
                    executeur.submit(() -> {
                        lances.incrementAndGet();
                        String nom = Thread.currentThread().toString();
                        int arobase = nom.lastIndexOf('@');
                        porteurs.add(arobase < 0 ? nom : nom.substring(arobase + 1));
                        Thread.sleep(1);
                        return null;
                    });
                }
            }
            assertEquals(combien, lances.get());
            assertTrue(porteurs.size() <= Runtime.getRuntime().availableProcessors() + 2,
                    combien + " taches portees par " + porteurs.size() + " porteurs");
        }

        @Test
        @Timeout(60)
        @DisplayName("des taches bloquantes vont plus vite sur des threads virtuels")
        void plusRapideQueLePool() {
            int taches = 2_000;
            long surPool = chronometre(() -> lancer(taches, true));
            long surVirtuels = chronometre(() -> lancer(taches, false));
            assertTrue(surVirtuels * 4 < surPool,
                    "pool=" + surPool + " ms, virtuels=" + surVirtuels + " ms");
        }

        private long chronometre(Runnable geste) {
            long debut = System.nanoTime();
            geste.run();
            return (System.nanoTime() - debut) / 1_000_000;
        }

        private void lancer(int taches, boolean poolFixe) {
            try (var executeur = poolFixe
                    ? Executors.newFixedThreadPool(8)
                    : Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < taches; i++) {
                    executeur.submit(() -> {
                        Thread.sleep(5);
                        return null;
                    });
                }
            }
        }
    }

    @Nested
    @DisplayName("le compteur partage")
    class Compteur {

        @Test
        @Timeout(60)
        @DisplayName("`recues++` perd des incrementations")
        void leCompteurNuPerd() {
            var guichet = new Guichet();
            enParallele(8, 100_000, guichet::recevoirSansProtection);
            assertTrue(guichet.sansProtection() < 800_000,
                    "PIECE A CONVICTION : " + guichet.sansProtection()
                    + " sur 800000 — si ce test echoue un jour, relancez-le, "
                    + "la course n'est pas garantie de se produire");
            assertTrue(guichet.sansProtection() > 0);
        }

        @Test
        @Timeout(60)
        @DisplayName("AtomicInteger ne perd rien")
        void lAtomiqueEstJuste() {
            var guichet = new Guichet();
            enParallele(8, 100_000, guichet::recevoirAtomique);
            assertEquals(800_000, guichet.atomiques());
        }

        @Test
        @Timeout(60)
        @DisplayName("synchronized non plus")
        void leVerrouEstJuste() {
            var guichet = new Guichet();
            enParallele(8, 100_000, guichet::recevoirSousVerrou);
            assertEquals(800_000, guichet.sousVerrou());
        }

        @Test
        @DisplayName("sur un seul thread, les trois comptent pareil")
        void surUnSeulThread() {
            var guichet = new Guichet();
            for (int i = 0; i < 1_000; i++) {
                guichet.recevoirSansProtection();
                guichet.recevoirAtomique();
                guichet.recevoirSousVerrou();
            }
            assertEquals(1_000, guichet.sansProtection());
            assertEquals(1_000, guichet.atomiques());
            assertEquals(1_000, guichet.sousVerrou());
        }

        private void enParallele(int threads, int tours, Runnable geste) {
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < threads; i++) {
                    executeur.submit(() -> {
                        for (int j = 0; j < tours; j++) {
                            geste.run();
                        }
                        return null;
                    });
                }
            }
        }
    }

    @Nested
    @DisplayName("ce que close() attend, et ce qu'il avale")
    class Fermeture {

        @Test
        @Timeout(30)
        @DisplayName("le try-with-resources attend la fin des taches")
        void closeAttend() {
            var terminee = new AtomicBoolean(false);
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                executeur.submit(() -> {
                    Thread.sleep(200);
                    terminee.set(true);
                    return null;
                });
            }
            assertTrue(terminee.get(), "close() n'a pas attendu la tache");
        }

        @Test
        @Timeout(30)
        @DisplayName("une exception sans get() ne remonte nulle part")
        void lExceptionEstAvalee() {
            var passeParLa = new AtomicBoolean(false);
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                executeur.submit(() -> {
                    passeParLa.set(true);
                    throw new IllegalStateException("le dossier est vide");
                });
            }
            assertTrue(passeParLa.get(), "la tache a bien tourne");
            // et pourtant aucune exception n'est sortie de ce bloc.
        }

        @Test
        @Timeout(30)
        @DisplayName("get() la rend, enveloppee dans une ExecutionException")
        void getLaRend() throws Exception {
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                var promesse = executeur.submit(() -> {
                    throw new IllegalStateException("le dossier est vide");
                });
                var erreur = assertThrows(ExecutionException.class, promesse::get);
                assertEquals(IllegalStateException.class, erreur.getCause().getClass());
                assertEquals("le dossier est vide", erreur.getCause().getMessage());
            }
        }

        @Test
        @Timeout(30)
        @DisplayName("un executeur ferme refuse les nouvelles taches")
        void unExecuteurFermeRefuse() {
            var executeur = Executors.newVirtualThreadPerTaskExecutor();
            executeur.close();
            assertThrows(java.util.concurrent.RejectedExecutionException.class,
                    () -> executeur.submit(() -> null));
        }
    }

    @Nested
    @DisplayName("la concurrence structuree, toujours en preview")
    class Structuree {

        @Test
        @DisplayName("StructuredTaskScope ne compile pas sans --enable-preview")
        void encoreEnPreview() {
            var verdict = Compilateur.compiler("Extrait", """
                    import java.util.concurrent.StructuredTaskScope;
                    public class Extrait {
                      static void m() throws Exception {
                        try (var portee = StructuredTaskScope.open()) { portee.join(); }
                      }
                    }
                    """);
            assertTrue(verdict.refuse(),
                    "si ce test echoue, c'est que StructuredTaskScope est devenu "
                    + "definitif : mettez a jour le chapitre 5");
            assertTrue(verdict.mentionne("preview API"), verdict.erreurs().toString());
        }

        @Test
        @DisplayName("mais la classe existe bel et bien dans le JDK")
        void elleExistePourtant() throws Exception {
            assertEquals("java.util.concurrent.StructuredTaskScope",
                    Class.forName("java.util.concurrent.StructuredTaskScope").getName(),
                    "elle est la : c'est le compilateur qui la verrouille, pas son absence");
        }
    }

    @Nested
    @DisplayName("lire un fichier")
    class Fichiers {

        @Test
        @DisplayName("Files.lines rend le meme contenu que readAllLines")
        void memeContenu() throws Exception {
            var fichier = Files.createTempFile("portail-test-", ".txt");
            try {
                Files.writeString(fichier, "a\nb\nc\n");
                var tout = Files.readAllLines(fichier);
                try (var flux = Files.lines(fichier)) {
                    assertEquals(tout, flux.toList());
                }
            } finally {
                Files.deleteIfExists(fichier);
            }
        }

        @Test
        @DisplayName("un flux de fichier ferme ne se relit pas")
        void leFluxFermeEstFini() throws Exception {
            var fichier = Files.createTempFile("portail-test-", ".txt");
            try {
                Files.writeString(fichier, "a\nb\n");
                java.util.stream.Stream<String> garde;
                try (var flux = Files.lines(fichier)) {
                    garde = flux;
                    assertEquals(2, flux.count());
                }
                assertThrows(IllegalStateException.class, garde::count);
            } finally {
                Files.deleteIfExists(fichier);
            }
        }

        @Test
        @DisplayName("le fichier temporaire est bien supprime apres usage")
        void leMenageEstFait() throws Exception {
            var fichier = Files.createTempFile("portail-test-", ".txt");
            Files.writeString(fichier, "x");
            Files.delete(fichier);
            assertFalse(Files.exists(fichier));
        }
    }
}
