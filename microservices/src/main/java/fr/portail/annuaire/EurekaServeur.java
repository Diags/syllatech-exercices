package fr.portail.annuaire;

import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.cloud.netflix.eureka.server.EnableEurekaServer;

/**
 * L'annuaire du portail : un vrai serveur Eureka.
 *
 * <p>Une annotation, et Spring Boot demarre le serveur Netflix complet —
 * celui-la meme qu'on deploie en production. Les chapitres l'interrogent
 * ensuite par son API REST, exactement comme le ferait un service.
 */
@SpringBootApplication
@EnableEurekaServer
public class EurekaServeur {
}
