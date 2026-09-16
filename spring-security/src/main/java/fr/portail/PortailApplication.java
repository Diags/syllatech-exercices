package fr.portail;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Le portail de l'emploi, vu par la sécurité.
 *
 * <p>Une vraie application Spring Boot : deux chaînes de filtres, un
 * resource server JWT, un émetteur de jetons RS256, et un document de
 * découverte OIDC servi par elle-même. Les six chapitres la démarrent et
 * l'attaquent.
 *
 * <pre>
 * mvn spring-boot:run     # le portail sur http://localhost:8080
 * </pre>
 */
@SpringBootApplication
public class PortailApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortailApplication.class, args);
    }
}
