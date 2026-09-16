package fr.portail.chapitres;

import fr.portail.commun.Console;
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

/**
 * Chapitre 4 — Lambdas et Streams.
 *
 * <p>« Rien ne s'exécute tant que l'opération terminale n'est pas appelée » :
 * c'est une affirmation sur ce qui se passe, donc elle se compte. Ce chapitre
 * met un compteur dans le pipeline et regarde combien d'éléments le
 * traversent réellement — y compris dans un cas où la réponse est
 * <strong>zéro</strong>.
 */
public final class Chapitre4Streams {

    private Chapitre4Streams() {
    }

    private static final List<Candidat> VIVIER = List.of(
            Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING, Competence.SQL),
            Candidat.de("Karim Bensaid", 3, Competence.PYTHON, Competence.DOCKER),
            Candidat.de("Lea Marchand", 9, Competence.JAVA, Competence.SQL, Competence.KUBERNETES),
            Candidat.de("Tom Nkosi", 1, Competence.REACT),
            Candidat.de("Ines Roux", 5, Competence.JAVA, Competence.TERRAFORM),
            Candidat.de("Malik Sy", 12, Competence.JAVA, Competence.SPRING, Competence.KUBERNETES));

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "COMBIEN D'ELEMENTS TRAVERSENT VRAIMENT LE PIPELINE ?");
        var sansTerminal = new AtomicInteger();
        var chaine = VIVIER.stream().peek(c -> sansTerminal.incrementAndGet())
                .filter(c -> c.anneesExperience() >= 5);
        Console.ligne("pipeline construit, pas de terminal",
                sansTerminal.get() + " element(s) vu(s)", 40);
        long combien = chaine.count();
        Console.ligne("apres `.count()`",
                sansTerminal.get() + " element(s) vu(s), resultat " + combien, 40);
        System.out.println();
        var jusquAuPremier = new AtomicInteger();
        var premier = VIVIER.stream().peek(c -> jusquAuPremier.incrementAndGet())
                .filter(c -> c.anneesExperience() >= 5)
                .findFirst();
        Console.ligne("`findFirst` sur " + VIVIER.size() + " candidats",
                jusquAuPremier.get() + " vus, trouve "
                        + premier.map(Candidat::prenom).orElse("-"), 40);
        var infini = new AtomicInteger();
        var premierMultiple = Stream.iterate(1, n -> n + 1)
                .peek(n -> infini.incrementAndGet())
                .filter(n -> n % 7 == 0)
                .findFirst();
        Console.ligne("le meme, sur un flux INFINI",
                infini.get() + " vus, trouve " + premierMultiple.orElse(-1), 40);
        System.out.println();
        Console.texte("Un flux infini qui se termine. C'est la paresse rendue "
                + "visible : `filter` ne parcourt rien, il DECRIT un filtre ; "
                + "c'est `findFirst` qui tire les elements, un par un, et qui "
                + "s'arrete des qu'il a ce qu'il veut.");

        Console.titre(2, "LE CAS OU LE COMPTEUR RESTE A ZERO");
        var vusSansFiltre = new AtomicInteger();
        long tailleDirecte = VIVIER.stream()
                .peek(c -> vusSansFiltre.incrementAndGet()).count();
        var vusAvecFiltre = new AtomicInteger();
        long tailleFiltree = VIVIER.stream().filter(c -> true)
                .peek(c -> vusAvecFiltre.incrementAndGet()).count();
        Console.ligne("`stream().peek(...).count()`",
                "resultat " + tailleDirecte + ", peek a vu "
                        + vusSansFiltre.get(), 40);
        Console.ligne("`stream().filter(...).peek(...).count()`",
                "resultat " + tailleFiltree + ", peek a vu "
                        + vusAvecFiltre.get(), 44);
        System.out.println();
        Console.texte("Zero. `count()` sait que la source est une `List` de "
                + "taille connue et qu'aucune operation ne peut changer ce "
                + "nombre : il rend la taille sans rien executer. Ajoutez un "
                + "`filter`, la taille devient inconnue, et le pipeline "
                + "tourne.");
        System.out.println();
        Console.texte("La lecon n'est pas « `peek` est casse » : c'est que "
                + "`peek` n'est pas un endroit ou faire quelque chose "
                + "d'important. Sa documentation le dit — il existe pour "
                + "observer pendant une mise au point. Un effet de bord qui "
                + "compte ne se met pas dans un pipeline.");

        Console.titre(3, "`sorted` AVANT `limit` : TOUT EST CONSOMME");
        var vusTries = new AtomicInteger();
        var troisPlusAnciens = IntStream.rangeClosed(1, 100).boxed()
                .peek(n -> vusTries.incrementAndGet())
                .sorted(Comparator.reverseOrder())
                .limit(3)
                .toList();
        var vusLimites = new AtomicInteger();
        var troisPremiers = IntStream.rangeClosed(1, 100).boxed()
                .peek(n -> vusLimites.incrementAndGet())
                .limit(3)
                .toList();
        Console.ligne("`sorted().limit(3)` sur 100",
                troisPlusAnciens + " apres " + vusTries.get() + " elements", 34);
        Console.ligne("`limit(3)` seul sur 100",
                troisPremiers + " apres " + vusLimites.get() + " elements", 34);
        System.out.println();
        Console.texte("`sorted` est a etat : il lui faut le flux entier avant "
                + "de produire le premier element trie. Le "
                + "court-circuit de `limit` ne peut donc rien economiser en "
                + "amont — il economise seulement ce qui vient apres. C'est "
                + "exactement ce que le support de cours annonce, et le "
                + "compteur le confirme : 100 contre 3.");

        Console.titre(4, "UN FLUX NE SE REJOUE PAS");
        var flux = VIVIER.stream().filter(c -> c.anneesExperience() > 4);
        long premiere = flux.count();
        String seconde;
        try {
            seconde = String.valueOf(flux.count());
        } catch (IllegalStateException erreur) {
            seconde = "IllegalStateException — " + erreur.getMessage();
        }
        Console.ligne("premier appel", String.valueOf(premiere), 20);
        Console.ligne("second appel", seconde, 20);
        System.out.println();
        Console.texte("Un `Stream` n'est pas une collection : c'est un "
                + "PARCOURS. Une fois parcouru, il est fini. Si le meme "
                + "pipeline doit servir deux fois, on garde la source — la "
                + "liste — et on refait `stream()` ; ou bien on garde un "
                + "`Supplier<Stream<...>>`.");

        Console.titre(5, "REFERMER LE PIPELINE SUR UNE STRUCTURE");
        var parAnciennete = VIVIER.stream().collect(Collectors.groupingBy(
                c -> c.anneesExperience() >= 5 ? "confirme" : "junior",
                TreeMap::new,
                Collectors.mapping(Candidat::prenom, Collectors.joining(", "))));
        parAnciennete.forEach((groupe, noms) -> Console.ligne("  " + groupe, noms, 14));
        System.out.println();
        var parCompetence = VIVIER.stream()
                .flatMap(c -> c.competences().stream())
                .collect(Collectors.groupingBy(Competence::libelle,
                        TreeMap::new, Collectors.counting()));
        Console.ligne("competences du vivier", parCompetence.toString(), 26);
        var extremes = VIVIER.stream().collect(Collectors.teeing(
                Collectors.minBy(Comparator.comparingInt(Candidat::anneesExperience)),
                Collectors.maxBy(Comparator.comparingInt(Candidat::anneesExperience)),
                (min, max) -> min.map(Candidat::prenom).orElse("-") + " .. "
                        + max.map(Candidat::prenom).orElse("-")));
        Console.ligne("teeing (le moins / le plus)", extremes, 26);
        System.out.println();
        String verdictToMap;
        try {
            VIVIER.stream().collect(Collectors.toMap(
                    c -> c.anneesExperience() >= 5, Candidat::prenom));
            verdictToMap = "accepte";
        } catch (IllegalStateException erreur) {
            verdictToMap = "IllegalStateException : " + erreur.getMessage();
        }
        Console.ligne("`toMap` avec des cles en double", verdictToMap, 34);
        var avecGroupingBy = VIVIER.stream().collect(Collectors.groupingBy(
                c -> c.anneesExperience() >= 5, Collectors.counting()));
        Console.ligne("`groupingBy` sur la meme cle",
                avecGroupingBy.toString(), 34);
        System.out.println();
        Console.texte("`toMap` refuse les doublons — et il a raison : sans "
                + "regle de fusion, garder le premier ou le dernier serait "
                + "arbitraire. La version a trois arguments prend cette regle "
                + "en parametre. `groupingBy`, lui, ne se pose pas la "
                + "question : sa valeur est une collection.");

        Console.titre(6, "`orElse` CALCULE MEME QUAND IL N'A RIEN A FAIRE");
        var appelsOrElse = new AtomicInteger();
        var appelsOrElseGet = new AtomicInteger();
        Optional.of("un candidat").orElse(coutDeux(appelsOrElse));
        Optional.of("un candidat").orElseGet(() -> coutDeux(appelsOrElseGet));
        Console.ligne("`orElse(calculDefaut())` sur un Optional PLEIN",
                appelsOrElse.get() + " appel(s) au calcul", 46);
        Console.ligne("`orElseGet(() -> calculDefaut())` sur le meme",
                appelsOrElseGet.get() + " appel(s) au calcul", 46);
        System.out.println();
        Console.texte("`orElse` prend une VALEUR : pour la lui passer, Java "
                + "doit d'abord la calculer. `orElseGet` prend une FONCTION, "
                + "qu'il n'appelle que s'il en a besoin. Tant que le defaut "
                + "est une constante, aucune importance ; des qu'il ouvre une "
                + "connexion ou lit un fichier, l'ecart est entier.");

        Console.titre(7, "LE PARALLELE N'EST PAS UN INTERRUPTEUR");
        var partagee = new ArrayList<Integer>();
        String etatListe;
        try {
            IntStream.range(0, 10_000).parallel().boxed().forEach(partagee::add);
            etatListe = partagee.size() + " elements sur 10000";
        } catch (RuntimeException erreur) {
            etatListe = erreur.getClass().getSimpleName();
        }
        var correcte = IntStream.range(0, 10_000).parallel().boxed().toList();
        Console.ligne("`forEach(liste::add)` en parallele", etatListe, 38);
        Console.ligne("`toList()` en parallele",
                correcte.size() + " elements", 38);
        System.out.println();
        var sequentiel = IntStream.rangeClosed(1, 20).boxed().reduce(0, (a, b) -> a - b);
        var parallele = IntStream.rangeClosed(1, 20).boxed().parallel()
                .reduce(0, (a, b) -> a - b);
        Console.ligne("`reduce(0, (a,b) -> a - b)` sequentiel",
                String.valueOf(sequentiel), 40);
        Console.ligne("   le meme, en parallele", String.valueOf(parallele), 40);
        System.out.println();
        Console.texte("Aucune exception dans les deux cas, et deux resultats "
                + "faux. La soustraction n'est pas associative : le parallele "
                + "regroupe les operations autrement, et obtient autre chose. "
                + "`.parallel()` n'est pas une optimisation gratuite — il "
                + "exige que l'operation soit associative et sans etat "
                + "partage. Quand elle l'est, `toList` et les `Collectors` "
                + "s'en chargent correctement.");

        Console.titre(8, "CE QU'UNE LAMBDA A LE DROIT DE CAPTURER");
        if (Compilateur.disponible()) {
            for (var essai : List.of(
                    new Essai("capturer une variable qui ne change plus", """
                            public class Extrait {
                              static Runnable m() {
                                int seuil = 5;
                                return () -> System.out.println(seuil);
                              }
                            }
                            """),
                    new Essai("capturer une variable qu'on modifie ensuite", """
                            public class Extrait {
                              static Runnable m() {
                                int seuil = 5;
                                Runnable r = () -> System.out.println(seuil);
                                seuil = 6;
                                return r;
                              }
                            }
                            """),
                    new Essai("contourner avec un tableau d'un element", """
                            public class Extrait {
                              static Runnable m() {
                                int[] seuil = {5};
                                Runnable r = () -> System.out.println(seuil[0]);
                                seuil[0] = 6;
                                return r;
                              }
                            }
                            """))) {
                var verdict = Compilateur.compiler("Extrait", essai.source());
                Console.ligne("  " + essai.titre(),
                        verdict.compile() ? "compile" : "REFUSE", 44);
                if (verdict.refuse()) {
                    Console.texte(verdict.premiereErreur().lines().findFirst().orElse(""), 6);
                }
            }
            System.out.println();
            Console.texte("La troisieme COMPILE, et c'est le piege : la regle "
                    + "porte sur la VARIABLE, pas sur ce qu'elle designe. Un "
                    + "tableau d'un element la contourne — et rend a la "
                    + "lambda exactement l'etat partage que la regle voulait "
                    + "eviter. Si vous ecrivez cela, vous etes en train de "
                    + "faire une boucle deguisee.");
        }

        Console.titre(9, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Dix mille taches lancees deux fois : sur un pool de "
                + "seize threads, puis sur des threads virtuels. Et huit "
                + "threads qui incrementent le meme compteur, pour voir "
                + "combien d'incrementations disparaissent.");
        System.out.println();
    }

    /** Un « calcul coûteux » qui se contente de signaler qu'on l'a appelé. */
    private static String coutDeux(AtomicInteger compteur) {
        compteur.incrementAndGet();
        return "aucun candidat";
    }

    private record Essai(String titre, String source) {
    }
}
