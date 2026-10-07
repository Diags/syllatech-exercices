package fr.portail.projection;

import fr.portail.domaine.Messages.CandidatureDeposee;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Une seconde projection, alimentée par les mêmes événements.
 *
 * <p>C'est la démonstration la plus directe de CQRS : deux modèles de lecture
 * pour un seul modèle d'écriture. Ajouter un écran n'ajoute pas une colonne à
 * l'agrégat — il ajoute une projection, qu'on rejoue depuis le début du
 * journal.
 *
 * <p>⚠️ <strong>Et celle-ci n'est PAS idempotente, volontairement.</strong>
 * Elle incrémente un compteur à chaque événement reçu. Or un bus en
 * <em>at-least-once</em> peut livrer deux fois le même message : le chapitre 1
 * le fabrique, et le compteur se met à mentir sans qu'aucune erreur ne soit
 * levée. La version corrigée, qui retient les identifiants déjà vus, est juste
 * à côté — {@link #onIdempotent}.
 */
public class CompteurParOffre {

    private final Map<String, AtomicInteger> naif = new LinkedHashMap<>();
    private final Map<String, AtomicInteger> sur = new LinkedHashMap<>();
    private final java.util.Set<String> dejaVus = new java.util.HashSet<>();

    @org.axonframework.eventhandling.EventHandler
    public void on(CandidatureDeposee fait) {
        naif.computeIfAbsent(fait.offre(), o -> new AtomicInteger())
                .incrementAndGet();
        onIdempotent(fait);
    }

    /**
     * La même chose, mais qui supporte d'être rejouée.
     *
     * <p>La recette est toujours la même : retenir ce qu'on a déjà traité.
     * Ici l'identifiant de la candidature suffit ; en production, on garde
     * l'identifiant du message dans une table, dans la même transaction que
     * la mise à jour.
     */
    public void onIdempotent(CandidatureDeposee fait) {
        // >>> depart: ignorer un fait deja traite — c'est toute la recette de l'idempotence
        //     // sans ce garde, une livraison at-least-once fait mentir le compteur
        if (!dejaVus.add(fait.candidatureId())) {
            return;
        }
        // <<<
        sur.computeIfAbsent(fait.offre(), o -> new AtomicInteger())
                .incrementAndGet();
    }

    public int compteNaif(String offre) {
        var compteur = naif.get(offre);
        return compteur == null ? 0 : compteur.get();
    }

    public int compteIdempotent(String offre) {
        var compteur = sur.get(offre);
        return compteur == null ? 0 : compteur.get();
    }

    public void vider() {
        naif.clear();
        sur.clear();
        dejaVus.clear();
    }
}
