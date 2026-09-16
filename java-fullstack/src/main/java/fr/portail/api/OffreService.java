package fr.portail.api;

import fr.portail.domaine.Entreprise;
import fr.portail.domaine.EntrepriseRepository;
import fr.portail.domaine.Offre;
import fr.portail.domaine.OffreRepository;
import java.util.List;
import java.util.NoSuchElementException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * La couche METIER : la logique, et la transaction.
 *
 * <p>⚠️ C'EST ICI QUE VIT `@Transactional`, pas dans le controleur. Une
 * transaction delimite une operation METIER — « creer une offre » — et pas
 * une requete HTTP. Les poser au-dessus reviendrait a ouvrir une
 * transaction pour servir une page d'erreur.
 *
 * <p>⚠️ Et c'est ici que la conversion entite → DTO a lieu, DANS la
 * transaction. La faire dans le controleur, avec `open-in-view=false`,
 * leverait une `LazyInitializationException` — ce qui est une bonne
 * nouvelle : l'erreur dit que la frontiere a ete franchie au mauvais
 * endroit.
 */
@Service
public class OffreService {

    private final OffreRepository offres;
    private final EntrepriseRepository entreprises;

    public OffreService(OffreRepository offres,
                        EntrepriseRepository entreprises) {
        this.offres = offres;
        this.entreprises = entreprises;
    }

    /** Toutes les offres, avec leur entreprise, en UNE requete. */
    @Transactional(readOnly = true)
    public List<OffreDto> lister() {
        return offres.toutesAvecEntreprise().stream().map(OffreDto::de).toList();
    }

    /**
     * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
     *
     * <p>La meme liste, sans `join fetch`. Elle fonctionne parfaitement, et
     * elle emet une requete par offre. Le chapitre 3 les compte, et le test
     * fixe l'ecart.
     */
    @Transactional(readOnly = true)
    public List<OffreDto> listerAvecUnNPlusUn() {
        return offres.findAll().stream().map(OffreDto::de).toList();
    }

    @Transactional(readOnly = true)
    public List<OffreDto> rechercher(String motCle) {
        if (motCle == null || motCle.isBlank()) {
            return lister();
        }
        return offres.findByTitreContainingIgnoreCase(motCle).stream()
                .map(OffreDto::de).toList();
    }

    @Transactional(readOnly = true)
    public OffreDto parIdentifiant(long id) {
        return offres.findById(id).map(OffreDto::de)
                .orElseThrow(() -> new NoSuchElementException(
                        "offre introuvable : " + id));
    }

    @Transactional
    public OffreDto creer(CreationOffre demande) {
        Entreprise entreprise = entreprises.findById(demande.entrepriseId())
                .orElseThrow(() -> new NoSuchElementException(
                        "entreprise introuvable : " + demande.entrepriseId()));
        Offre creee = offres.save(new Offre(demande.titre(), demande.pile(),
                                            demande.salaireEnKiloEuros(),
                                            entreprise));
        return OffreDto.de(creee);
    }

    @Transactional
    public void supprimer(long id) {
        if (!offres.existsById(id)) {
            throw new NoSuchElementException("offre introuvable : " + id);
        }
        offres.deleteById(id);
    }
}
