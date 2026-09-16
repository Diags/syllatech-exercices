package fr.portail.chapitres;

import fr.portail.commun.Console;
import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.domaine.Dossier;
import fr.portail.mesure.Compilateur;
import fr.portail.pieges.CandidatEcritMain;
import fr.portail.pieges.SacCompteur;
import fr.portail.pieges.SacParComposition;
import java.util.HashSet;
import java.util.List;

/**
 * Chapitre 2 — Programmation orientée objet.
 *
 * <p>Trois affirmations du cours, mesurées :
 *
 * <ul>
 *   <li>« un record génère {@code equals}, {@code hashCode} et
 *       {@code toString} » — on les regarde, et on regarde ce qui se passe
 *       quand on les écrit à la main et qu'on en oublie un ;</li>
 *   <li>« héritez seulement pour un vrai <em>est-un</em> » — le compteur qui
 *       compte double, et sa version par composition qui compte juste ;</li>
 *   <li>« ajoutez un cas au {@code permits}, le compilateur refusera » — on
 *       le fait compiler pendant l'exécution, et on lit son refus.</li>
 * </ul>
 */
public final class Chapitre2Objets {

    private Chapitre2Objets() {
    }

    public static void main(String[] args) {
        Console.utf8();

        Console.titre(1, "CE QU'UN `record` ECRIT POUR VOUS");
        var awa = Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING);
        var memeAwa = Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING);
        Console.ligne("toString()", awa.toString(), 22);
        Console.ligne("equals sur deux objets distincts",
                String.valueOf(awa.equals(memeAwa)), 38);
        Console.ligne("meme hashCode ?",
                String.valueOf(awa.hashCode() == memeAwa.hashCode()), 38);
        Console.ligne("== (deux objets differents)",
                String.valueOf(awa == memeAwa), 38);
        var ensemble = new HashSet<Candidat>();
        ensemble.add(awa);
        Console.ligne("HashSet.contains(l'autre)",
                String.valueOf(ensemble.contains(memeAwa)), 38);
        System.out.println();
        Console.texte("Trois methodes, zero ligne ecrite. Et surtout : elles "
                + "restent coherentes. Ajoutez un composant au record demain, "
                + "les trois le prennent en compte — alors qu'une classe "
                + "ecrite a la main vous oblige a penser aux trois, a chaque "
                + "changement.");

        Console.titre(2, "LA MEME CLASSE, ECRITE A LA MAIN");
        var manuel = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
        var memeManuel = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
        var ensembleManuel = new HashSet<CandidatEcritMain>();
        ensembleManuel.add(manuel);
        Console.ligne("equals", String.valueOf(manuel.equals(memeManuel)), 38);
        Console.ligne("meme hashCode ?",
                String.valueOf(manuel.hashCode() == memeManuel.hashCode()), 38);
        Console.ligne("HashSet.contains(l'autre)",
                String.valueOf(ensembleManuel.contains(memeManuel)), 38);
        Console.ligne("List.contains(l'autre)",
                String.valueOf(List.of(manuel).contains(memeManuel)), 38);
        Console.ligne("toString()", manuel.toString(), 38);
        System.out.println();
        Console.texte("Deux objets « egaux » dont l'un ne retrouve pas l'autre. "
                + "Ce n'est pas une subtilite : `HashSet` cherche d'abord le "
                + "casier — le `hashCode` — et n'appelle `equals` que sur le "
                + "contenu de ce casier. Deux codes differents, deux casiers, "
                + "et `equals` n'est jamais appele. `List`, qui n'a pas de "
                + "casiers, retrouve l'objet : d'ou le bug qui n'apparait que "
                + "le jour ou on change de collection.");
        System.out.println();
        Console.texte("Le compilateur n'a rien dit. C'est du Java legal, et "
                + "c'est pourquoi le cours insiste : `equals` et `hashCode` "
                + "vont ensemble, ou on prend un `record`.");

        Console.titre(3, "HERITER D'UNE CLASSE QU'ON NE CONTROLE PAS");
        var parHeritage = new SacCompteur<String>();
        parHeritage.addAll(List.of("cv.pdf", "lettre.pdf", "diplome.pdf"));
        var parComposition = new SacParComposition<String>();
        parComposition.addAll(List.of("cv.pdf", "lettre.pdf", "diplome.pdf"));
        Console.tableau(List.of("un addAll de 3 elements", "compteur", "taille reelle"),
                List.of(
                        List.of("extends HashSet", String.valueOf(parHeritage.ajoutes()),
                                String.valueOf(parHeritage.size())),
                        List.of("composition", String.valueOf(parComposition.ajoutes()),
                                String.valueOf(parComposition.size()))),
                List.of(24, 12, 16));
        System.out.println();
        Console.texte("Le code des deux classes est le meme, a une ligne pres : "
                + "l'une ecrit `extends HashSet`, l'autre `private final Set "
                + "contenu`. `HashSet.addAll` appelle `add` pour chaque "
                + "element — un detail interne, que la documentation ne promet "
                + "pas de garder. La sous-classe compte donc deux fois.");
        System.out.println();
        Console.texte("Rien dans le fichier `SacCompteur.java` ne permet de "
                + "voir le bug. Il faut aller lire le code d'une classe du "
                + "JDK. C'est cela, le « probleme de la classe de base "
                + "fragile » : un contrat qui n'est pas ecrit dans les "
                + "signatures.");

        Console.titre(4, "ENCAPSULER : CE QUI SORT N'EST PAS CE QUI EST DEDANS");
        var dossier = Dossier.exemple();
        var vus = dossier.evenements();
        Console.ligne("evenements du dossier", String.valueOf(vus.size()), 34);
        String verdict;
        try {
            vus.add(new fr.portail.domaine.Evenement.Triee(
                    java.time.LocalDate.now(), false, "ajout depuis l'exterieur"));
            verdict = "accepte — et le dossier a " + dossier.evenements().size();
        } catch (UnsupportedOperationException erreur) {
            verdict = "UnsupportedOperationException";
        }
        Console.ligne("ajouter dans la liste rendue", verdict, 34);
        Console.ligne("le dossier a toujours",
                dossier.evenements().size() + " evenements", 34);
        System.out.println();
        Console.texte("`evenements()` rend une copie non modifiable. Sans "
                + "cela, n'importe quel appelant ajouterait un evenement sans "
                + "passer par `ajouter` — et la classe ne pourrait plus rien "
                + "garantir de son propre etat. L'encapsulation n'est pas le "
                + "`private` sur le champ : c'est ce qui se passe au retour.");

        Console.titre(5, "UNE HIERARCHIE FERMEE, ET UN `switch` COMPLET");
        var permis = fr.portail.domaine.Evenement.class.getPermittedSubclasses();
        Console.ligne("sealed interface Evenement", permis.length + " cas permis", 34);
        for (var cas : permis) {
            Console.ligne("   " + cas.getSimpleName(),
                    cas.isRecord() ? "record" : "classe", 34);
        }
        System.out.println();
        for (var evenement : dossier.evenements()) {
            Console.ligne("   " + evenement.date(), resumer(evenement), 16);
        }
        System.out.println();
        Console.texte("Le `switch` de `resumer` n'a pas de `default`. Il n'en "
                + "a pas besoin : le compilateur connait la liste complete des "
                + "cas, il verifie qu'ils y sont tous. Et si demain on ajoute "
                + "un cinquieme cas au `permits` ?");

        Console.titre(6, "LE COMPILATEUR, APPELE A LA BARRE");
        if (!Compilateur.disponible()) {
            Console.texte("Pas de compilateur ici : ce programme tourne sur un "
                    + "JRE. Cette mesure demande un JDK.");
            return;
        }
        String complet = """
                public class Extrait {
                  sealed interface Forme permits Cercle, Rectangle {}
                  record Cercle(double rayon) implements Forme {}
                  record Rectangle(double l, double h) implements Forme {}
                  static double aire(Forme f) {
                    return switch (f) {
                      case Cercle c    -> Math.PI * c.rayon() * c.rayon();
                      case Rectangle r -> r.l() * r.h();
                    };
                  }
                }
                """;
        String incomplet = complet.replace(
                "      case Rectangle r -> r.l() * r.h();\n", "");
        String avecDefaut = incomplet.replace(
                "    };", "      default -> 0;\n    };");
        String avecTriangle = complet
                .replace("permits Cercle, Rectangle", "permits Cercle, Rectangle, Triangle")
                .replace("  record Rectangle(double l, double h) implements Forme {}",
                        "  record Rectangle(double l, double h) implements Forme {}\n"
                        + "  record Triangle(double b, double h) implements Forme {}");

        for (var essai : List.of(
                new Essai("les deux cas traites", complet),
                new Essai("un cas manquant, sans default", incomplet),
                new Essai("le meme, avec un default", avecDefaut),
                new Essai("un Triangle ajoute au permits", avecTriangle))) {
            var resultat = Compilateur.compiler("Extrait", essai.source());
            Console.ligne("  " + essai.titre(),
                    resultat.compile() ? "compile" : "REFUSE", 36);
            if (resultat.refuse()) {
                Console.texte(resultat.premiereErreur().lines().findFirst().orElse(""), 6);
            }
        }
        System.out.println();
        Console.texte("La troisieme ligne est l'avertissement du chapitre : "
                + "ajouter un `default` fait compiler le code incomplet. Le "
                + "`default` n'est pas une securite, c'est un baillon — il "
                + "transforme l'erreur de compilation que le cours vous promet "
                + "en un comportement silencieux a l'execution. Une hierarchie "
                + "fermee ne protege que les `switch` qui n'en ont pas.");

        Console.titre(7, "CE QUE LE CHAPITRE SUIVANT MESURE");
        Console.texte("Un objet range dans un `HashMap`, puis modifie — et "
                + "introuvable ; un `record` « immuable » dont le hashCode "
                + "change tout seul ; et cinq facons de dire « non "
                + "modifiable », qui ne disent pas la meme chose.");
        System.out.println();
    }

    /**
     * Un switch exhaustif sur une hiérarchie scellée : pas de {@code default}.
     *
     * <p>Le chapitre 6 y revient avec les <em>record patterns</em>, qui
     * déconstruisent les composants au lieu d'appeler des accesseurs.
     */
    private static String resumer(fr.portail.domaine.Evenement evenement) {
        return switch (evenement) {
            case fr.portail.domaine.Evenement.Deposee d ->
                    "depot de " + d.candidat().prenom() + " sur " + d.offre().reference();
            case fr.portail.domaine.Evenement.Triee t ->
                    (t.retenue() ? "tri : retenue" : "tri : ecartee") + " (" + t.motif() + ")";
            case fr.portail.domaine.Evenement.Entretien e ->
                    "entretien avec " + e.interlocuteur() + ", note " + e.note() + "/20";
            case fr.portail.domaine.Evenement.Decision d ->
                    "decision : " + d.issue() + " — " + d.commentaire();
        };
    }

    private record Essai(String titre, String source) {
    }
}
