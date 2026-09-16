package fr.portail.coeur;

import jakarta.annotation.PostConstruct;
import jakarta.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.List;
import org.springframework.stereotype.Component;

/**
 * Ce que Spring fait, et dans quel ordre.
 *
 * <p>Le cours dit : « Spring appelle {@code @PostConstruct} après l'injection
 * et {@code @PreDestroy} avant la destruction ». Ce bean tient le journal de
 * ce qui lui arrive, et le chapitre 1 l'imprime — y compris la ligne qui
 * surprend : au moment du <strong>constructeur</strong>, la dépendance
 * injectée par champ n'existe pas encore.
 */
@Component
public class CycleDeVie {

    /** Statique : le journal doit survivre à la destruction du bean. */
    private static final List<String> JOURNAL = new ArrayList<>();

    private final CompteurSur parConstructeur;

    public CycleDeVie(CompteurSur parConstructeur) {
        this.parConstructeur = parConstructeur;
        noter("constructeur — la dependance du CONSTRUCTEUR est deja la : "
                + (parConstructeur != null));
    }

    @PostConstruct
    void apresInjection() {
        noter("@PostConstruct — l'objet est complet, c'est ici qu'on initialise");
    }

    @PreDestroy
    void avantDestruction() {
        noter("@PreDestroy — derniere chance de liberer une ressource");
    }

    public CompteurSur parConstructeur() {
        return parConstructeur;
    }

    public static List<String> journal() {
        return List.copyOf(JOURNAL);
    }

    public static void vider() {
        JOURNAL.clear();
    }

    private static void noter(String etape) {
        JOURNAL.add(etape);
    }
}
