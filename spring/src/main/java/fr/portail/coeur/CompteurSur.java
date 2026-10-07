package fr.portail.coeur;

import java.util.concurrent.atomic.AtomicLong;
import org.springframework.stereotype.Component;

/**
 * Le même compteur, sans état muable partagé — et donc juste.
 *
 * <p>Deux différences avec {@link CompteurDeVues}, et une seule est
 * technique :
 *
 * <ul>
 *   <li>le compteur est un {@link AtomicLong} : l'incrémentation est
 *       indivisible ;</li>
 *   <li>le nom de l'utilisateur n'est <strong>pas retenu</strong>. Il est
 *       rendu à l'appelant, qui est le seul à savoir de quelle requête il
 *       s'agit. C'est cela, « un singleton sans état » : ce qui appartient à
 *       une requête reste dans sa requête.</li>
 * </ul>
 *
 * <p>La seconde ligne est celle qui compte. Un {@code AtomicLong} corrige un
 * chiffre ; ne rien retenir corrige une fuite de données.
 */
@Component
public class CompteurSur {

    private final AtomicLong vues = new AtomicLong();

    /** Le rang de cette vue, et le nom qu'on vient de recevoir. */
    public Vue enregistrer(String utilisateur) {
        return new Vue(vues.incrementAndGet(), utilisateur);
    }

    public long vues() {
        return vues.get();
    }

    public void remettreAZero() {
        vues.set(0);
    }

    /** Ce que la requête emporte avec elle, et que le bean ne garde pas. */
    public record Vue(long rang, String utilisateur) {
    }
}
