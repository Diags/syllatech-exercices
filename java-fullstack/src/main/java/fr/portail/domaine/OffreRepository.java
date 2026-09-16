package fr.portail.domaine;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

/**
 * Le repository : une interface, aucune implantation a ecrire.
 *
 * <p>Spring Data derive la requete du NOM de la methode. C'est du code en
 * moins, et surtout du code TYPE : le compilateur verifie les parametres et
 * le type de retour, ce qu'une chaine SQL ne permet jamais.
 *
 * <p>⚠️ Et le nom est un CONTRAT. Renommer {@code titre} en
 * {@code intitule} dans l'entite fait echouer le demarrage, parce que
 * {@code findByTitre…} ne correspond plus a rien. C'est une bonne nouvelle :
 * l'erreur arrive au demarrage, pas a la premiere requete d'un utilisateur.
 */
public interface OffreRepository extends JpaRepository<Offre, Long> {

    /** Le nom EST la requete : recherche insensible a la casse sur le titre. */
    List<Offre> findByTitreContainingIgnoreCase(String motCle);

    List<Offre> findByPile(String pile);

    /**
     * ⚠️ LA CORRECTION DU N+1, et elle tient en un mot : {@code join fetch}.
     *
     * <p>Sans elle, lister six offres puis lire le nom de leur entreprise
     * emet SEPT requetes — une pour la liste, une par offre. Le chapitre 3
     * les compte. La bonne reponse n'est pas de forcer {@code EAGER}
     * partout : ce serait payer la jointure meme quand personne ne demande
     * l'entreprise. C'est de la demander la ou on en a besoin.
     */
    // >>> depart: charger les offres ET leur entreprise en UNE requete — sans quoi lire le nom de l'entreprise emet une requete par entreprise distincte
    //     @Query("select o from Offre o")
    //     List<Offre> toutesAvecEntreprise();
    @Query("select o from Offre o join fetch o.entreprise")
    List<Offre> toutesAvecEntreprise();
    // <<<
}
