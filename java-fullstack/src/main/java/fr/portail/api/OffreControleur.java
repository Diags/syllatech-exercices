package fr.portail.api;

import jakarta.validation.Valid;
import java.net.URI;
import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Le controleur MINCE : il traduit du HTTP, et rien d'autre.
 *
 * <p>Pas un `if` metier, pas une ligne de SQL, pas de transaction. Il lit la
 * requete, delegue, et choisit un code de statut. C'est cette maigreur qui
 * rend le service testable sans serveur.
 *
 * <p>⚠️ REGARDEZ LES CODES DE STATUT : ils font partie du contrat autant que
 * le JSON. `201 Created` avec un en-tete `Location`, `204 No Content` sur
 * une suppression, `404` sur un identifiant inconnu. Rendre `200` partout
 * oblige le front a lire le corps pour savoir ce qui s'est passe.
 */
@RestController
@RequestMapping("/api/offres")
public class OffreControleur {

    private final OffreService service;

    /** Un seul constructeur : Spring injecte sans `@Autowired`. */
    public OffreControleur(OffreService service) {
        this.service = service;
    }

    @GetMapping
    public List<OffreDto> lister(@RequestParam(required = false) String motCle) {
        return service.rechercher(motCle);
    }

    @GetMapping("/{id}")
    public OffreDto parIdentifiant(@PathVariable long id) {
        return service.parIdentifiant(id);
    }

    @PostMapping
    public ResponseEntity<OffreDto> creer(@RequestBody @Valid CreationOffre demande) {
        OffreDto creee = service.creer(demande);
        return ResponseEntity
                .created(URI.create("/api/offres/" + creee.id()))
                .body(creee);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> supprimer(@PathVariable long id) {
        service.supprimer(id);
        return ResponseEntity.noContent().build();
    }
}
