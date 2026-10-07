package fr.portail.domaine;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.Map;
import org.hibernate.cfg.AvailableSettings;
import org.hibernate.resource.jdbc.spi.StatementInspector;
import org.springframework.boot.hibernate.autoconfigure.HibernatePropertiesCustomizer;
import org.springframework.stereotype.Component;

/**
 * L'instrument du chapitre 3 : il COMPTE le SQL reellement emis.
 *
 * <p>C'est un {@code StatementInspector} d'Hibernate — un point
 * d'interception officiel, appele pour chaque requete avant son envoi. Sans
 * lui, le N+1 est une histoire qu'on raconte ; avec lui, c'est un nombre.
 *
 * <p>⚠️ En developpement, {@code spring.jpa.show-sql=true} fait le meme
 * travail dans les journaux. Ce compteur existe pour qu'un TEST puisse
 * echouer quand une requete de trop reapparait — ce qu'un journal ne fait
 * jamais.
 */
@Component
public class CompteurDeRequetes
        implements StatementInspector, HibernatePropertiesCustomizer {

    /**
     * ⚠️ L'INSCRIPTION PASSE PAR UN CUSTOMIZER, ET C'EST OBLIGATOIRE.
     *
     * <p>Ecrire
     * {@code spring.jpa.properties.hibernate.session_factory.statement_inspector}
     * avec le NOM de la classe fonctionne — mais Hibernate instancie alors
     * son PROPRE objet, et le bean Spring ne voit jamais passer une seule
     * requete. Le compteur reste a zero, sans la moindre erreur.
     *
     * <p>Pour que l'instrument soit le bean, il faut lui passer l'INSTANCE.
     */
    @Override
    public void customize(Map<String, Object> proprietes) {
        proprietes.put(AvailableSettings.STATEMENT_INSPECTOR, this);
    }

    private final List<String> requetes = new CopyOnWriteArrayList<>();
    private volatile boolean actif;

    @Override
    public String inspect(String sql) {
        if (actif && sql != null) {
            requetes.add(sql);
        }
        return sql;   // on n'altere rien : on observe
    }

    /** Ouvre une mesure, et repart de zero. */
    public void demarrer() {
        requetes.clear();
        actif = true;
    }

    public void arreter() {
        actif = false;
    }

    public int nombre() {
        return requetes.size();
    }

    /** Les requetes SELECT, dans l'ordre — celles qui font le N+1. */
    public List<String> selects() {
        List<String> selects = new ArrayList<>();
        for (String requete : requetes) {
            if (requete.trim().toLowerCase().startsWith("select")) {
                selects.add(requete);
            }
        }
        return List.copyOf(selects);
    }

    public List<String> toutes() {
        return List.copyOf(requetes);
    }
}
