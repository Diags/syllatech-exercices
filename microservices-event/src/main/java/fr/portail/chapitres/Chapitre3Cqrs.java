package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.Decider;
import fr.portail.domaine.Messages.DeposerCandidature;
import fr.portail.domaine.Messages.PlanifierEntretien;
import fr.portail.projection.VueDesCandidatures;
import java.util.ArrayList;
import java.util.List;

/**
 * Chapitre 3 — CQRS en pratique.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Cqrs
 * </pre>
 *
 * <p>« Une projection se rejoue depuis zéro sans impacter le côté écriture. »
 * Ce chapitre le fait : il <strong>jette</strong> la vue, la reconstruit en
 * relisant le journal, et compare — puis crée une projection qui n'existait
 * pas, et la remplit avec un passé qu'elle n'a pas vécu.
 *
 * <p>Il mesure aussi la fenêtre de cohérence à terme, et dit clairement
 * pourquoi elle est nulle ici.
 */
public final class Chapitre3Cqrs {

    private Chapitre3Cqrs() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            // Un peu de vie sur le portail.
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-awa", "Awa", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-karim", "Karim", "OFF-014"));
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-lea", "Lea", "OFF-021"));
            banc.passerelle().sendAndWait(
                    new PlanifierEntretien("c-awa", "mardi 14h"));
            banc.passerelle().sendAndWait(
                    new Decider("c-awa", true, "excellent profil"));

            Console.titre(1, "UN MODELE D'ECRITURE, DEUX MODELES DE LECTURE");
            Console.sousTitre("La vue des candidatures — une ligne par ecran :");
            var lignes = new ArrayList<List<String>>();
            for (var ligne : banc.vue().toutes()) {
                lignes.add(List.of(ligne.candidatureId(), ligne.candidat(),
                        ligne.offre(), ligne.statut(), ligne.creneau()));
            }
            Console.tableau(List.of("id", "candidat", "offre", "statut",
                    "creneau"), lignes, List.of(10, 10, 10, 12, 12));
            System.out.println();
            Console.sousTitre("Le compteur par offre — la meme source, un "
                    + "autre besoin :");
            Console.ligne("candidatures sur OFF-014",
                    String.valueOf(banc.compteur().compteIdempotent("OFF-014")), 32);
            Console.ligne("candidatures sur OFF-021",
                    String.valueOf(banc.compteur().compteIdempotent("OFF-021")), 32);
            System.out.println();
            Console.texte("Deux projections, un seul journal. Aucune des deux "
                    + "n'a demande la permission a l'agregat, et l'agregat "
                    + "ignore leur existence. Ajouter un troisieme ecran "
                    + "n'ajoute pas une colonne au modele d'ecriture — il "
                    + "ajoute une projection.");
            System.out.println();
            Console.texte("Et regardez la table de gauche : elle est PLATE. "
                    + "Une ligne, un ecran, aucune jointure. C'est exactement "
                    + "ce que le cours appelle « denormalisee expres ».");

            Console.titre(2, "JETER LA VUE, ET LA RECONSTRUIRE");
            int avant = banc.vue().taille();
            int evenementsAvant = banc.vue().evenementsRecus();
            banc.vue().vider();
            int apresLeVidage = banc.vue().taille();
            int rejoues = rejouer(banc, banc.vue());
            Console.tableau(List.of("moment", "lignes dans la vue",
                    "evenements traites"), List.of(
                    List.of("avant", String.valueOf(avant),
                            String.valueOf(evenementsAvant)),
                    List.of("apres le vidage", String.valueOf(apresLeVidage), "0"),
                    List.of("apres le rejeu",
                            String.valueOf(banc.vue().taille()),
                            String.valueOf(rejoues))),
                    List.of(22, 22, 22));
            System.out.println();
            Console.ligne("evenements dans le journal",
                    String.valueOf(rejoues), 32);
            Console.ligne("le modele d'ecriture a-t-il bouge", "non", 36);
            System.out.println();
            Console.texte("La vue a ete detruite et reconstruite a "
                    + "l'identique, uniquement a partir du journal. C'est LA "
                    + "propriete qui rend CQRS confortable : un modele de "
                    + "lecture n'est jamais une donnee de reference, c'est un "
                    + "cache — jetable, reconstructible, et qu'on peut donc "
                    + "changer de forme sans migration.");
            System.out.println();
            Console.texte("⚠️ Le rejeu n'est gratuit qu'en apparence. Ici une "
                    + "poignee d'evenements passe en une milliseconde ; sur "
                    + "dix millions, un rejeu complet se compte en heures et "
                    + "occupe la base pendant ce temps. C'est pourquoi on "
                    + "rejoue une projection a la fois, et de preference sur "
                    + "une copie.");

            Console.titre(3, "UNE PROJECTION QUI N'EXISTAIT PAS HIER");
            var nouvelle = new VueDesCandidatures();
            int pourLaNouvelle = rejouer(banc, nouvelle);
            Console.ligne("evenements rejoues",
                    String.valueOf(pourLaNouvelle), 30);
            Console.ligne("lignes obtenues",
                    String.valueOf(nouvelle.taille()), 30);
            Console.ligne("etat de c-awa", statut(nouvelle, "c-awa"), 30);
            System.out.println();
            Console.texte("Cette projection vient d'etre creee. Elle n'a "
                    + "assiste a aucun des evenements du portail, et elle "
                    + "connait pourtant l'histoire complete de chaque "
                    + "candidature. C'est ce que le cours veut dire par « on "
                    + "la rejoue depuis le debut du flux » — et c'est "
                    + "impossible avec une base classique, ou seul le dernier "
                    + "etat survit.");
            System.out.println();
            Console.texte("C'est aussi la reponse a « et si on avait besoin "
                    + "d'un ecran qu'on n'avait pas prevu ? » : on l'ecrit, "
                    + "on rejoue, et on a l'historique.");

            Console.titre(4, "LA FENETRE DE COHERENCE A TERME");
            banc.passerelle().sendAndWait(
                    new DeposerCandidature("c-omar", "Omar", "OFF-033"));
            Console.ligne("juste apres `sendAndWait`",
                    banc.vue().parId("c-omar") == null
                            ? "la vue ne sait pas encore"
                            : "la vue est deja a jour", 34);
            Console.sousTitre("Les processeurs en place :");
            for (var processeur : banc.processeurs()) {
                Console.texte("→ " + processeur, 5);
            }
            System.out.println();
            Console.texte("⚠️ Ne tirez pas de cette ligne la conclusion que la "
                    + "cohérence a terme n'existe pas. Ce projet configure "
                    + "des processeurs SUBSCRIBING : les projections tournent "
                    + "dans le fil qui publie, a l'interieur de la meme unite "
                    + "de travail. La fenetre est donc nulle — par "
                    + "construction, et pour que ces chapitres soient "
                    + "reproductibles.");
            System.out.println();
            Console.texte("Le defaut d'Axon, et ce que vous aurez en "
                    + "production, est le mode TRACKING : chaque groupe de "
                    + "handlers tourne sur son propre fil, garde un jeton de "
                    + "position, et rejoue tout seul. C'est ce qui permet le "
                    + "rejeu et le parallelisme — et c'est ce qui cree la "
                    + "fenetre. L'ecriture n'attend plus les lecteurs.");
            System.out.println();
            Console.texte("La consequence pratique est entierement cote "
                    + "interface : afficher un etat optimiste, interroger a "
                    + "nouveau, ou utiliser les `subscription queries` "
                    + "d'Axon qui poussent la mise a jour des que la "
                    + "projection est prete. L'important est d'ASSUMER le "
                    + "delai plutot que de le nier.");

            Console.titre(5, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("L'event sourcing lui-meme : le flux d'une "
                    + "candidature, le nombre d'evenements rejoues a chaque "
                    + "chargement, et ce qu'un snapshot change.");
            System.out.println();
        }
    }

    /**
     * Rejoue tout le journal dans une projection — à la main, et exprès.
     *
     * <p>En production, c'est ce que fait un {@code TrackingEventProcessor}
     * quand on remet son jeton à zéro ({@code resetTokens}). Le faire ici à
     * la main rend l'opération visible : on relit la liste, du début, et on
     * appelle les mêmes méthodes annotées {@code @EventHandler}.
     */
    /**
     * Le statut d'une ligne, ou un mot quand la ligne n'existe pas.
     *
     * <p>⚠️ Sur la branche « depart », la projection n'est pas remplie : ce
     * chapitre doit alors AFFICHER le vide, pas planter. Un squelette qui
     * s'arrête sur une {@code NullPointerException} n'enseigne rien.
     */
    private static String statut(VueDesCandidatures vue, String id) {
        var ligne = vue.parId(id);
        return ligne == null ? "(aucune ligne)" : ligne.statut();
    }

    private static int rejouer(Banc banc, VueDesCandidatures vue) {
        int compte = 0;
        var evenements = new ArrayList<Object>();
        banc.moteur().readEvents(null, false)
                .forEach(message -> evenements.add(message.getPayload()));
        for (var fait : evenements) {
            compte++;
            switch (fait) {
                case CandidatureDeposee depot -> vue.on(depot);
                case fr.portail.domaine.Messages.EntretienPlanifie planifie ->
                        vue.on(planifie);
                case fr.portail.domaine.Messages.DecisionPrononcee decision ->
                        vue.on(decision);
                case fr.portail.domaine.Messages.CandidatureAnnulee annulation ->
                        vue.on(annulation);
                default -> { }
            }
        }
        return compte;
    }
}
