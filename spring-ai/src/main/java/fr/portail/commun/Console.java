package fr.portail.commun;

import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * Le peu que les six chapitres partagent.
 *
 * <p>Volontairement minuscule : un chapitre doit rester lisible seul, et un
 * module commun qui grossit finit par être l'endroit où le cours se cache.
 */
public final class Console {

    private Console() {
    }

    private static boolean sortieDejaForcee;

    /**
     * Les chapitres affichent « paresseux » et des guillemets français.
     *
     * <p>Depuis Java 18, {@code file.encoding} vaut UTF-8 par défaut — mais
     * {@code stdout.encoding} suit la console, et celle de Windows est en
     * cp1252. Sans cette ligne, les accents sortent en charabia ; avec, ils
     * sortent juste. C'est le pendant exact du {@code utf8()} des projets
     * Python de ce catalogue.
     *
     * <p>⚠️ Cette méthode ne fait rien si la sortie est <strong>déjà</strong>
     * en UTF-8. Ce n'est pas une optimisation : rebrancher {@code System.out}
     * sur {@code FileDescriptor.out} court-circuite toute redirection posée
     * par l'appelant — et {@code ChapitresTest} en pose une pour lire ce que
     * les chapitres écrivent. Sans ce garde-fou, le test capturait zéro
     * ligne, et l'a fait savoir.
     */
    public static void utf8() {
        if (sortieDejaForcee) {
            return;
        }
        if ("UTF-8".equalsIgnoreCase(System.getProperty("stdout.encoding"))) {
            return;
        }
        System.setOut(new PrintStream(new java.io.FileOutputStream(
                java.io.FileDescriptor.out), true, StandardCharsets.UTF_8));
        sortieDejaForcee = true;
    }

    public static void titre(int numero, String texte) {
        System.out.println();
        System.out.println(numero + ". " + texte);
        System.out.println("   " + "─".repeat(texte.length()));
    }

    /** Une intertitre à l'intérieur d'une section. */
    public static void sousTitre(String texte) {
        System.out.println();
        System.out.println("   " + texte);
    }

    public static void ligne(String gauche, String droite, int largeur) {
        // Une ligne sans valeur a droite ne doit pas laisser de blancs en fin
        // de ligne : ils se voient dans un diff, et pas a l'ecran.
        if (droite.isEmpty()) {
            System.out.println("   " + gauche);
            return;
        }
        System.out.printf("   %-" + largeur + "s %s%n", gauche, droite);
    }

    public static void ligne(String gauche, String droite) {
        ligne(gauche, droite, 34);
    }

    public static void tableau(List<String> entetes, List<List<String>> lignes,
                               List<Integer> largeurs) {
        var tete = new StringBuilder("   ");
        var barre = new StringBuilder("   ");
        for (int i = 0; i < entetes.size(); i++) {
            tete.append(remplir(entetes.get(i), largeurs.get(i)));
            barre.append("─".repeat(largeurs.get(i) - 2)).append("  ");
        }
        System.out.println(tete.toString().stripTrailing());
        System.out.println(barre.toString().stripTrailing());
        for (var rang : lignes) {
            var sortie = new StringBuilder("   ");
            for (int i = 0; i < rang.size() && i < largeurs.size(); i++) {
                sortie.append(remplir(rang.get(i), largeurs.get(i)));
            }
            System.out.println(sortie.toString().stripTrailing());
        }
    }

    /** Plie un paragraphe à la largeur voulue et l'imprime, indenté. */
    public static void texte(String contenu) {
        for (var l : plier(contenu, 64)) {
            System.out.println("   " + l);
        }
    }

    public static void texte(String contenu, int indentation) {
        for (var l : plier(contenu, 66 - indentation)) {
            System.out.println(" ".repeat(indentation) + l);
        }
    }

    /**
     * Imprime un texte de plusieurs lignes — un prompt, un document — en
     * respectant ses retours à la ligne et en pliant ce qui dépasse.
     *
     * <p>⚠️ <strong>Pourquoi cette méthode existe.</strong> Les chapitres
     * faisaient une boucle sur {@code contenu.lines()} puis appelaient
     * {@link #texte(String, int)} sur chaque ligne. Or {@code texte} plie
     * <em>lui aussi</em> : une ligne déjà pliée à 64 était repliée à 60, et
     * le dernier mot tombait seul sur une ligne. Le texte semblait haché
     * sans raison. Plier deux fois n'est jamais plier mieux — on plie ici
     * une seule fois, à la largeur réelle.
     */
    public static void bloc(String contenu, int indentation) {
        for (var ligne : contenu.lines().toList()) {
            if (ligne.isBlank()) {
                System.out.println();
                continue;
            }
            for (var pliee : plier(ligne, 66 - indentation)) {
                System.out.println(" ".repeat(indentation) + pliee);
            }
        }
    }

    /**
     * La ponctuation française qui veut une espace <em>avant</em> elle.
     *
     * <p>En français, {@code :} {@code ;} {@code ?} {@code !} et le guillemet
     * fermant sont précédés d'une espace — mais d'une espace insécable. Un
     * pliage naïf coupe à cette espace et fait commencer la ligne suivante
     * par un deux-points isolé. C'est exactement ce qui arrivait ici avant
     * cette correction.
     */
    private static final java.util.Set<String> PONCTUATION_COLLEE =
            java.util.Set.of(":", ";", "?", "!", "»", "…");

    public static List<String> plier(String contenu, int largeur) {
        var lignes = new ArrayList<String>();
        var courante = new StringBuilder();
        for (var mot : souder(contenu.split("\\s+"))) {
            if (courante.length() + mot.length() + 1 > largeur
                    && !courante.isEmpty()) {
                lignes.add(courante.toString());
                courante.setLength(0);
            }
            if (!courante.isEmpty()) {
                courante.append(' ');
            }
            courante.append(mot);
        }
        if (!courante.isEmpty()) {
            lignes.add(courante.toString());
        }
        return lignes;
    }

    /**
     * Soude à leur voisin les signes qui ne doivent jamais ouvrir une ligne
     * — ni la fermer, pour le guillemet ouvrant.
     */
    private static List<String> souder(String[] mots) {
        var soudes = new ArrayList<String>();
        boolean attendLaSuite = false;
        for (var mot : mots) {
            if (mot.isEmpty()) {
                continue;
            }
            boolean suitSonMot = PONCTUATION_COLLEE.contains(mot)
                    || (mot.length() == 2
                        && PONCTUATION_COLLEE.contains(mot.substring(0, 1)));
            if ((attendLaSuite || suitSonMot) && !soudes.isEmpty()) {
                soudes.set(soudes.size() - 1,
                        soudes.getLast() + " " + mot);
            } else {
                soudes.add(mot);
            }
            attendLaSuite = mot.endsWith("«");
        }
        return soudes;
    }

    private static String remplir(String texte, int largeur) {
        return texte.length() >= largeur ? texte
                : texte + " ".repeat(largeur - texte.length());
    }
}
