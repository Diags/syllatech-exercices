package fr.portail.web;

import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Component;

/**
 * Qui est l'auteur de quelle offre.
 *
 * <p>Ce bean est appelé <strong>depuis une annotation</strong> :
 * {@code @PreAuthorize("@proprietaire.estLAuteur(#reference, authentication.name)")}.
 * Le {@code @} devant le nom désigne un bean du contexte — c'est ce qui
 * permet d'écrire une règle d'autorisation qui interroge la base sans
 * l'écrire dans une chaîne SpEL illisible.
 *
 * <p>{@link #consultations} compte les appels : le chapitre 6 s'en sert pour
 * montrer que la règle est évaluée <strong>avant</strong> la méthode, pas
 * dedans.
 */
@Component("proprietaire")
public class Proprietaire {

    private static final Map<String, String> AUTEURS = Map.of(
            "OFF-014", "awa",
            "OFF-021", "karim");

    private static final AtomicInteger CONSULTATIONS = new AtomicInteger();

    public static int consultations() {
        return CONSULTATIONS.get();
    }

    public static void remettreAZero() {
        CONSULTATIONS.set(0);
    }

    public boolean estLAuteur(String reference, String identifiant) {
        CONSULTATIONS.incrementAndGet();
        return identifiant != null
                && identifiant.equals(AUTEURS.get(reference));
    }

    public static String auteurDe(String reference) {
        return AUTEURS.get(reference);
    }
}
