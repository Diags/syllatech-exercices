package fr.portail.api;

import fr.portail.domaine.Offre;

/**
 * Le CONTRAT PUBLIC de l'API — et rien d'autre.
 *
 * <p>⚠️ REGARDEZ CE QUI N'Y EST PAS : l'identifiant de l'entreprise, la
 * structure de la jointure, le nom des colonnes. Le front voit un nom
 * d'entreprise et une ville ; il ne sait pas qu'il existe une table
 * `entreprise`, et il n'a pas a le savoir.
 *
 * <p>C'est ce qui permet aux deux cycles de vie de diverger : renommer une
 * colonne est une migration Flyway, pas un deploiement du front.
 */
public record OffreDto(Long id, String titre, String pile,
                       int salaireEnKiloEuros, String entreprise,
                       String ville) {

    public static OffreDto de(Offre offre) {
        // >>> depart: construire le DTO depuis l'entite — le contrat public expose un NOM et une VILLE, jamais l'objet Entreprise ni les noms de colonnes
        //     return new OffreDto(offre.getId(), offre.getTitre(),
        //             offre.getPile(), offre.getSalaireEnKiloEuros(), "", "");
        return new OffreDto(offre.getId(), offre.getTitre(), offre.getPile(),
                            offre.getSalaireEnKiloEuros(),
                            offre.getEntreprise().getNom(),
                            offre.getEntreprise().getVille());
        // <<<
    }
}
