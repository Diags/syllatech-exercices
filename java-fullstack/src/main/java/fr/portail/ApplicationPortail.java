package fr.portail;

import fr.portail.domaine.Compte;
import fr.portail.domaine.CompteRepository;
import org.springframework.boot.CommandLineRunner;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.security.crypto.password.PasswordEncoder;

/** L'application du portail : un seul artefact, front et back. */
@SpringBootApplication
public class ApplicationPortail {

    public static void main(String[] args) {
        SpringApplication.run(ApplicationPortail.class, args);
    }

    /**
     * Les comptes de demonstration.
     *
     * <p>⚠️ LES EMPREINTES SONT CALCULEES AU DEMARRAGE, jamais ecrites dans
     * une migration. Une empreinte BCrypt dans un fichier versionne est un
     * secret commite : elle se casse hors ligne, et elle est la meme chez
     * tous ceux qui ont clone le depot.
     */
    @Bean
    public CommandLineRunner comptesDeDemonstration(CompteRepository comptes,
                                                    PasswordEncoder encodeur) {
        return args -> {
            if (comptes.count() > 0) {
                return;
            }
            comptes.save(new Compte("awa", encodeur.encode("motdepasse"),
                                    "ROLE_USER,ROLE_RH"));
            comptes.save(new Compte("bilal", encodeur.encode("motdepasse"),
                                    "ROLE_USER"));
        };
    }
}
