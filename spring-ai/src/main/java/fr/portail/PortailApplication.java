package fr.portail;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Le portail de l'emploi, augmenté — sans clé d'API.
 *
 * <p>Toutes les classes de Spring AI qu'un projet réel utilise sont là :
 * {@code ChatClient}, les advisors, les convertisseurs de sortie, le
 * {@code VectorStore}, les outils. Seul le {@code ChatModel} est écrit à la
 * main, et c'est ce qui rend le projet exécutable hors ligne — et mesurable.
 */
@SpringBootApplication
public class PortailApplication {

    public static void main(String[] args) {
        SpringApplication.run(PortailApplication.class, args);
    }
}
