package fr.portail.paiement;

import java.time.Instant;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestHeader;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Les deux routes du paiement.
 *
 * <p>⚠️ LE WEBHOOK EST PUBLIC — il doit l'etre, puisque Stripe l'appelle
 * sans jeton. Ce n'est pas une faille tant que sa SIGNATURE est verifiee :
 * c'est elle qui authentifie l'appel, pas un en-tete `Authorization`.
 */
@RestController
@RequestMapping("/api/paiement")
public class PaiementControleur {

    private final ServicePaiement service;

    public PaiementControleur(ServicePaiement service) {
        this.service = service;
    }

    @PostMapping("/session")
    public Map<String, String> session(@RequestBody Map<String, Object> demande) {
        return service.creerUneSession(
                String.valueOf(demande.get("commande")),
                ((Number) demande.getOrDefault("montantEnCentimes", 4900)).intValue());
    }

    /**
     * ⚠️ LE CORPS EST LU BRUT, en `String`, et c'est obligatoire : la
     * signature porte sur les OCTETS exacts envoyes par Stripe. Laisser
     * Spring desserialiser puis reserialiser change les espaces et l'ordre
     * des cles — et la signature ne correspond plus.
     */
    @PostMapping("/webhook")
    public ResponseEntity<String> webhook(
            @RequestBody String corps,
            @RequestHeader(value = "Stripe-Signature", required = false) String enTete) {
        SignatureStripe.Verdict verdict =
                service.traiterLeWebhook(corps, enTete, Instant.now());
        return verdict.valide()
                ? ResponseEntity.ok("recu")
                : ResponseEntity.badRequest().body(verdict.motif());
    }
}
