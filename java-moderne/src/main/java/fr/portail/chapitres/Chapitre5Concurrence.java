package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.mesure.Chrono;
import fr.portail.mesure.Compilateur;
import fr.portail.pieges.Guichet;
import java.io.IOException;
import java.nio.file.Files;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.atomic.AtomicBoolean;

/**
 * Chapitre 5 — Concurrence et I/O.
 *
 * <p>Le cours annonce « des millions de tâches » et « quelques kilo-octets ».
 * Ce chapitre ne va pas jusqu'au million — il lance cinq mille tâches deux
 * fois, une fois sur un pool de plateforme, une fois sur des threads
 * virtuels, et affiche les deux durées. L'écart parle tout seul.
 *
 * <p>Il mesure aussi ce que le cours ne dit pas : combien de threads porteurs
 * la JVM utilise réellement, ce que devient une exception qu'on ne lit pas,
 * et le fait que {@code StructuredTaskScope} — présenté comme la façon de
 * structurer la concurrence — est encore en <em>preview</em> dans Java 25.
 */
public final class Chapitre5Concurrence {

    private Chapitre5Concurrence() {
    }

    private static final int TACHES = 5_000;
    private static final int ATTENTE_MS = 10;

    public static void main(String[] args) throws Exception {
        Console.utf8();

        Console.titre(1, "CE QUE CETTE MACHINE A SOUS LA MAIN");
        Console.ligne("version de Java", Runtime.version().toString(), 26);
        Console.ligne("processeurs disponibles",
                String.valueOf(Runtime.getRuntime().availableProcessors()), 26);
        Console.ligne("memoire maximale",
                Runtime.getRuntime().maxMemory() / (1024 * 1024) + " Mio", 26);
        System.out.println();
        Console.texte("Les chiffres qui suivent dependent de cette machine. "
                + "Ce n'est pas un defaut de la mesure : c'est ce qui la rend "
                + "utile — relancez-la sur la votre, l'ordre de grandeur sera "
                + "le meme et les valeurs, differentes.");

        Console.titre(2, TACHES + " TACHES, DEUX FACONS");
        Console.texte("Chaque tache dort " + ATTENTE_MS + " ms. C'est le cas "
                + "qui compte : une tache BLOQUEE, comme un appel reseau ou "
                + "une requete SQL. Une tache qui calcule ne gagnerait rien "
                + "aux threads virtuels — le processeur ne se duplique pas.");
        System.out.println();
        var surPool = Chrono.une(() -> lancer(Executors.newFixedThreadPool(16)));
        var surVirtuels = Chrono.une(
                () -> lancer(Executors.newVirtualThreadPerTaskExecutor()));
        Console.ligne("pool fixe de 16 threads", surPool.lisible(), 30);
        Console.ligne("un thread virtuel par tache", surVirtuels.lisible(), 30);
        Console.ligne("rapport", Chrono.rapport(surPool, surVirtuels), 30);
        Console.ligne("minimum theorique",
                "environ " + ATTENTE_MS + " ms (tout en meme temps)", 30);
        System.out.println();
        Console.texte("Le pool de 16 traite " + TACHES + " taches par "
                + "fournees de 16 : " + (TACHES / 16) + " fournees de "
                + ATTENTE_MS + " ms. Les threads virtuels n'ont pas cette "
                + "file — chaque tache a le sien, et pendant qu'elle dort, "
                + "son porteur travaille ailleurs.");

        Console.titre(3, "COMBIEN DE THREADS PORTEURS ?");
        var porteurs = ConcurrentHashMap.<String>newKeySet();
        var virtuels = ConcurrentHashMap.<String>newKeySet();
        try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < 2_000; i++) {
                executeur.submit(() -> {
                    virtuels.add(Thread.currentThread().threadId() + "");
                    porteurs.add(nomDuPorteur());
                    Thread.sleep(1);
                    return null;
                });
            }
        }
        Console.ligne("threads virtuels lances", String.valueOf(virtuels.size()), 30);
        Console.ligne("threads porteurs distincts",
                String.valueOf(porteurs.size()), 30);
        Console.ligne("un thread virtuel est daemon ?",
                String.valueOf(Thread.ofVirtual().unstarted(() -> { }).isDaemon()), 34);
        System.out.println();
        Console.texte("Deux mille threads virtuels, portes par une poignee de "
                + "threads de plateforme — autant que de processeurs. C'est "
                + "la le gain : le thread virtuel n'est pas un thread du "
                + "systeme, c'est un objet que la JVM pose et retire d'un "
                + "porteur au gre des blocages.");
        System.out.println();
        Console.texte("⚠️ Ils sont tous « daemon » : la JVM ne les attend pas "
                + "pour s'arreter. Un thread virtuel lance a la main, sans "
                + "executeur, peut donc etre coupe net a la fin du "
                + "programme.");

        Console.titre(4, "LE COMPTEUR QUI PERD DES INCREMENTATIONS");
        int threads = 8;
        int parThread = 100_000;
        int attendu = threads * parThread;
        // Trois passes separees, et non trois compteurs dans la meme boucle :
        // un `incrementAndGet` voisin pose une barriere memoire qui rend le
        // compteur nu BEAUCOUP moins faux. Mesurer les trois ensemble
        // reviendrait a mesurer un bug attenue par son propre temoin.
        var sansProtection = new Guichet();
        var atomique = new Guichet();
        var sousVerrou = new Guichet();
        var tempsSans = enParallele(threads, parThread, sansProtection::recevoirSansProtection);
        var tempsAtomique = enParallele(threads, parThread, atomique::recevoirAtomique);
        var tempsVerrou = enParallele(threads, parThread, sousVerrou::recevoirSousVerrou);
        Console.tableau(List.of("compteur", "attendu", "obtenu", "perdu", "duree"), List.of(
                List.of("recues++", String.valueOf(attendu),
                        String.valueOf(sansProtection.sansProtection()),
                        pourcentage(attendu - sansProtection.sansProtection(), attendu),
                        tempsSans.lisible()),
                List.of("AtomicInteger", String.valueOf(attendu),
                        String.valueOf(atomique.atomiques()),
                        pourcentage(attendu - atomique.atomiques(), attendu),
                        tempsAtomique.lisible()),
                List.of("synchronized", String.valueOf(attendu),
                        String.valueOf(sousVerrou.sousVerrou()),
                        pourcentage(attendu - sousVerrou.sousVerrou(), attendu),
                        tempsVerrou.lisible())),
                List.of(18, 11, 11, 9, 10));
        System.out.println();
        Console.texte("`recues++` n'est pas une operation : c'est lire, "
                + "ajouter un, ecrire. Deux threads qui lisent la meme valeur "
                + "ecrivent la meme valeur, et une incrementation disparait. "
                + "La proportion perdue n'est pas stable — relancez ce "
                + "chapitre, elle changera. C'est ce qui rend ce bug "
                + "difficile : trop gros pour passer pour un arrondi, trop "
                + "instable pour etre reproduit dans un test.");
        System.out.println();
        Console.texte("Les deux versions justes ne coutent pas la meme chose. "
                + "`AtomicInteger` s'appuie sur une instruction du "
                + "processeur ; `synchronized` prend et rend un verrou, "
                + "ce qui serialise les huit threads. Pour un compteur, "
                + "l'atomique suffit et gagne — le verrou devient utile des "
                + "que PLUSIEURS champs doivent rester coherents entre eux.");

        Console.titre(5, "CE QUE `close()` ATTEND, ET CE QU'IL AVALE");
        var terminee = new AtomicBoolean(false);
        var attenteFermeture = Chrono.une(() -> {
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                executeur.submit(() -> {
                    Thread.sleep(300);
                    terminee.set(true);
                    return null;
                });
            }
            return null;
        });
        Console.ligne("`close()` a rendu la main apres",
                attenteFermeture.lisible(), 34);
        Console.ligne("la tache de 300 ms etait finie ?",
                String.valueOf(terminee.get()), 34);
        System.out.println();
        try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
            executeur.submit(() -> {
                throw new IllegalStateException("le dossier est vide");
            });
        }
        Console.ligne("une exception dans `submit(...)`",
                "rien ne sort — personne n'appelle get()", 34);
        try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
            var promesse = executeur.submit(() -> {
                throw new IllegalStateException("le dossier est vide");
            });
            try {
                promesse.get();
            } catch (java.util.concurrent.ExecutionException erreur) {
                Console.ligne("   la meme, avec `get()`",
                        erreur.getCause().getClass().getSimpleName() + " : "
                                + erreur.getCause().getMessage(), 34);
            }
        }
        System.out.println();
        Console.texte("Le `try-with-resources` est la bonne nouvelle : "
                + "`close()` attend toutes les taches. La mauvaise est "
                + "juste en dessous — une exception levee dans une tache "
                + "soumise par `submit` ne remonte NULLE PART tant que "
                + "personne n'appelle `get()`. Elle est rangee dans le "
                + "`Future`, et si on jette le `Future`, on jette "
                + "l'exception.");
        System.out.println();
        Console.texte("C'est le probleme que la concurrence structuree "
                + "resout : un groupe de taches qui reussissent ou echouent "
                + "ensemble, dans une portee ou l'echec ne peut pas se "
                + "perdre.");

        Console.titre(6, "LA CONCURRENCE STRUCTUREE EST ENCORE EN PREVIEW");
        if (Compilateur.disponible()) {
            var verdict = Compilateur.compiler("Extrait", """
                    import java.util.concurrent.StructuredTaskScope;
                    public class Extrait {
                      static void m() throws Exception {
                        try (var portee = StructuredTaskScope.open()) {
                          portee.fork(() -> "offre");
                          portee.fork(() -> "candidat");
                          portee.join();
                        }
                      }
                    }
                    """);
            Console.ligne("compile sur ce JDK " + Runtime.version().feature() + " ?",
                    verdict.compile() ? "oui" : "NON", 30);
            for (var erreur : verdict.erreurs()) {
                Console.texte(erreur.lines().findFirst().orElse(""), 6);
            }
            System.out.println();
            Console.texte("Java 25 est une LTS, et `StructuredTaskScope` n'y "
                    + "est toujours pas definitif : il faut `--enable-preview` "
                    + "a la compilation ET a l'execution, et le format de "
                    + "classe produit refuse de tourner sur une autre version "
                    + "de la JVM. Ce projet compile sans preview — d'ou "
                    + "l'absence de cette classe dans son code.");
            System.out.println();
            Console.texte("La difference entre « existe dans le JDK » et "
                    + "« utilisable en production » se mesure avec cette "
                    + "commande, pas avec une note de version.");
        }

        Console.titre(7, "`synchronized` N'EPINGLE PLUS LE PORTEUR");
        int taches = Runtime.getRuntime().availableProcessors() * 2;
        var horsVerrou = Chrono.une(() -> dormirEn(taches, false));
        var dansVerrou = Chrono.une(() -> dormirEn(taches, true));
        Console.ligne(taches + " taches, sommeil hors verrou",
                horsVerrou.lisible(), 38);
        Console.ligne(taches + " taches, sommeil DANS synchronized",
                dansVerrou.lisible(), 38);
        System.out.println();
        Console.texte("Les deux durees sont proches. Jusqu'a Java 23, la "
                + "seconde aurait ete environ deux fois plus longue : un "
                + "thread virtuel bloque a l'interieur d'un `synchronized` "
                + "restait EPINGLE a son porteur, qui ne pouvait servir "
                + "personne d'autre. Java 24 a leve cette limite.");
        System.out.println();
        Console.texte("C'est ce que le cours appelle « des virtual threads "
                + "sans leurs dernieres limitations ». La mesure ci-dessus "
                + "est ce que cette phrase veut dire concretement.");

        Console.titre(8, "LIRE UN FICHIER : TOUT, OU AU FIL DE L'EAU");
        var fichier = Files.createTempFile("portail-", ".csv");
        try {
            var lignes = new StringBuilder();
            for (int i = 1; i <= 50_000; i++) {
                lignes.append("OFF-").append(i).append(";Lyon;").append(40_000 + i)
                        .append(System.lineSeparator());
            }
            Files.writeString(fichier, lignes.toString());
            Console.ligne("fichier de travail",
                    Files.size(fichier) / 1024 + " Kio, 50 000 lignes", 30);

            var enMemoire = Chrono.une(() -> {
                try {
                    return Files.readAllLines(fichier).size();
                } catch (IOException erreur) {
                    throw new RuntimeException(erreur);
                }
            });
            var enFlux = Chrono.une(() -> {
                try (var flux = Files.lines(fichier)) {
                    return flux.filter(l -> l.endsWith("50000")).count();
                } catch (IOException erreur) {
                    throw new RuntimeException(erreur);
                }
            });
            Console.ligne("`readAllLines` (tout en memoire)",
                    enMemoire.lisible() + " — " + enMemoire.resultat()
                    + " chaines gardees en meme temps", 34);
            Console.ligne("`lines` + filter (au fil de l'eau)",
                    enFlux.lisible() + " — 1 chaine a la fois, "
                    + enFlux.resultat() + " retenue(s)", 36);
            System.out.println();
            Console.texte("Les deux durees sont du meme ordre, et c'est "
                    + "normal : sur un megaoctet, tout tient en memoire sans "
                    + "peine. La difference n'est pas la vitesse, c'est ce "
                    + "qui reste alloue — 50 000 `String` d'un cote, une de "
                    + "l'autre. Multipliez le fichier par mille et le "
                    + "premier devient un `OutOfMemoryError` quand le second "
                    + "ne bouge pas.");
            System.out.println();
            Console.texte("`Files.lines` rend un flux paresseux, mais il "
                    + "ouvre un fichier — et un flux qui tient une ressource "
                    + "se ferme. D'ou le `try-with-resources` autour : c'est "
                    + "le seul `Stream` de ce projet qui en ait besoin, et "
                    + "c'est justement celui qu'on oublie.");
        } finally {
            Files.deleteIfExists(fichier);
        }

        Console.titre(9, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Les `record patterns` qui deconstruisent au lieu "
                + "d'appeler des accesseurs ; un `switch` qui accepte `null` "
                + "sans exploser ; et ce que Java 25 rend definitif — verifie "
                + "extrait par extrait, par le compilateur.");
        System.out.println();
    }

    /** Fait exécuter {@code tours} fois ce geste par {@code threads} threads. */
    private static Chrono.Mesure enParallele(int threads, int tours, Runnable geste) {
        return Chrono.une(() -> {
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
            return threads * tours;
        });
    }

    /** Lance les tâches sur cet exécuteur et attend qu'il les ait finies. */
    private static Object lancer(ExecutorService executeur) {
        try (executeur) {
            for (int i = 0; i < TACHES; i++) {
                executeur.submit(() -> {
                    Thread.sleep(ATTENTE_MS);
                    return null;
                });
            }
        }
        return TACHES;
    }

    /** Fait dormir {@code combien} tâches, dedans ou dehors d'un verrou. */
    private static Object dormirEn(int combien, boolean sousVerrou) {
        try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
            for (int i = 0; i < combien; i++) {
                executeur.submit(() -> {
                    if (sousVerrou) {
                        // Un verrou par tache : il n'y a AUCUNE contention.
                        // Ce qui est mesure est donc l'epinglage du porteur,
                        // pas l'attente d'un verrou pris par un autre.
                        Object verrou = new Object();
                        synchronized (verrou) {
                            Thread.sleep(50);
                        }
                    } else {
                        Thread.sleep(50);
                    }
                    return null;
                });
            }
        }
        return combien;
    }

    /**
     * Le nom du thread porteur, tel que la JVM l'expose.
     *
     * <p>Il n'y a pas d'API publique pour le demander : le nom du thread
     * virtuel contient celui de son porteur, et c'est ce qu'on lit ici. Cela
     * suffit à les compter, et à rien de plus — ne bâtissez pas de code
     * dessus.
     */
    private static String nomDuPorteur() {
        String description = Thread.currentThread().toString();
        int arobase = description.lastIndexOf('@');
        return arobase < 0 ? description : description.substring(arobase + 1);
    }

    private static String pourcentage(int perdu, int attendu) {
        return perdu == 0 ? "0" : "%.0f %%".formatted(100.0 * perdu / attendu);
    }
}
