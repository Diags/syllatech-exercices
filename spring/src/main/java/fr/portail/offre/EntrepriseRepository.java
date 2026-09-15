package fr.portail.offre;

import java.util.Optional;
import org.springframework.data.jpa.repository.JpaRepository;

public interface EntrepriseRepository extends JpaRepository<Entreprise, Long> {

    Optional<Entreprise> findByNom(String nom);
}
