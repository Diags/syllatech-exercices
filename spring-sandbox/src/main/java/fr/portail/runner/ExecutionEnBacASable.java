package fr.portail.runner;

import fr.portail.bac.Executeur;
import fr.portail.langage.Interprete;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.TimeUnit;

/**
 * L'execution du cours : un PROCESSUS SEPARE, borne, tuable.
 *
 * <p>CE QUE LA FRONTIERE DE PROCESSUS APPORTE, ET QUI EST REEL ICI
 * <ul>
 *   <li>le code ne voit <strong>pas</strong> le tas de l'application : ni ses
 *       beans, ni ses proprietes, ni ses connexions ouvertes. Ce n'est pas
 *       une politique, c'est une propriete du systeme d'exploitation ;</li>
 *   <li>la memoire est bornee par {@code -Xmx} : une allocation sans fin
 *       tue l'enfant, pas l'application ;</li>
 *   <li>le delai est DUR : {@code waitFor(timeout)} puis
 *       {@code destroyForcibly()}. Une boucle sans fin est tuee ;</li>
 *   <li>la sortie est plafonnee avant de traverser HTTP.</li>
 * </ul>
 *
 * <p>⚠️ CE QUE CETTE CLASSE NE PROUVE PAS. Un processus separe partage le
 * NOYAU. Il ne remplace ni un conteneur durci, ni gVisor, ni une microVM :
 * une faille du noyau franchit cette frontiere-la. Ce que le cours demande
 * — {@code docker run --runtime=runsc --network=none --read-only} — est
 * construit et audite par {@link fr.portail.bac.CommandeDocker}, mais n'est
 * pas lance : ce projet doit tourner sans demon Docker.
 *
 * <p>Autrement dit : la classe mesure ce qu'une frontiere de processus
 * apporte, et le README dit ce qu'il manque encore.
 */
public final class ExecutionEnBacASable implements ServiceExecution {

    /** ⚠️ Non negociable. Sans lui, une seule soumission fige le runner. */
    private final long delaiEnSecondes;

    /** La memoire maximale de l'enfant, en mebioctets. */
    private final int memoireMaximale;

    public ExecutionEnBacASable() {
        this(5, 48);
    }

    public ExecutionEnBacASable(long delaiEnSecondes, int memoireMaximale) {
        this.delaiEnSecondes = delaiEnSecondes;
        this.memoireMaximale = memoireMaximale;
    }

    /** Le delai dur, tel qu'il a ete regle. Une entree declaree, pas un secret. */
    public long delaiEnSecondes() {
        return delaiEnSecondes;
    }

    /** La memoire maximale de l'enfant, en mebioctets. */
    public int memoireMaximale() {
        return memoireMaximale;
    }

    @Override
    public Resultat lancer(DemandeExecution demande) {
        long depart = System.nanoTime();
        Process processus = null;
        try {
            processus = demarrer();
            envoyer(processus, demande.code());

            // >>> depart: le delai DUR — attendre au plus `delaiEnSecondes`, puis TUER le processus (pas le lui demander) et rendre un resultat marque « delai depasse »
            //     if (!processus.waitFor(delaiEnSecondes, TimeUnit.SECONDS)) {
            //         return new Resultat("", "delai depasse", -1, true,
            //                             millisecondes(depart));
            //     }
            if (!processus.waitFor(delaiEnSecondes, TimeUnit.SECONDS)) {
                // ⚠️ Le tueur. `destroy()` demande poliment ; un script
                // hostile n'ecoute pas. `destroyForcibly` ne demande pas.
                processus.destroyForcibly();
                processus.waitFor(2, TimeUnit.SECONDS);
                return new Resultat("", "delai depasse (" + delaiEnSecondes
                                        + " s) — processus tue", -1, true,
                                    millisecondes(depart));
            }
            // <<<

            String sortie = lire(processus.getInputStream());
            String erreurs = lire(processus.getErrorStream());
            return new Resultat(Interprete.tronquer(sortie),
                                Interprete.tronquer(erreurs),
                                processus.exitValue(), false,
                                millisecondes(depart));
        } catch (IOException erreur) {
            return new Resultat("", "le bac a sable n'a pas demarre : "
                                    + erreur.getMessage(), -2, false,
                                millisecondes(depart));
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            if (processus != null) {
                processus.destroyForcibly();
            }
            return new Resultat("", "interrompu", -3, false,
                                millisecondes(depart));
        }
    }

    /** La ligne de commande reelle — celle que les chapitres impriment. */
    public List<String> commande() {
        String java = ProcessHandle.current().info().command()
                .orElse(System.getProperty("java.home") + "/bin/java");
        List<String> commande = new ArrayList<>();
        commande.add(java);
        // >>> depart: borner l'enfant par des drapeaux de JVM — memoire maximale, mort nette sur manque de memoire, un seul cœur
        //     commande.add("-Dfile.encoding=UTF-8");
        // ⚠️ Chaque drapeau ferme une porte, exactement comme ceux de
        // `docker run` au chapitre 4.
        commande.add("-Xmx" + memoireMaximale + "m");      // saturation
        commande.add("-XX:+ExitOnOutOfMemoryError");       // mort nette
        commande.add("-XX:ActiveProcessorCount=1");        // pas tout le CPU
        commande.add("-Djava.awt.headless=true");
        commande.add("-Dfile.encoding=UTF-8");
        // <<<
        commande.add("-cp");
        commande.add(cheminDeClassesMinimal());
        commande.add(Executeur.class.getName());
        return commande;
    }

    /**
     * ⚠️ L'enfant ne recoit PAS le chemin de classes de l'application.
     *
     * <p>On lui donne le seul repertoire qui contient {@code Executeur} et
     * le langage — ni Spring, ni les pilotes de base de donnees, ni les
     * bibliotheques metier. Moins il y a de classes dans un bac a sable,
     * moins il y a de gadgets a enchainer.
     *
     * <p>C'est aussi ce qui rend ce lancement fiable sous Maven : le
     * {@code java.class.path} d'un fil de test surefire pointe sur un jar
     * d'amorcage, pas sur les classes du projet.
     */
    static String cheminDeClassesMinimal() {
        try {
            var source = Executeur.class.getProtectionDomain().getCodeSource();
            if (source != null) {
                return java.nio.file.Path.of(source.getLocation().toURI())
                        .toString();
            }
        } catch (java.net.URISyntaxException ignore) {
            // on retombe sur le chemin complet ci-dessous
        }
        return System.getProperty("java.class.path");
    }

    private Process demarrer() throws IOException {
        ProcessBuilder constructeur = new ProcessBuilder(commande());
        // >>> depart: ne laisser passer AUCUNE variable d'environnement de l'application vers l'enfant — une ligne, et un jeton d'API cesse de traverser sans qu'on y pense
        // ⚠️ L'environnement est VIDE : aucune variable de l'application ne
        // passe. C'est le pendant de `--env-file /dev/null` — et c'est ce
        // qui empeche un jeton d'API de traverser sans qu'on y pense.
        constructeur.environment().clear();
        // <<<
        return constructeur.start();
    }

    private static void envoyer(Process processus, String code)
            throws IOException {
        try (OutputStream entree = processus.getOutputStream()) {
            entree.write(code.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static String lire(java.io.InputStream flux) throws IOException {
        return new String(flux.readAllBytes(), StandardCharsets.UTF_8);
    }

    private static long millisecondes(long depart) {
        return (System.nanoTime() - depart) / 1_000_000;
    }

    @Override
    public String nom() {
        return "dans un processus separe";
    }
}
