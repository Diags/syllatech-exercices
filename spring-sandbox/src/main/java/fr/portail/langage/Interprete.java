package fr.portail.langage;

import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.Function;

/**
 * Le petit langage dans lequel un candidat rend sa solution.
 *
 * <p>POURQUOI UN LANGAGE PLUTOT QUE PYTHON
 * <p>Parce que le cours n'enseigne pas Python : il enseigne <em>ou</em> le
 * code d'un inconnu s'execute, et ce qu'il peut y faire. Un langage minuscule
 * — huit verbes — suffit a poser la question, et il a une propriete qu'aucun
 * vrai langage n'a : on peut le faire tourner des DEUX cotes de la frontiere
 * et comparer.
 *
 * <p>LES VERBES, ET CE QU'ILS OUVRENT
 * <pre>
 *   ecrire &lt;texte&gt;            ecrit sur la sortie standard
 *   somme &lt;a&gt; &lt;b&gt;             ecrit la somme
 *   sortie &lt;n&gt;                termine avec ce code
 *   lire_fichier &lt;chemin&gt;     ⚠️ LIT LE DISQUE DE L'HOTE
 *   connexion &lt;hote&gt; &lt;port&gt;   ⚠️ OUVRE UNE CONNEXION SORTANTE
 *   secret &lt;nom&gt;              ⚠️ LIT UNE PROPRIETE DE L'APPLICATION
 *   boucle                    boucle sans fin
 *   memoire &lt;mo&gt;              alloue jusqu'a saturation
 * </pre>
 *
 * <p>⚠️ LES TROIS VERBES MARQUES SONT LA MENACE, ET ILS SONT REELS. Dans la
 * JVM de l'application, {@code lire_fichier} lit vraiment un fichier et
 * {@code secret} lit vraiment une propriete Spring. Le chapitre 1 le mesure,
 * et c'est la seule facon de rendre l'argument indiscutable.
 *
 * <p>L'interprete ne decide pas seul de ce qu'il autorise : il recoit un
 * {@link Politique}. C'est deliberate — la politique se voit, se teste, et
 * surtout elle ne suffit pas : le chapitre 3 montre ce que la FRONTIERE DE
 * PROCESSUS ajoute par-dessus.
 */
public final class Interprete {

    /** Le nombre de caracteres au-dela duquel la sortie est tronquee. */
    public static final int PLAFOND_DE_SORTIE = 10_000;

    private final Politique politique;
    private final Function<String, String> lecteurDeSecrets;

    public Interprete(Politique politique) {
        this(politique, nom -> null);
    }

    /**
     * @param lecteurDeSecrets ce qui donne acces aux proprietes de
     *     l'application. Dans la JVM de l'application, c'est le contexte
     *     Spring lui-meme — et c'est exactement le probleme.
     */
    public Interprete(Politique politique,
                      Function<String, String> lecteurDeSecrets) {
        this.politique = politique;
        this.lecteurDeSecrets = lecteurDeSecrets;
    }

    /** Ce qu'une execution produit. */
    public record Trace(String sortie, String erreurs, int code) {}

    public Trace executer(String source) {
        StringBuilder sortie = new StringBuilder();
        StringBuilder erreurs = new StringBuilder();
        int code = 0;
        try {
            code = derouler(source, sortie, erreurs);
        } catch (RefusDePrivilege refus) {
            erreurs.append(refus.getMessage()).append('\n');
            code = 77;
        } catch (ErreurScript erreur) {
            erreurs.append(erreur.getMessage()).append('\n');
            code = 2;
        } catch (RuntimeException | OutOfMemoryError autre) {
            erreurs.append(autre.getClass().getSimpleName())
                   .append(" : ").append(autre.getMessage()).append('\n');
            code = 1;
        }
        return new Trace(tronquer(sortie.toString()),
                         tronquer(erreurs.toString()), code);
    }

