package fr.portail.securite;

import static org.springframework.security.config.Customizer.withDefaults;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.provisioning.InMemoryUserDetailsManager;
import org.springframework.security.web.SecurityFilterChain;

/**
 * La configuration de sécurité — minimale, et comprise ligne à ligne.
 *
 * <p>Trois choses s'y mesurent, et le chapitre 5 les mesure :
 *
 * <ul>
 *   <li>l'ordre réel de la chaîne de filtres, lue dans le
 *       {@code FilterChainProxy} que ce bean produit ;</li>
 *   <li>le <strong>refus par défaut</strong> : une route que personne n'a
 *       listée répond 401, sans qu'on ait rien écrit pour elle ;</li>
 *   <li>qu'un refus arrive <strong>avant</strong> le contrôleur — un
 *       compteur dans le contrôleur ne bouge pas.</li>
 * </ul>
 */
@Configuration
public class SecurityConfig {

    @Bean
    SecurityFilterChain chaine(HttpSecurity http) throws Exception {
        return http
                // L'ORDRE COMPTE. Les regles sont evaluees de haut en bas, et
                // la premiere qui correspond gagne. Mettre `anyRequest` en
                // premier rendrait tout le reste inatteignable — Spring
                // Security 6 leve d'ailleurs une erreur au demarrage dans ce
                // cas, plutot que de laisser passer une configuration morte.
                // TODO : ouvrir /api/public/** et /actuator/health, reserver /api/admin/** au role ADMIN, fermer le reste
                .authorizeHttpRequests(regles -> regles
                        .anyRequest().permitAll())
                .httpBasic(withDefaults())
                // L'API est sans etat et consommee par des clients qui
                // n'ont pas de cookie de session : la protection CSRF, qui
                // protege les formulaires d'un navigateur, n'a rien a
                // proteger ici. On la desactive EXPLICITEMENT, en sachant
                // pourquoi — pas parce qu'un exemple d'internet le faisait.
                .csrf(csrf -> csrf.disable())
                .build();
    }

    /**
     * Deux comptes en mémoire, pour que le chapitre 5 ait de quoi mesurer.
     *
     * <p>En production, ce bean lit une base — mais le reste de la
     * configuration ne change pas d'une ligne, et c'est le but de
     * l'abstraction {@link UserDetailsService}.
     */
    @Bean
    UserDetailsService utilisateurs(PasswordEncoder encodeur) {
        var karim = User.withUsername("karim")
                .password(encodeur.encode("motdepasse"))
                .roles("USER")
                .build();
        var awa = User.withUsername("awa")
                .password(encodeur.encode("motdepasse"))
                .roles("USER", "ADMIN")
                .build();
        return new InMemoryUserDetailsManager(karim, awa);
    }

    /**
     * BCrypt, avec le coût par défaut (10).
     *
     * <p>Le chapitre 5 mesure deux choses : que le même mot de passe donne
     * deux empreintes différentes — le sel est dans l'empreinte — et le temps
     * que coûte une vérification. Ce temps <em>est</em> la protection : il
     * borne le nombre d'essais par seconde d'un attaquant qui aurait volé la
     * table.
     */
    @Bean
    PasswordEncoder encodeurDeMotDePasse() {
        return new BCryptPasswordEncoder();
    }
}
