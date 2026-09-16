package fr.portail.chapitres;

import fr.portail.front.Composant;
import fr.portail.front.Reconciliation;
import fr.portail.front.Reconciliation.Element;
import fr.portail.front.Reconciliation.Operation;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 1 — React : les fondamentaux.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1React
 * </pre>
 *
 * <p>⚠️ AUCUN NAVIGATEUR N'EST LANCE, ET AUCUN NODE N'EST REQUIS. Ce que ce
 * chapitre mesure est la MECANIQUE : l'appariement d'une liste — avec et
 * sans {@code key} — et la semantique des dependances de {@code useEffect}.
 * Les deux sont des algorithmes, et ils se comptent.
 */
public final class Chapitre1React {

    private Chapitre1React() {
    }

    /** La liste affichee : les offres du portail, par ordre d'arrivee. */
    private static final List<Element> AVANT = List.of(
            new Element("OFF-101", "Developpeur Java Spring"),
            new Element("OFF-102", "Ingenieur plateforme Kubernetes"),
            new Element("OFF-103", "Developpeur Java / Kafka"),
            new Element("OFF-104", "SRE astreinte"),
            new Element("OFF-105", "Developpeur front React"),
            new Element("OFF-106", "Architecte cloud"));

    public static void main(String[] args) {
        System.out.println("""
                1. LA MESURE QUI TRANCHE : CE QUE LA `key` EVITE
                """);
        System.out.println("""
                   Une nouvelle offre arrive, et elle s'affiche en TETE de
                   liste — le cas le plus banal d'un portail d'emploi. Les
                   six autres n'ont pas bouge d'un caractere.

                   Voici ce que React fait du DOM dans les deux cas :
                """);

        List<Element> apres = new ArrayList<>();
        apres.add(new Element("OFF-107", "Lead developpeur Java"));
        apres.addAll(AVANT);

        Reconciliation.Rendu parPosition = Reconciliation.parPosition(AVANT, apres);
        Reconciliation.Rendu parCle = Reconciliation.parCle(AVANT, apres);

        System.out.printf("   %-24s %-9s %-9s %-11s %-11s %s%n",
                          "APPARIEMENT", "CREER", "SUPPR.", "DEPLACER",
                          "MAJ", "TOTAL");
        imprimer("par POSITION (sans key)", parPosition);
        imprimer("par CLE (avec key)", parCle);

        System.out.println("""

                   ⚠️ Sans `key`, React compare le rang 0 au rang 0. Or
                   l'insertion a tout decale : chaque ligne differe de celle
                   qui occupait sa place, donc chaque ligne est REECRITE. Six
                   mises a jour pour un ajout.

                   Avec `key`, chaque element est retrouve par son identite.
                   UNE operation au lieu de SEPT : la creation du nouveau, et
                   rien d'autre. Les six offres existantes gardent leur nœud
                   du DOM, parce que leur ordre relatif n'a pas change —
                   c'est l'heuristique du « dernier indice place », celle que
                   React applique vraiment.

                   ⚠️ ET LA `key` NE DOIT PAS ETRE L'INDICE. `key={index}` ne
                   vaut pas mieux que pas de key du tout : l'indice EST la
                   position, donc on retombe exactement sur la premiere
                   ligne du tableau. Il faut une identite STABLE — ici, la
                   reference de l'offre.
                """);

        System.out.println("""
                2. LE BOGUE QUE PERSONNE NE VOIT VENIR : L'ETAT QUI MIGRE
                """);
        System.out.println("""
                   Une ligne de liste n'est pas qu'un texte. Imaginez une
                   case « offre suivie » cochee sur la premiere ligne,
                   OFF-101. L'utilisateur coche, puis une nouvelle offre
                   arrive en tete.
                """);

        System.out.printf("   %-24s %s%n", "APPARIEMENT",
                          "QUELLE OFFRE PORTE LA COCHE, APRES L'AJOUT ?");
        System.out.printf("   %-24s %s%n", "par POSITION (sans key)",
                Reconciliation.quiHeriteDeLEtat(apres, 0, false, "OFF-101")
                + "   ⚠️ ce n'est plus la meme offre");
        System.out.printf("   %-24s %s%n", "par CLE (avec key)",
                Reconciliation.quiHeriteDeLEtat(apres, 0, true, "OFF-101")
                + "   l'etat a suivi son element");

        System.out.println("""

                   ⚠️ L'etat interne d'un composant suit son IDENTITE, et
                   cette identite est la `key`. Sans elle, l'etat suit la
                   POSITION : la coche saute sur l'offre qui a pris la
                   place, et le champ de recherche a demi rempli se retrouve
                   sur une autre ligne.

                   C'est un bogue qu'aucun test d'affichage ne voit — la
                   liste est correcte — et que l'utilisateur signale par
                   « c'est bizarre, ma selection a bouge ».
                """);

        System.out.println("""
                3. `useEffect` : LE TABLEAU DE DEPENDANCES, COMPTE
                """);
        System.out.println("""
                   Quatre rendus du meme composant. Entre le deuxieme et le
                   troisieme, la valeur surveillee change (un filtre de
                   recherche passe de « java » a « devops ») ; les autres
                   rendus ne changent rien.
                """);

        System.out.printf("   %-34s %-9s %-11s %s%n", "FORME",
                          "RENDUS", "EFFETS", "NETTOYAGES");
        Object[] valeurs = {"java", "java", "devops", "devops"};
        for (Composant.Dependances forme : Composant.Dependances.values()) {
            Composant composant = new Composant(forme, List.of());
            for (Object valeur : valeurs) {
                composant.rendre(valeur, c -> { });
            }
            System.out.printf("   %-34s %-9d %-11d %d%n",
                    libelle(forme), composant.rendus(),
                    composant.executionsDEffet(), composant.nettoyages());
        }

        System.out.println("""

                   La premiere ligne est celle qu'on ecrit par erreur : sans
                   tableau, l'effet part a CHAQUE rendu. Un appel d'API
                   dedans, et c'est quatre requetes pour un affichage.

                   La deuxieme est celle de l'exemple du cours : `[]`, donc
                   une seule fois, au montage. C'est ce qu'il faut pour
                   charger une liste une bonne fois.

                   ⚠️ La troisieme est celle qu'on oublie, et c'est souvent
                   la bonne : `[motCle]` recharge QUAND LE FILTRE CHANGE. Un
                   `[]` sur un composant filtrable affiche la premiere
                   recherche pour toujours — le bogue « ca ne se met pas a
                   jour » dans sa forme la plus pure.

                   ⚠️ Et remarquez la colonne NETTOYAGES : avant de
                   reexecuter, React nettoie l'effet precedent. Sans cela,
                   un abonnement pose au rendu N survivrait au rendu N+1, et
                   les requetes partiraient en double, puis en quadruple.
                """);

        System.out.println("""
                4. CE QUE `setState` NE FAIT PAS
                """);
        Composant boucle = new Composant(Composant.Dependances.SURVEILLEES, 0);
        boolean premier = boucle.poserLEtat(List.of("a", "b"));
        boolean second = boucle.poserLEtat(List.of("a", "b"));
        boolean troisieme = boucle.poserLEtat(new ArrayList<>(List.of("a", "b")));

        System.out.printf("      poser [a, b] la 1re fois   : nouveau rendu ? %b%n",
                          premier);
        System.out.printf("      poser [a, b] la 2e fois    : nouveau rendu ? %b%n",
                          second);
        System.out.printf("      poser une AUTRE liste egale : nouveau rendu ? %b%n",
                          troisieme);

        System.out.println("""

                   Reposer la MEME valeur ne declenche pas de rendu — c'est
                   ce qui empeche la boucle « je charge dans un effet, je
                   pose l'etat, l'effet repart ».

                   ⚠️ Mais « meme valeur » se juge par egalite, et React,
                   lui, compare par REFERENCE (`Object.is`). Un
                   `setOffres([...offres])` cree un nouveau tableau, donc
                   une nouvelle reference, donc un rendu — meme si le
                   contenu est identique. C'est la cause n°1 des boucles de
                   rendu infinies, et elle ne se voit qu'au profileur.

                   La regle qui tient : les donnees descendent par les
                   props, les evenements remontent par des fonctions de
                   rappel — et l'etat vit au plus pres de qui l'utilise.
                """);
    }

    private static void imprimer(String nom, Reconciliation.Rendu rendu) {
        System.out.printf("   %-24s %-9d %-9d %-11d %-11s %d%n", nom,
                rendu.compte(Operation.CREER),
                rendu.compte(Operation.SUPPRIMER),
                rendu.compte(Operation.DEPLACER),
                rendu.compte(Operation.METTRE_A_JOUR)
                        + (rendu.compte(Operation.METTRE_A_JOUR) > 0 ? " ⚠️" : ""),
                rendu.total());
    }

    private static String libelle(Composant.Dependances forme) {
        return switch (forme) {
            case AUCUNE -> "useEffect(fn)          (aucun)";
            case VIDES -> "useEffect(fn, [])      (montage)";
            case SURVEILLEES -> "useEffect(fn, [motCle])";
        };
    }
}