    private int derouler(String source, StringBuilder sortie,
                         StringBuilder erreurs) {
        for (String brute : source.split("\\R")) {
            String ligne = brute.strip();
            if (ligne.isEmpty() || ligne.startsWith("#")) {
                continue;
            }
            List<String> mots = decouper(ligne);
            String verbe = mots.getFirst();
            List<String> arguments = mots.subList(1, mots.size());

            switch (verbe) {
                case "ecrire" -> sortie.append(String.join(" ", arguments))
                                       .append('\n');
                case "somme" -> sortie.append(entier(arguments, 0)
                                              + entier(arguments, 1))
                                      .append('\n');
                case "sortie" -> {
                    return entier(arguments, 0);
                }
                case "lire_fichier" -> sortie.append(lireLeFichier(argument(arguments, 0)))
                                             .append('\n');
                case "connexion" -> sortie.append(seConnecter(
                        argument(arguments, 0), entier(arguments, 1))).append('\n');
                case "secret" -> sortie.append(lireLeSecret(argument(arguments, 0)))
                                       .append('\n');
                case "boucle" -> boucler();
                case "memoire" -> devorer(entier(arguments, 0));
                default -> throw new ErreurScript(
                        "verbe inconnu : « " + verbe + " »");
            }
        }
        return 0;
    }

    // -- les trois verbes qui font le cours --------------------------------

    private String lireLeFichier(String chemin) {
        politique.exiger(Capacite.FICHIERS, "lire_fichier " + chemin);
        try {
            return Files.readString(Path.of(chemin), StandardCharsets.UTF_8)
                        .strip();
        } catch (IOException erreur) {
            throw new ErreurScript("lecture impossible : " + erreur.getMessage());
        }
    }

    private String seConnecter(String hote, int port) {
        politique.exiger(Capacite.RESEAU, "connexion " + hote + ":" + port);
        try (Socket prise = new Socket()) {
            prise.connect(new InetSocketAddress(hote, port), 400);
            return "connecte a " + hote + ":" + port;
        } catch (IOException erreur) {
            throw new ErreurScript("connexion refusee : " + erreur.getMessage());
        }
    }

    private String lireLeSecret(String nom) {
        politique.exiger(Capacite.PROPRIETES, "secret " + nom);
        String valeur = lecteurDeSecrets.apply(nom);
        if (valeur == null) {
            throw new ErreurScript("propriete absente : " + nom);
        }
        return valeur;
    }

    // -- les deux verbes qui epuisent --------------------------------------

    @SuppressWarnings("InfiniteLoopStatement")
    private void boucler() {
        long compteur = 0;
        while (true) {
            compteur++;
            if (compteur == Long.MAX_VALUE) {
                compteur = 0;   // pour que le compilateur ne l'elimine pas
            }
        }
    }

    private void devorer(int mebioctets) {
        List<byte[]> retenus = new ArrayList<>();
        for (int i = 0; i < mebioctets; i++) {
            retenus.add(new byte[1024 * 1024]);
        }
        // On garde la reference jusqu'ici : sans cela, le ramasse-miettes
        // libere au fur et a mesure et rien ne sature.
        if (retenus.size() < 0) {
            throw new IllegalStateException();
        }
    }

    // -- outillage ---------------------------------------------------------

    static List<String> decouper(String ligne) {
        List<String> mots = new ArrayList<>();
        StringBuilder courant = new StringBuilder();
        boolean entreGuillemets = false;
        for (char caractere : ligne.toCharArray()) {
            if (caractere == '"') {
                entreGuillemets = !entreGuillemets;
            } else if (Character.isWhitespace(caractere) && !entreGuillemets) {
                if (!courant.isEmpty()) {
                    mots.add(courant.toString());
                    courant.setLength(0);
                }
            } else {
                courant.append(caractere);
            }
        }
        if (!courant.isEmpty()) {
            mots.add(courant.toString());
        }
        if (mots.isEmpty()) {
            throw new ErreurScript("ligne vide apres decoupage");
        }
        return mots;
    }

    private static String argument(List<String> arguments, int rang) {
        if (rang >= arguments.size()) {
            throw new ErreurScript("argument manquant au rang " + rang);
        }
        return arguments.get(rang);
    }

    private static int entier(List<String> arguments, int rang) {
        try {
            return Integer.parseInt(argument(arguments, rang));
        } catch (NumberFormatException erreur) {
            throw new ErreurScript(
                    "entier attendu : « " + argument(arguments, rang) + " »");
        }
    }

    /**
     * ⚠️ La sortie d'un sandbox est une donnee HOSTILE, et elle peut etre
     * enorme. Un candidat qui ecrit dix millions de lignes sature la memoire
     * du runner, pas la sienne. Le plafond se pose ICI, avant que la chaine
     * ne traverse HTTP.
     */
    public static String tronquer(String texte) {
        if (texte.length() <= PLAFOND_DE_SORTIE) {
            return texte;
        }
        return texte.substring(0, PLAFOND_DE_SORTIE) + "…(tronque)";
    }
}
