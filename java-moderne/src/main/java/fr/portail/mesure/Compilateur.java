package fr.portail.mesure;

import java.io.IOException;
import java.net.URI;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaFileObject;
import javax.tools.SimpleJavaFileObject;
import javax.tools.StandardLocation;
import javax.tools.ToolProvider;

/**
 * Compile un bout de Java <em>pendant l'exécution</em>, et rend ce que le
 * compilateur en dit.
 *
 * <p>C'est la pièce centrale de ce projet. Un cours de langage passe son
 * temps à affirmer des choses sur la <strong>compilation</strong> — « le
 * switch ne compilera pas si vous oubliez un cas », « var n'est pas du
 * typage dynamique », « ce code refuse un mauvais type ». Ces affirmations
 * ne se vérifient pas en exécutant un programme : elles se vérifient en
 * essayant de le compiler.
 *
 * <p>Le JDK embarque son propre compilateur, accessible par
 * {@link ToolProvider#getSystemJavaCompiler()}. On lui donne une source en
 * mémoire, on récupère ses diagnostics, et l'affirmation devient une mesure.
 * Aucun fichier n'est écrit : ni source, ni {@code .class}.
 *
 * <p>⚠️ Cela demande un <strong>JDK</strong>, pas un JRE. Sur un JRE,
 * {@code getSystemJavaCompiler()} rend {@code null} — le cas est traité, et
 * les chapitres le disent plutôt que de planter.
 */
public final class Compilateur {

    private Compilateur() {
    }

    /** Le verdict d'une compilation : réussie, ou les erreurs rencontrées. */
    public record Verdict(boolean compile, List<String> erreurs) {

        public boolean refuse() {
            return !compile;
        }

        /** La première erreur, sans son numéro de ligne ni son extrait. */
        public String premiereErreur() {
            return erreurs.isEmpty() ? "" : erreurs.getFirst();
        }

        /** L'erreur contient-elle ce fragment ? Sert aux tests. */
        public boolean mentionne(String fragment) {
            return erreurs.stream().anyMatch(e -> e.contains(fragment));
        }
    }

    /** Le compilateur du JDK est-il accessible ? */
    public static boolean disponible() {
        return ToolProvider.getSystemJavaCompiler() != null;
    }

    /**
     * Compile une unité de compilation complète.
     *
     * @param nomDeClasse la classe publique attendue dans {@code source}
     * @param source      le fichier Java, en entier
     */
    public static Verdict compiler(String nomDeClasse, String source) {
        var compilateur = ToolProvider.getSystemJavaCompiler();
        if (compilateur == null) {
            return new Verdict(false, List.of(
                    "aucun compilateur : ce programme tourne sur un JRE, "
                    + "pas sur un JDK"));
        }
        var diagnostics = new DiagnosticCollector<JavaFileObject>();
        var gestionnaire = new EnMemoire(
                compilateur.getStandardFileManager(diagnostics, null, null));
        var unite = new SourceEnMemoire(nomDeClasse, source);

        // -proc:none : on ne veut pas qu'un processeur d'annotations du
        // classpath se mele de nos extraits. Le resultat doit ne dependre
        // que du langage.
        var tache = compilateur.getTask(null, gestionnaire, diagnostics,
                List.of("-proc:none"), null, List.of(unite));
        boolean succes = Boolean.TRUE.equals(tache.call());

        var erreurs = new ArrayList<String>();
        for (var d : diagnostics.getDiagnostics()) {
            if (d.getKind() == Diagnostic.Kind.ERROR) {
                erreurs.add(d.getMessage(Locale.ENGLISH));
            }
        }
        try {
            gestionnaire.close();
        } catch (IOException ignore) {
            // Rien a fermer : tout est en memoire.
        }
        return new Verdict(succes && erreurs.isEmpty(), List.copyOf(erreurs));
    }

    /**
     * Compile <strong>puis exécute</strong> la méthode {@code main} du code
     * donné, et rend ce qu'elle a écrit sur la sortie standard.
     *
     * <p>C'est le prolongement naturel de {@link #compiler} : une fois qu'on
     * tient les octets du {@code .class}, plus rien n'empêche de les charger.
     * Le chapitre 6 s'en sert pour faire tourner un fichier source
     * <em>compact</em> — une nouveauté de Java 25 qu'on ne peut pas écrire
     * dans ce projet, puisqu'un fichier compact n'a pas de paquet.
     *
     * @param nomDeClasse la classe à charger, et dont {@code main} sera appelé
     * @return ce que le programme a écrit, ou le message de l'échec
     */
    public static String compilerEtExecuter(String nomDeClasse, String source) {
        var compilateur = ToolProvider.getSystemJavaCompiler();
        if (compilateur == null) {
            return "aucun compilateur : ce programme tourne sur un JRE";
        }
        var diagnostics = new DiagnosticCollector<JavaFileObject>();
        var gestionnaire = new EnMemoire(
                compilateur.getStandardFileManager(diagnostics, null, null));
        var tache = compilateur.getTask(null, gestionnaire, diagnostics,
                List.of("-proc:none"), null,
                List.of(new SourceEnMemoire(nomDeClasse, source)));
        if (!Boolean.TRUE.equals(tache.call())) {
            for (var d : diagnostics.getDiagnostics()) {
                if (d.getKind() == Diagnostic.Kind.ERROR) {
                    return "REFUSE — " + d.getMessage(Locale.ENGLISH);
                }
            }
            return "REFUSE, sans diagnostic";
        }
        var sortieOriginale = System.out;
        var capture = new java.io.ByteArrayOutputStream();
        try {
            System.setOut(new java.io.PrintStream(capture, true,
                    java.nio.charset.StandardCharsets.UTF_8));
            var chargeur = gestionnaire.chargeur();
            var classe = Class.forName(nomDeClasse, true, chargeur);
            lancer(classe);
        } catch (ReflectiveOperationException | RuntimeException erreur) {
            var cause = erreur instanceof java.lang.reflect.InvocationTargetException i
                    ? i.getCause() : erreur;
            return "a leve " + cause.getClass().getSimpleName() + " : "
                    + cause.getMessage();
        } finally {
            System.setOut(sortieOriginale);
            try {
                gestionnaire.close();
            } catch (IOException ignore) {
                // Rien a fermer : tout est en memoire.
            }
        }
        return capture.toString(java.nio.charset.StandardCharsets.UTF_8).strip();
    }

