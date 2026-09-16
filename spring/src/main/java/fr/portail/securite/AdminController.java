package fr.portail.securite;

import fr.portail.offre.OffreService;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Les routes réservées, et le compteur qui prouve qu'on n'y entre pas.
 *
 * <p>Le cours dit : « Si un filtre refuse, la requête n'atteint jamais votre
 * code métier ». C'est une affirmation sur ce qui s'exécute, donc elle se
 * compte. {@link #entrees} est incrémenté à chaque passage réel dans une
 * méthode de ce contrôleur ; le chapitre 5 envoie une requête refusée, puis
 * regarde le compteur.
 */
@RestController
@RequestMapping("/api/admin")
public class AdminController {

    private static final AtomicInteger ENTREES = new AtomicInteger();

    private final OffreService service;

    AdminController(OffreService service) {
        this.service = service;
    }

    public static int entrees() {
        return ENTREES.get();
    }

    public static void remettreAZero() {
        ENTREES.set(0);
    }

    @GetMapping("/tableau-de-bord")
    Map<String, Object> tableauDeBord() {
        ENTREES.incrementAndGet();
        return Map.of("offres", service.combien(), "acces", "ADMIN");
    }

    /**
     * Une route que la configuration ne mentionne <strong>pas</strong>.
     *
     * <p>Elle n'est ni dans {@code /api/public/**}, ni dans
     * {@code /api/admin/**}… si : elle l'est, par son préfixe. Voir
     * {@link fr.portail.securite.RouteOubliee} pour celle qui ne l'est
     * vraiment pas.
     */
    @GetMapping("/statistiques")
    Map<String, Object> statistiques() {
        ENTREES.incrementAndGet();
        return Map.of("offres", service.combien());
    }
}
