package fr.portail.securite;

import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * La route que personne n'a pensé à sécuriser.
 *
 * <p>Son chemin — {@code /rapports/salaires} — n'apparaît <strong>nulle
 * part</strong> dans {@link SecurityConfig} : ni dans les règles ouvertes, ni
 * dans les règles réservées. Elle a été ajoutée après coup, comme dans la
 * vraie vie, et elle rend des données que personne ne devrait lire librement.
 *
 * <p>Le chapitre 5 l'appelle sans jeton et mesure la réponse. Avec le refus
 * par défaut ({@code anyRequest().authenticated()}), c'est un 401. Avec la
 * configuration inverse — tout ouvert sauf une liste d'exceptions — c'eût été
 * un 200, et la fuite serait passée inaperçue jusqu'au jour où quelqu'un
 * l'aurait trouvée.
 *
 * <p>C'est pour cela que le refus par défaut n'est pas un détail de style :
 * il fait porter l'oubli du bon côté.
 */
@RestController
public class RouteOubliee {

    private static final AtomicInteger ENTREES = new AtomicInteger();

    public static int entrees() {
        return ENTREES.get();
    }

    public static void remettreAZero() {
        ENTREES.set(0);
    }

    @GetMapping("/rapports/salaires")
    Map<String, Object> salaires() {
        ENTREES.incrementAndGet();
        return Map.of(
                "medianeReelle", 47_500,
                "margeDeNegociation", 8_000,
                "commentaire", "ne jamais publier");
    }
}
