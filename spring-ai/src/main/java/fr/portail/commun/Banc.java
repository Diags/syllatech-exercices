package fr.portail.commun;

import fr.portail.PortailApplication;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * Le banc d'essai : l'application, démarrée sans serveur web.
 *
 * <p>Contrairement aux projets Spring et Spring Security, ce projet n'a rien
 * à mesurer côté HTTP : tout se joue entre {@code ChatClient} et le modèle.
 * Démarrer Tomcat coûterait deux secondes par chapitre et ne montrerait rien
 * de plus.
 */
public final class Banc implements AutoCloseable {

    private static final String[] SILENCE = {
        "logging.level.root=WARN",
        "logging.level.org.springframework.boot.diagnostics=OFF",
    };

    private final ConfigurableApplicationContext contexte;

    private Banc(ConfigurableApplicationContext contexte) {
        this.contexte = contexte;
    }

    public static Banc demarrer(String... proprietes) {
        var construction = new SpringApplicationBuilder(PortailApplication.class)
                .web(WebApplicationType.NONE)
                .properties(SILENCE)
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false);
        var arguments = new java.util.ArrayList<String>();
        for (var propriete : proprietes) {
            arguments.add("--" + propriete);
        }
        return new Banc(construction.run(arguments.toArray(String[]::new)));
    }

    public ConfigurableApplicationContext contexte() {
        return contexte;
    }

    public <T> T bean(Class<T> type) {
        return contexte.getBean(type);
    }

    @Override
    public void close() {
        contexte.close();
    }
}
