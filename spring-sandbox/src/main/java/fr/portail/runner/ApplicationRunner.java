package fr.portail.runner;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.core.env.Environment;

/**
 * Le service d'execution, demarre pour de vrai par les chapitres et les
 * tests, sur un port libre, et interroge en HTTP.
 *
 * <p>⚠️ La propriete `jobportal.cle-api` est ici a dessein : c'est le secret
 * que le chapitre 1 fait lire par le code d'un candidat. Elle n'a aucune
 * valeur — c'est un leurre — et sa presence est ce qui rend la
 * demonstration verifiable.
 */
@SpringBootApplication
public class ApplicationRunner {

    public static void main(String[] args) {
        SpringApplication.run(ApplicationRunner.class, args);
    }

    /**
     * Le bon service : un processus separe, borne et tuable.
     *
     * <p>Les chapitres qui veulent l'autre — {@link ExecutionDansLaJvm} —
     * le construisent explicitement, pour qu'on ne puisse jamais le
     * configurer par accident.
     *
     * <p>⚠️ LE DELAI EST UNE ENTREE DECLAREE, pas une constante. Il n'est pas
     * negociable dans son PRINCIPE, mais sa valeur depend du travail qu'on
     * accepte : cinq secondes pour un test technique, davantage pour une
     * compilation, et plus encore sur un noeud lent ou froid. La valeur par
     * defaut ne vaut que pour le cas ou personne ne l'a reglee — et c'est la
     * seule raison pour laquelle elle existe.
     */
    @Bean
    public ExecutionCommutable serviceExecution(
            @Value("${jobportal.sandbox.delai-en-secondes:5}") long delai,
            @Value("${jobportal.sandbox.memoire-en-mio:48}") int memoire) {
        return new ExecutionCommutable(new ExecutionEnBacASable(delai, memoire));
    }

    /**
     * Ce qu'un moteur de script recevrait s'il tournait ici : un acces
     * direct a la configuration de l'application.
     */
    @Bean
    public java.util.function.Function<String, String> lecteurDeProprietes(
            Environment environnement) {
        return environnement::getProperty;
    }
}
