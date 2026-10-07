package fr.portail.offre;

import fr.portail.coeur.CompteurDeVues;
import fr.portail.coeur.CompteurSur;
import fr.portail.offre.dto.CreerOffreDto;
import fr.portail.offre.dto.OffreDto;
import jakarta.validation.Valid;
import java.util.List;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.util.UriComponentsBuilder;

/**
 * Les routes publiques du portail.
 *
 * <p>Injection par constructeur, un seul constructeur, champs {@code final} :
 * le contrôleur se teste sans Spring, en passant des doublures au
 * constructeur. C'est la démonstration du chapitre 1, appliquée.
 */
@RestController
@RequestMapping("/api/public/offres")
public class OffreController {

    private final OffreService service;

    private final CompteurDeVues compteurAvecEtat;

    private final CompteurSur compteurSansEtat;

    OffreController(OffreService service, CompteurDeVues compteurAvecEtat,
                    CompteurSur compteurSansEtat) {
        this.service = service;
        this.compteurAvecEtat = compteurAvecEtat;
        this.compteurSansEtat = compteurSansEtat;
    }

    @GetMapping
    List<OffreDto> lister() {
        return service.listerOffres();
    }

    @PostMapping
    ResponseEntity<OffreDto> creer(@Valid @RequestBody CreerOffreDto demande) {
        var creee = service.creer(demande);
        // 201 avec l'adresse de la ressource creee : c'est ce que REST
        // attend, et ce qu'un 200 ne dit pas.
        var adresse = UriComponentsBuilder.fromPath("/api/public/offres/{id}")
                .buildAndExpand(creee.id()).toUri();
        return ResponseEntity.created(adresse).body(creee);
    }

    /**
     * ⚠️ <strong>Route de démonstration : ne jamais écrire cela.</strong>
     *
     * <p>Elle rend l'entité JPA telle quelle. Le chapitre 3 lit le JSON
     * qu'elle produit et y trouve {@code salaireReel} et la
     * {@code noteInterne} de l'entreprise. Elle existe pour que la faute
     * soit visible, et {@code ApiTest} vérifie qu'elle fuit toujours — sans
     * quoi la démonstration serait morte sans qu'on le sache.
     */
    @GetMapping("/entites-brutes")
    @Transactional(readOnly = true)
    List<Offre> listerLesEntitesTellesQuelles() {
        var brutes = service.listerToutesLesEntites();
        // On force le chargement de l'association DANS la transaction, sinon
        // Jackson la lirait dehors et echouerait — ce qui masquerait la
        // vraie lecon en la remplacant par une erreur technique.
        brutes.forEach(o -> {
            if (o.getEntreprise() != null) {
                o.getEntreprise().getNom();
            }
        });
        return brutes;
    }

    /** Les deux compteurs du chapitre 1, exposés pour être bombardés. */
    @GetMapping("/vue")
    Map<String, Object> vue(@RequestParam String utilisateur) {
        long rangAvecEtat = compteurAvecEtat.enregistrer(utilisateur);
        var vue = compteurSansEtat.enregistrer(utilisateur);
        return Map.of(
                "utilisateurDemande", utilisateur,
                "vuParLeSingletonAvecEtat", compteurAvecEtat.dernierUtilisateur(),
                "rangAvecEtat", rangAvecEtat,
                "vuParLeSingletonSansEtat", vue.utilisateur(),
                "rangSansEtat", vue.rang());
    }

    @GetMapping("/compteurs")
    Map<String, Long> compteurs() {
        return Map.of("avecEtat", compteurAvecEtat.vues(),
                "sansEtat", compteurSansEtat.vues());
    }

    @PostMapping("/compteurs/remise-a-zero")
    ResponseEntity<Void> remiseAZero() {
        compteurAvecEtat.remettreAZero();
        compteurSansEtat.remettreAZero();
        return ResponseEntity.status(HttpStatus.NO_CONTENT).build();
    }
}
