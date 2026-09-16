package fr.portail.projection;

import fr.portail.domaine.Messages.CandidatureAnnulee;
import fr.portail.domaine.Messages.CandidatureDeposee;
import fr.portail.domaine.Messages.DecisionPrononcee;
import fr.portail.domaine.Messages.EntretienPlanifie;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Le modèle de lecture : une ligne par candidature, aucune jointure.
 *
 * <p>C'est la projection du chapitre 3. En production ce serait une table SQL
 * dénormalisée ; ici c'est une {@code Map}, et cela ne change rien à la
 * démonstration : ce qui compte est qu'elle <strong>dérive</strong> des
 * événements, qu'on peut la jeter, et la reconstruire en rejouant le journal.
 *
 * <p>⚠️ <strong>Elle est toujours en retard.</strong> Entre l'événement et sa
 * prise en compte ici, il s'écoule un délai — nul en mémoire, réel dès qu'un
 * bus sépare les deux. C'est pourquoi une projection ne garantit
 * <em>jamais</em> un invariant : deux lecteurs peuvent y voir le même « il
 * reste un créneau » au même instant. Les invariants vivent dans l'agrégat.
 *
 * <p>Elle compte aussi les événements reçus — c'est ce qui permet au chapitre
 * 3 de mesurer un rejeu, et au chapitre 1 de mesurer ce que coûte une
 * livraison <em>at-least-once</em>.
 */
public class VueDesCandidatures {

    /** Une ligne du modèle de lecture : plate, prête pour un écran. */
    public record Ligne(String candidatureId, String candidat, String offre,
                        String statut, String creneau) {
    }

    private final Map<String, Ligne> lignes = new LinkedHashMap<>();
    private final AtomicInteger recus = new AtomicInteger();

    public int evenementsRecus() {
        return recus.get();
    }

    public List<Ligne> toutes() {
        return List.copyOf(lignes.values());
    }

    public Ligne parId(String candidatureId) {
        return lignes.get(candidatureId);
    }

    public int taille() {
        return lignes.size();
    }

    public void vider() {
        lignes.clear();
        recus.set(0);
    }

    // ── les faits, appliques a la vue ────────────────────────────────────

    @org.axonframework.eventhandling.EventHandler
    public void on(CandidatureDeposee fait) {
        recus.incrementAndGet();
        // TODO : creer la ligne du modele de lecture — plate, prete pour un ecran, statut DEPOSEE
        // une projection vide ne leve aucune erreur : elle ne montre rien
    }

    @org.axonframework.eventhandling.EventHandler
    public void on(EntretienPlanifie fait) {
        recus.incrementAndGet();
        majuscule(fait.candidatureId(), "ENTRETIEN", fait.creneau());
    }

    @org.axonframework.eventhandling.EventHandler
    public void on(DecisionPrononcee fait) {
        recus.incrementAndGet();
        majuscule(fait.candidatureId(),
                fait.retenu() ? "RETENUE" : "REFUSEE", null);
    }

    @org.axonframework.eventhandling.EventHandler
    public void on(CandidatureAnnulee fait) {
        recus.incrementAndGet();
        majuscule(fait.candidatureId(), "ANNULEE", null);
    }

    private void majuscule(String id, String statut, String creneau) {
        var ligne = lignes.get(id);
        if (ligne == null) {
            return;
        }
        lignes.put(id, new Ligne(ligne.candidatureId(), ligne.candidat(),
                ligne.offre(), statut,
                creneau == null ? ligne.creneau() : creneau));
    }
}
