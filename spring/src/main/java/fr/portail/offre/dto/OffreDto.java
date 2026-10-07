package fr.portail.offre.dto;

import fr.portail.offre.Offre;

/**
 * Ce que l'API promet — et rien d'autre.
 *
 * <p>Quatre champs, choisis. L'entité en a six, plus une association qui en
 * traîne quatre de plus. Le chapitre 3 compare les deux JSON côte à côte :
 * ce n'est pas une question de style, c'est ce qui sépare une API stable
 * d'un schéma de base publié par accident.
 */
public record OffreDto(Long id, String titre, int salaireMin,
                       String entreprise, String ville) {

    /**
     * Construit le DTO depuis l'entité.
     *
     * <p>⚠️ Cette méthode lit {@code offre.getEntreprise()} : appelée hors
     * d'une transaction sur une entité détachée, elle déclenche la
     * {@code LazyInitializationException} du chapitre 4. Le service la
     * convertit donc <em>dans</em> la transaction — l'endroit où l'entité est
     * encore vivante.
     */
    public static OffreDto de(Offre offre) {
        // TODO : construire le DTO a partir de l'entite, en tolerant une entreprise absente
        return new OffreDto(offre.getId(), offre.getTitre(),
                offre.getSalaireMin(), null, null);
    }
}
