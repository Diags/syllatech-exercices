package fr.portail.commun;

import fr.portail.observabilite.Mesures;
import fr.portail.runner.ApplicationRunner;
import fr.portail.runner.ExecutionCommutable;
import fr.portail.runner.ExecutionDansLaJvm;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.ServiceExecution;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import java.util.Map;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;

/**
 * Le banc d'essai : un VRAI runner Spring Boot, sur un port libre.
 *
 * <p>Les chapitres et les tests demarrent ici un service complet et
 * l'interrogent en HTTP. Rien n'est simule : c'est un `@SpringBootApplication`
 * qui ecoute, un `RestClient` qui appelle, et un `record` qui revient.
 *
 * <p>⚠️ LE PORT EST CHOISI PAR LE SYSTEME (`server.port=0`). Un port fixe
 * ferait echouer les executions paralleles et, pire, ferait passer un test
 * en se connectant a un service laisse ouvert par la fois precedente.
 */
public final class Banc implements AutoCloseable {

    private final ConfigurableApplicationContext contexte;
    private final int port;
    private final Mesures mesures;

    private Banc(ConfigurableApplicationContext contexte, Mesures mesures) {
        this.contexte = contexte;
        this.mesures = mesures;
        this.port = Integer.parseInt(
                contexte.getEnvironment().getProperty("local.server.port", "0"));
    }

    /** Le runner du cours : execution dans un processus separe. */
    public static Banc durci() {
        return demarrer(new ExecutionEnBacASable());
    }

    /** Le meme, avec un delai court — pour mesurer le tueur sans attendre. */
    public static Banc durci(long delaiEnSecondes, int memoireEnMio) {
        return demarrer(new ExecutionEnBacASable(delaiEnSecondes, memoireEnMio));
    }

    /**
     * ⚠️ Le runner de la HONTE : execution dans la JVM de l'application.
     *
     * <p>Il n'existe que pour etre mesure. Aucun test ne doit le rendre
     * « sur » : sa raison d'etre est de montrer ce qu'il laisse passer.
     */
    public static Banc dansLaJvm() {
        ConfigurableApplicationContext contexte = construire();
        Environment environnement = contexte.getEnvironment();
        return remplacer(contexte,
                         new ExecutionDansLaJvm(environnement::getProperty));
    }

    private static Banc demarrer(ServiceExecution execution) {
        return remplacer(construire(), execution);
    }

    private static ConfigurableApplicationContext construire() {
        return new SpringApplicationBuilder(ApplicationRunner.class)
                .properties(Map.of("server.port", "0",
                                   "spring.main.banner-mode", "off",
                                   "logging.level.root", "WARN"))
                .run();
    }

    private static Banc remplacer(ConfigurableApplicationContext contexte,
                                  ServiceExecution execution) {
        // Le runner expose UN contrat HTTP ; l'implantation se commute
        // derriere. Les chapitres comparent ainsi les deux sans changer
        // d'application ni de port.
        contexte.getBean(ExecutionCommutable.class).commuter(execution);
        return new Banc(contexte, new Mesures(new SimpleMeterRegistry()));
    }

    public String url() {
        return "http://localhost:" + port;
    }

    public int port() {
        return port;
    }

    public Mesures mesures() {
        return mesures;
    }

    public String propriete(String nom) {
        return contexte.getEnvironment().getProperty(nom);
    }

    @Override
    public void close() {
        contexte.close();
    }

}
