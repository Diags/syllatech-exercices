package fr.portail.coeur;

import org.springframework.beans.factory.config.ConfigurableBeanFactory;
import org.springframework.context.annotation.Scope;
import org.springframework.stereotype.Component;

/**
 * Un bean {@code prototype} : Spring en construit un neuf à chaque demande.
 *
 * <p>Le brouillon d'une offre en cours de rédaction a un état, et cet état
 * appartient à une seule personne. C'est le cas où le singleton est le
 * mauvais choix — et le chapitre 1 le vérifie en demandant deux fois le même
 * bean au conteneur, puis en comparant les deux références.
 *
 * <p>⚠️ Le piège du prototype : injecté dans un singleton, il n'est construit
 * <strong>qu'une fois</strong>, à la construction du singleton. Le scope d'un
 * bean n'a d'effet qu'au moment où on le demande au conteneur. Le chapitre 1
 * le mesure aussi, parce que c'est ce qui rend le prototype décevant pour qui
 * l'attendait ailleurs.
 */
@Component
@Scope(ConfigurableBeanFactory.SCOPE_PROTOTYPE)
public class Brouillon {

    private static long construits;

    private final long numero;

    private String titre = "";

    public Brouillon() {
        this.numero = ++construits;
    }

    public long numero() {
        return numero;
    }

    public String titre() {
        return titre;
    }

    public Brouillon titre(String titre) {
        this.titre = titre;
        return this;
    }

    public static long construits() {
        return construits;
    }
}
