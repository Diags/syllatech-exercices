package fr.portail.coeur;

import org.springframework.stereotype.Component;

/**
 * Un bean singleton <strong>avec un état</strong> — la faute que le cours
 * nomme sans la montrer.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Spring crée
 * <em>un seul</em> exemplaire de cette classe pour toute l'application, et
 * toutes les requêtes — qui arrivent en parallèle, sur des threads
 * différents — écrivent dans les mêmes champs.
 *
 * <p>Deux défauts distincts, et le second est le pire :
 *
 * <ol>
 *   <li>{@code vues++} n'est pas indivisible : des incrémentations
 *       disparaissent. C'est un chiffre faux, et on s'en aperçoit ;</li>
 *   <li>{@code dernierUtilisateur} est <strong>partagé entre les
 *       requêtes</strong> : la requête de Karim peut lire le nom d'Awa.
 *       C'est une fuite de données entre utilisateurs, et rien ne la
 *       signale.</li>
 * </ol>
 *
 * <p>Le chapitre 1 lance deux cents requêtes concurrentes et compte les deux.
 * {@link CompteurSur} est la version juste, à côté, pour la comparaison.
 */
@Component
public class CompteurDeVues {

    private long vues;

    private String dernierUtilisateur = "personne";

    /** Le geste fautif : lire, ajouter un, écrire — et retenir un nom. */
    public long enregistrer(String utilisateur) {
        this.dernierUtilisateur = utilisateur;
        this.vues++;
        // Un aller-retour vers la base, un appel reseau, un log : n'importe
        // quoi qui laisse le thread partir ici suffit a ce qu'un autre
        // ecrase `dernierUtilisateur` avant qu'on le relise.
        Thread.onSpinWait();
        return this.vues;
    }

    /** Ce que cette requête croit avoir écrit juste avant. */
    public String dernierUtilisateur() {
        return dernierUtilisateur;
    }

    public long vues() {
        return vues;
    }

    public void remettreAZero() {
        vues = 0;
        dernierUtilisateur = "personne";
    }
}
