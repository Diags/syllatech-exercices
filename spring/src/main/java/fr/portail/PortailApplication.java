package fr.portail;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Le portail de l'emploi — une vraie application Spring Boot.
 *
 * <p>Elle démarre, écoute sur un port, sert des routes protégées et parle à
 * une base. Les six chapitres ne la simulent pas : ils la démarrent et lui
 * envoient de vraies requêtes HTTP.
 *
 * <pre>
 * mvn spring-boot:run                    # le portail, sur http://localhost:8080
 * </pre>
 */
@SpringBootApplication
public class PortailApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortailApplication.class, args);
    }
}