    /**
     * Appelle le {@code main} de cette classe, comme le lanceur du JDK.
     *
     * <p>Depuis Java 25 (JEP 512), {@code main} n'est plus forcément
     * {@code public static void main(String[])}. Le lanceur cherche, dans cet
     * ordre : {@code main(String[])} puis {@code main()}, statique d'abord,
     * d'instance ensuite — et dans ce dernier cas il construit un exemplaire
     * de la classe avec son constructeur sans argument.
     *
     * <p>Reproduire cet ordre ici n'est pas un détail : c'est ce qui permet
     * d'exécuter un fichier source compact, qui déclare précisément un
     * {@code void main()} d'instance sans modificateur.
     */
    private static void lancer(Class<?> classe) throws ReflectiveOperationException {
        for (boolean avecArguments : new boolean[]{true, false}) {
            java.lang.reflect.Method principal;
            try {
                principal = avecArguments
                        ? classe.getDeclaredMethod("main", String[].class)
                        : classe.getDeclaredMethod("main");
            } catch (NoSuchMethodException absente) {
                continue;
            }
            principal.setAccessible(true);
            Object cible = null;
            if (!java.lang.reflect.Modifier.isStatic(principal.getModifiers())) {
                var constructeur = classe.getDeclaredConstructor();
                constructeur.setAccessible(true);
                cible = constructeur.newInstance();
            }
            if (avecArguments) {
                principal.invoke(cible, (Object) new String[0]);
            } else {
                principal.invoke(cible);
            }
            return;
        }
        throw new NoSuchMethodException(
                classe.getName() + " n'a ni main(String[]) ni main()");
    }

    // ── la plomberie : sources et classes en memoire ─────────────────────

    private static final class SourceEnMemoire extends SimpleJavaFileObject {
        private final String code;

        SourceEnMemoire(String nom, String code) {
            super(URI.create("string:///" + nom.replace('.', '/')
                    + Kind.SOURCE.extension), Kind.SOURCE);
            this.code = code;
        }

        @Override
        public CharSequence getCharContent(boolean ignoreEncodingErrors) {
            return code;
        }
    }

    private static final class ClasseEnMemoire extends SimpleJavaFileObject {
        private final java.io.ByteArrayOutputStream octets =
                new java.io.ByteArrayOutputStream();

        ClasseEnMemoire(String nom) {
            super(URI.create("mem:///" + nom.replace('.', '/')
                    + Kind.CLASS.extension), Kind.CLASS);
        }

        @Override
        public java.io.OutputStream openOutputStream() {
            return octets;
        }

        byte[] octets() {
            return octets.toByteArray();
        }
    }

    /**
     * Un gestionnaire de fichiers qui écrit les {@code .class} en mémoire.
     *
     * <p>Sans lui, chaque mesure laisserait des fichiers derrière elle — et
     * un chapitre qui salit le dossier de travail n'est pas un chapitre.
     */
    private static final class EnMemoire
            extends javax.tools.ForwardingJavaFileManager<javax.tools.JavaFileManager> {

        private final java.util.Map<String, ClasseEnMemoire> produites =
                new java.util.LinkedHashMap<>();

        EnMemoire(javax.tools.JavaFileManager delegue) {
            super(delegue);
        }

        @Override
        public JavaFileObject getJavaFileForOutput(
                javax.tools.JavaFileManager.Location emplacement, String nom,
                JavaFileObject.Kind genre, javax.tools.FileObject source)
                throws IOException {
            // Seule la sortie des .class est detournee. Le reste — les
            // ressources, par exemple — continue vers le gestionnaire du JDK.
            if (emplacement == StandardLocation.CLASS_OUTPUT
                    && genre == JavaFileObject.Kind.CLASS) {
                var produite = new ClasseEnMemoire(nom);
                produites.put(nom, produite);
                return produite;
            }
            return super.getJavaFileForOutput(emplacement, nom, genre, source);
        }

        /**
         * Un chargeur qui sert les classes compilées, et délègue le reste.
         *
         * <p>Il délègue à son parent d'abord — sans quoi le code compilé
         * verrait deux {@code java.lang.String} différents. Les classes qu'il
         * connaît sont exactement celles que cette compilation a produites,
         * classes internes et {@code record} imbriqués compris.
         */
        ClassLoader chargeur() {
            return new ClassLoader(Compilateur.class.getClassLoader()) {
                @Override
                protected Class<?> findClass(String nom)
                        throws ClassNotFoundException {
                    var produite = produites.get(nom);
                    if (produite == null) {
                        throw new ClassNotFoundException(nom);
                    }
                    byte[] octets = produite.octets();
                    return defineClass(nom, octets, 0, octets.length);
                }
            };
        }
    }
}
