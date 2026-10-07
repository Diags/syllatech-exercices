package fr.portail.plateforme;

import java.util.ArrayList;
import java.util.List;

/**
 * Ce qu'une mise à jour progressive fait, étape par étape — calculé.
 *
 * <p>{@code maxSurge} et {@code maxUnavailable} sont deux nombres dans un
 * YAML, et personne ne sait vraiment ce qu'ils impliquent avant de les avoir
 * vus tourner. Cette classe déroule l'arithmétique de Kubernetes et rend la
 * suite des états : combien de pods de l'ancienne version, combien de la
 * nouvelle, et surtout <strong>combien de pods servent réellement du
 * trafic</strong> à chaque instant.
 *
 * <p>⚠️ <strong>C'est une simulation, et elle est nommée comme telle.</strong>
 * Le vrai contrôleur de Kubernetes fait davantage : il attend les sondes de
 * disponibilité, respecte {@code minReadySeconds}, gère les échecs. Ce qui est
 * calculé ici est l'<em>enveloppe</em> — le nombre minimal de pods disponibles
 * et le nombre maximal de pods créés — et c'est précisément ce que les deux
 * réglages garantissent.
 *
 * <p>La leçon est dans la dernière colonne : avec
 * {@code maxUnavailable: 1} sur 4 répliques, il reste toujours au moins 3 pods
 * pour servir. Avec {@code maxUnavailable: 4}, il peut n'en rester
 * <em>aucun</em> — et la « mise à jour sans interruption » devient une
 * interruption.
 */
public final class MiseAJourProgressive {

    /** Un instant de la mise à jour. */
    public record Etape(int numero, int anciens, int nouveaux,
                        int disponibles, String action) {
    }

    private MiseAJourProgressive() {
    }

    /**
     * Déroule la mise à jour.
     *
     * @param repliques      le nombre de pods voulu
     * @param maxSurge       combien de pods EN PLUS on tolère
     * @param maxUnavailable combien de pods EN MOINS on tolère
     */
    public static List<Etape> derouler(int repliques, int maxSurge,
                                       int maxUnavailable) {
        var etapes = new ArrayList<Etape>();
        int anciens = repliques;
        int nouveaux = 0;
        int numero = 0;
        etapes.add(new Etape(numero, anciens, nouveaux, anciens,
                "etat initial"));

        // Les deux invariants de Kubernetes, et il n'y en a pas d'autres :
        //   total   = anciens + nouveaux <= repliques + maxSurge
        //   dispo   = anciens + nouveaux >= repliques - maxUnavailable
        int plafond = repliques + maxSurge;
        int plancher = Math.max(0, repliques - maxUnavailable);

        int garde = 0;
        while ((nouveaux < repliques || anciens > 0) && garde++ < 100) {
            int total = anciens + nouveaux;
            int aCreer = Math.min(repliques - nouveaux,
                    Math.max(0, plafond - total));
            if (aCreer > 0) {
                nouveaux += aCreer;
                etapes.add(new Etape(++numero, anciens, nouveaux,
                        anciens + nouveaux, "+" + aCreer + " nouveau(x)"));
                total = anciens + nouveaux;
            }
            // >>> depart: ne supprimer que ce que maxUnavailable autorise — le plancher de disponibilite
            //     int aSupprimer = anciens;
            int aSupprimer = Math.min(anciens, Math.max(0, total - plancher));
            // <<<
            if (aSupprimer > 0) {
                anciens -= aSupprimer;
                etapes.add(new Etape(++numero, anciens, nouveaux,
                        anciens + nouveaux, "-" + aSupprimer + " ancien(s)"));
            }
            if (aCreer == 0 && aSupprimer == 0) {
                // Ni creation ni suppression possible : la mise a jour est
                // bloquee. C'est le cas maxSurge=0 ET maxUnavailable=0, que
                // Kubernetes refuse a la validation — et on voit ici
                // pourquoi : il n'existe aucune sequence valide.
                etapes.add(new Etape(++numero, anciens, nouveaux,
                        anciens + nouveaux, "BLOQUEE"));
                break;
            }
        }
        return etapes;
    }

    /** Le plus petit nombre de pods disponibles pendant toute l'opération. */
    public static int creuxDeDisponibilite(List<Etape> etapes) {
        return etapes.stream().mapToInt(Etape::disponibles).min().orElse(0);
    }

    /** Le plus grand nombre de pods existant en même temps. */
    public static int picDePods(List<Etape> etapes) {
        return etapes.stream().mapToInt(e -> e.anciens() + e.nouveaux())
                .max().orElse(0);
    }
}
