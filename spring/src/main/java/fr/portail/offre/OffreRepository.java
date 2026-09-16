package fr.portail.offre;

import java.util.List;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;

/**
 * Les deux façons de lire la même chose — et leur coût, mesuré.
 *
 * <p>Le chapitre 4 appelle les deux méthodes et compte les instructions SQL
 * réellement envoyées. Sur dix offres, la première en émet onze et la seconde
 * une. C'est tout le chapitre, et c'est un nombre, pas une opinion.
 */
public interface OffreRepository extends JpaRepository<Offre, Long> {

    /**
     * ❌ Le N+1. Une requête pour la liste, puis une par offre dès qu'on
     * touche à son entreprise.
     *
     * <p>Hérité de {@code JpaRepository} : c'est le {@code findAll()} que
     * tout le monde appelle sans y penser. Il n'est pas fautif en soi — il
     * le devient au moment où le code lit l'association.
     */
    @Override
    List<Offre> findAll();

    /**
     * ✅ Une seule requête, avec la jointure.
     *
     * <p>{@code join fetch} n'est pas une jointure ordinaire : il dit à
     * Hibernate de <strong>remplir</strong> l'association au passage. Une
     * jointure sans {@code fetch} filtrerait sans rien charger, et le N+1
     * reviendrait intact.
     */
    // >>> depart: ecrire la requete JPQL qui charge l'entreprise en une seule instruction
    //     @Query("select o from Offre o order by o.id")
    //     List<Offre> findAllAvecEntreprise();
    @Query("""
            select o from Offre o
            join fetch o.entreprise
            order by o.id
            """)
    List<Offre> findAllAvecEntreprise();
    // <<<

    List<Offre> findByEntrepriseVille(String ville);
}
