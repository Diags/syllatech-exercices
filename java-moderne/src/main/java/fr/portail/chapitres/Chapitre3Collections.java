package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.mesure.Compilateur;
import fr.portail.pieges.CleMuable;
import fr.portail.pieges.PanierSansCopie;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * Chapitre 3 — Collections et génériques.
 *
 * <p>Le cours dit : « si vous redéfinissez l'une sans l'autre, vos objets se
 * perdent dans les HashMap ». Ce chapitre va plus loin : il montre le cas où
 * les <em>deux</em> sont correctement écrites et où l'objet se perd quand
 * même — parce que le champ dont elles dépendent a bougé. Puis il montre que
 * le même piège atteint un {@code record}, réputé immuable.
 */
public final class Chapitre3Collections {

    private Chapitre3Collections() {
    }

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "UNE CLE RANGEE, PUIS DEPLACEE");
        var cle = new CleMuable("java");
        var offres = new HashMap<CleMuable, String>();
        offres.put(cle, "OFF-2026-014");
        Console.ligne("apres put, get(cle)", String.valueOf(offres.get(cle)), 34);
        cle.changer("java17");
        Console.ligne("on modifie le champ de la cle", "cle.changer(\"java17\")", 34);
        Console.ligne("get(cle)", String.valueOf(offres.get(cle)), 34);
        Console.ligne("containsKey(cle)", String.valueOf(offres.containsKey(cle)), 34);
        Console.ligne("keySet().contains(cle)",
                String.valueOf(offres.keySet().contains(cle)), 34);
        Console.ligne("size()", String.valueOf(offres.size()), 34);
        var vues = new StringBuilder();
        offres.forEach((k, v) -> vues.append(k).append("=").append(v).append(" "));
        Console.ligne("ce que l'iteration voit", vues.toString().strip(), 34);
        cle.changer("java");
        Console.ligne("on remet l'ancienne valeur", String.valueOf(offres.get(cle)), 34);
        System.out.println();
        Console.texte("L'entree n'a jamais disparu : `size()` vaut 1 et "
                + "l'iteration la voit. Elle est rangee dans le casier de son "
                + "ANCIEN code, et `get` la cherche dans celui du nouveau. "
                + "Remettre le champ a sa valeur d'origine la fait "
                + "reapparaitre — ce qui est la preuve que rien n'etait "
                + "perdu, seulement mal range.");
        System.out.println();
        Console.texte("Ici `equals` et `hashCode` sont tous les deux ecrits, "
                + "et coherents entre eux. Le contrat que le cours rappelle "
                + "est respecte. Il en manque un second, moins souvent dit : "
                + "une cle de table de hachage ne doit pas changer tant "
                + "qu'elle est dedans.");

        Console.titre(2, "LE MEME PIEGE, DANS UN `record`");
        var articles = new ArrayList<>(List.of("cv.pdf"));
        var panier = new PanierSansCopie("Awa", articles);
        int empreinteAvant = panier.hashCode();
        var ensemble = new HashSet<PanierSansCopie>();
        ensemble.add(panier);
        Console.ligne("avant", panier.toString(), 22);
        Console.ligne("contains(lui-meme)", String.valueOf(ensemble.contains(panier)), 34);
        articles.add("lettre.pdf");
        Console.ligne("apres `articles.add(...)`", panier.toString(), 34);
        Console.ligne("le hashCode a change ?",
                String.valueOf(empreinteAvant != panier.hashCode()), 34);
        Console.ligne("contains(lui-meme)", String.valueOf(ensemble.contains(panier)), 34);
        System.out.println();
        Console.texte("Personne n'a touche au record. On a modifie la liste "
                + "qu'on lui avait passee — et qu'il a gardee telle quelle. "
                + "« Immuable » decrit ses REFERENCES : on ne peut pas "
                + "reaffecter `articles`. Ce que la reference designe, lui, "
                + "reste modifiable si on l'a laisse modifiable.");
        System.out.println();
        var copie = Candidat.de("Awa Diallo", 6, Competence.JAVA);
        Console.ligne("`Candidat`, avec Set.copyOf",
                copie.competences().getClass().getSimpleName(), 34);
        String tentative;
        try {
            copie.competences().add(Competence.DOCKER);
            tentative = "accepte — la copie ne protege pas";
        } catch (UnsupportedOperationException erreur) {
            tentative = "UnsupportedOperationException";
        }
        Console.ligne("   y ajouter une competence", tentative, 34);
        System.out.println();
        Console.texte("Une ligne dans le bloc compact — "
                + "`competences = Set.copyOf(competences)` — et le record "
                + "redevient ce qu'on croyait qu'il etait. C'est le genre de "
                + "detail qu'un cours passe sous silence parce qu'il rallonge "
                + "l'exemple ; c'est aussi celui qui cause le bug.");

        Console.titre(3, "CINQ FACONS DE DIRE « NON MODIFIABLE »");
        var modifiable = new ArrayList<>(List.of("a"));
        var essais = List.<Map.Entry<String, List<String>>>of(
                Map.entry("new ArrayList<>()", new ArrayList<>(List.of("a"))),
                Map.entry("Arrays.asList(...)", Arrays.asList("a")),
                Map.entry("List.of(...)", List.of("a")),
                Map.entry("List.copyOf(...)", List.copyOf(modifiable)),
                Map.entry("unmodifiableList(...)", Collections.unmodifiableList(modifiable)));
        var lignes = new ArrayList<List<String>>();
        for (var essai : essais) {
            lignes.add(List.of(essai.getKey(),
                    tenter(() -> essai.getValue().add("b")),
                    tenter(() -> essai.getValue().set(0, "z"))));
        }
        Console.tableau(List.of("la liste vient de", "add", "set"), lignes,
                List.of(24, 30, 30));
        System.out.println();
        Console.texte("`Arrays.asList` est la ligne a retenir : elle refuse "
                + "`add` et accepte `set`. Ce n'est pas une liste non "
                + "modifiable, c'est une VUE sur un tableau — de taille fixe, "
                + "mais dont les cases s'ecrivent. Beaucoup de code la traite "
                + "comme une liste immuable, et se trompe.");
        System.out.println();
        Console.ligne("et `unmodifiableList` ?", "refuse add et set", 34);
        modifiable.add("b");
        Console.ligne("   mais la source a change", Collections
                .unmodifiableList(modifiable).toString(), 34);
        System.out.println();
        Console.texte("`unmodifiableList` est une vue : elle interdit "
                + "d'ecrire A TRAVERS elle, et refletera toute modification "
                + "faite a la liste d'origine. `List.copyOf` copie : elle est "
                + "immunisee. Deux outils tres proches, deux garanties "
                + "differentes.");

        Console.titre(4, "LES GENERIQUES SONT UNE PROMESSE DE COMPILATION");
        Console.ligne("List<String> et List<Integer>",
                new ArrayList<String>().getClass()
                        == new ArrayList<Integer>().getClass()
                        ? "la MEME classe a l'execution" : "deux classes", 34);
        System.out.println();
        Console.texte("L'effacement de type : `<String>` disparait a la "
                + "compilation. C'est pourquoi on ne peut pas ecrire "
                + "`new T[]`, ni tester `x instanceof List<String>`. La "
                + "verification a lieu AVANT, une seule fois, et la "
                + "bibliotheque d'execution n'en garde pas trace.");
        System.out.println();
        if (Compilateur.disponible()) {
            for (var essai : List.of(
                    new Essai("ajouter un int dans une List<String>", """
                            import java.util.*;
                            public class Extrait {
                              static void m() {
                                List<String> noms = new ArrayList<>();
                                noms.add(42);
                              }
                            }
                            """),
                    new Essai("le meme, en passant par un type BRUT", """
                            import java.util.*;
                            public class Extrait {
                              static Object m() {
                                List<String> noms = new ArrayList<>();
                                List brut = noms;
                                brut.add(42);
                                return noms.get(0);
                              }
                            }
                            """))) {
                var verdict = Compilateur.compiler("Extrait", essai.source());
                Console.ligne("  " + essai.titre(),
                        verdict.compile() ? "compile" : "REFUSE", 42);
                if (verdict.refuse()) {
                    Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
                }
            }
            System.out.println();
            Console.texte("La seconde COMPILE. Un type brut desactive la "
                    + "verification, l'`Integer` entre dans la liste, et "
                    + "l'explosion arrive plus tard, a la lecture :");
            var poison = new ArrayList<String>();
            @SuppressWarnings({"unchecked", "rawtypes"})
            List brut = poison;
            brut.add(42);
            try {
                String premier = poison.get(0);
                Console.texte("lu sans erreur : " + premier, 6);
            } catch (ClassCastException erreur) {
                Console.texte("ClassCastException — " + erreur.getMessage(), 6);
            }
            System.out.println();
            Console.texte("L'erreur ne designe ni la ligne qui a insere le "
                    + "42, ni meme la liste : elle sort sur un `get` qui, lui, "
                    + "est correct. C'est ce que les generiques evitent, et "
                    + "c'est ce qu'un type brut reintroduit.");
        }

        Console.titre(5, "CHOISIR SA COLLECTION, C'EST CHOISIR SON ORDRE");
        var candidats = List.of(
                Candidat.de("Awa Diallo", 6, Competence.JAVA),
                Candidat.de("Karim Bensaid", 3, Competence.PYTHON),
                Candidat.de("Lea Marchand", 9, Competence.JAVA, Competence.SQL),
                Candidat.de("Tom Nkosi", 1, Competence.REACT));
        var parDefaut = new HashMap<String, Integer>();
        var parInsertion = new LinkedHashMap<String, Integer>();
        var trie = new TreeMap<String, Integer>();
        for (var c : candidats) {
            parDefaut.put(c.prenom(), c.anneesExperience());
            parInsertion.put(c.prenom(), c.anneesExperience());
            trie.put(c.prenom(), c.anneesExperience());
        }
        Console.ligne("HashMap", String.join(", ", parDefaut.keySet()), 20);
        Console.ligne("LinkedHashMap", String.join(", ", parInsertion.keySet()), 20);
        Console.ligne("TreeMap", String.join(", ", trie.keySet()), 20);
        System.out.println();
        Console.texte("L'ordre du `HashMap` n'est pas aleatoire : il est "
                + "determine par les codes de hachage, donc stable pour ces "
                + "memes cles — et il changera si vous renommez un candidat, "
                + "ou si vous changez de version de Java. Ne jamais s'y fier. "
                + "Quand l'ordre compte, il faut le DIRE.");

        Console.titre(6, "DEUX SIGNATURES QUI SE RESSEMBLENT TROP");
        var entiers = new ArrayList<>(List.of(3, 2, 1));
        var autres = new ArrayList<>(List.of(3, 2, 1));
        entiers.remove(1);
        autres.remove(Integer.valueOf(1));
        Console.ligne("[3, 2, 1].remove(1)", entiers.toString(), 34);
        Console.ligne("[3, 2, 1].remove(Integer.valueOf(1))", autres.toString(), 38);
        System.out.println();
        Console.texte("`List` a deux methodes `remove` : une qui prend un "
                + "INDICE, une qui prend un OBJET. Sur une `List<Integer>` "
                + "les deux acceptent le meme litteral, et le compilateur "
                + "choisit celle qui prend l'indice — sans un avertissement. "
                + "Le seul moyen de demander l'autre est de la forcer.");
        System.out.println();
        var vivante = new ArrayList<>(List.of("a", "b", "c"));
        for (var element : List.of("a", "b", "c")) {
            var liste = new ArrayList<>(List.of("a", "b", "c"));
            String resultat;
            try {
                for (var x : liste) {
                    if (x.equals(element)) {
                        liste.remove(x);
                    }
                }
                resultat = "silencieux — reste " + liste;
            } catch (java.util.ConcurrentModificationException erreur) {
                resultat = "ConcurrentModificationException";
            }
            Console.ligne("  retirer \"" + element + "\" pendant un for-each",
                    resultat, 40);
        }
        vivante.removeIf(x -> x.equals("b"));
        Console.ligne("  removeIf", vivante.toString(), 40);
        System.out.println();
        Console.texte("Le cas du milieu est le plus dangereux : retirer "
                + "l'avant-dernier element ne leve AUCUNE exception. "
                + "L'iterateur compare sa position a la taille, la taille "
                + "vient de diminuer, la boucle s'arrete une position trop "
                + "tot — et le dernier element n'est jamais vu. Un bug "
                + "silencieux, la ou les deux autres cas font du bruit.");

        Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Un flux infini dont on ne lit que sept elements ; un "
                + "`count()` qui saute tout le pipeline ; et un "
                + "`Collectors.toMap` qui refuse ce que `groupingBy` accepte.");
        System.out.println();
    }

    private static String tenter(Runnable geste) {
        try {
            geste.run();
            return "accepte";
        } catch (RuntimeException erreur) {
            return erreur.getClass().getSimpleName();
        }
    }

    private record Essai(String titre, String source) {
    }
}
