package fr.portail.mesure;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicBoolean;
import org.hibernate.resource.jdbc.spi.StatementInspector;

/**
 * Compte les requêtes SQL qu'Hibernate envoie réellement.
 *
 * <p>C'est la pièce centrale du chapitre 4. Le cours dit : « si vous voyez la
 * même requête revenir en boucle pour chaque ligne, c'est un N+1 ». Lire un
 * journal à l'œil est une façon de s'en convaincre ; compter est une façon de
 * le prouver — et de le <strong>tester</strong>, ce qu'un journal ne permet
 * pas.
 *
 * <p>Hibernate accepte un {@link StatementInspector} : il l'appelle avec
 * chaque instruction SQL, juste avant de l'envoyer. Cette classe les retient.
 * Le réglage se fait dans {@code application.yml} :
 *
 * <pre>
 * spring.jpa.properties.hibernate.session_factory.statement_inspector:
 *   fr.portail.mesure.CompteurDeRequetes
 * </pre>
 *
 * <p>⚠️ Hibernate construit lui-même l'exemplaire qu'il utilisera : ce n'est
 * pas un bean Spring, et on ne peut pas se le faire injecter. D'où l'état
 * <strong>statique</strong> — c'est le seul endroit de ce projet où il est
 * justifié, et le chapitre 4 le dit.
 */
public class CompteurDeRequetes implements StatementInspector {

    private static final List<String> REQUETES = new ArrayList<>();

    private static final AtomicBoolean ACTIF = new AtomicBoolean(false);

    @Override
    public String inspect(String sql) {
        if (ACTIF.get()) {
            synchronized (REQUETES) {
                REQUETES.add(sql);
            }
        }
        return sql;
    }

    /** Vide le journal et commence à compter. */
    public static void commencer() {
        synchronized (REQUETES) {
            REQUETES.clear();
        }
        ACTIF.set(true);
    }

    /** Arrête de compter et rend les instructions vues, dans l'ordre. */
    public static List<String> arreter() {
        ACTIF.set(false);
        synchronized (REQUETES) {
            return List.copyOf(REQUETES);
        }
    }

    /** Le nombre d'instructions vues depuis {@link #commencer()}. */
    public static int combien() {
        synchronized (REQUETES) {
            return REQUETES.size();
        }
    }

    /**
     * Compte les instructions SQL émises pendant l'exécution de ce bloc.
     *
     * <p>Si le bloc échoue, le comptage est arrêté proprement et l'exception
     * repart — elle n'est jamais avalée. Un chapitre qui veut mesurer un bloc
     * <em>censé</em> échouer appelle {@link #commencer()} et
     * {@link #arreter()} lui-même : c'est plus long à écrire, et cela dit ce
     * qu'on attend.
     *
     * @return les instructions, dans l'ordre où Hibernate les a envoyées
     */
    public static List<String> pendant(Runnable bloc) {
        commencer();
        try {
            bloc.run();
        } catch (RuntimeException erreur) {
            arreter();
            throw erreur;
        }
        return arreter();
    }

    /** Combien de ces instructions lisent la table donnée ? */
    public static long selectsSur(List<String> requetes, String table) {
        String cible = " " + table.toLowerCase(java.util.Locale.ROOT) + " ";
        return requetes.stream()
                .map(r -> r.toLowerCase(java.util.Locale.ROOT).replace('\n', ' '))
                .filter(r -> r.startsWith("select"))
                .filter(r -> r.contains(cible))
                .count();
    }

    /** Une forme courte, lisible dans un tableau de console. */
    public static String resumer(String sql) {
        String plat = sql.replaceAll("\\s+", " ").strip();
        return plat.length() <= 78 ? plat : plat.substring(0, 75) + "...";
    }
}
