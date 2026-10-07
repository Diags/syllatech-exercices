package fr.portail.securite;

import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

/**
 * La chaine de filtres : sans etat, et refus par defaut.
 *
 * <p>⚠️ `anyRequest().authenticated()` VIENT TOUJOURS EN DERNIER. C'est le
 * refus par defaut : tout ce qui n'a pas ete explicitement ouvert est
 * ferme. Une route ajoutee dans six mois et oubliee ici sera protegee, pas
 * ouverte — et c'est le seul ordre qui pardonne.
 */
@Configuration
public class ConfigurationSecurite {

    @Bean
    public PasswordEncoder passwordEncoder() {
        // ⚠️ BCrypt integre le sel ET le cout dans la chaine stockee : il n'y
        // a pas de colonne « sel » a prevoir, et changer le cout n'invalide
        // pas les empreintes existantes.
        return new BCryptPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain chaine(HttpSecurity http, FiltreJwt filtre)
            throws Exception {
        return http
                // ⚠️ CSRF DESACTIVE, ET C'EST JUSTIFIE : l'API est sans etat
                // et s'authentifie par un en-tete `Authorization`, pas par un
                // cookie. Une attaque CSRF exploite un cookie envoye
                // automatiquement par le navigateur ; un en-tete, lui, doit
                // etre pose par du JavaScript, qui ne traverse pas les
                // origines. Le jour ou l'on passe aux cookies, CSRF redevient
                // obligatoire.
                .csrf(csrf -> csrf.disable())
                .cors(Customizer.withDefaults())
                // Sans etat : aucune session en memoire, donc n'importe
                // quelle instance peut traiter n'importe quelle requete.
                .sessionManagement(session -> session
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // TODO : poser les regles — le refus par defaut EN DERNIER, les routes publiques avant, les roles sur les ecritures, et le reacheminement vers `/error` permis (sinon un 403 ressort en 401)
                .authorizeHttpRequests(regles -> regles.anyRequest().permitAll())
                // ⚠️ SANS CE POINT D'ENTREE, UNE REQUETE SANS JETON REND 403.
                // C'est le defaut de Spring Security, et il est trompeur :
                // 403 veut dire « je sais qui tu es, tu n'as pas le droit »,
                // alors qu'ici personne n'est identifie. Cote React, les deux
                // cas appellent des reactions OPPOSEES — rediriger vers la
                // page de connexion, ou afficher « acces refuse ». Le
                // chapitre 2 mesure les deux.
                .exceptionHandling(erreurs -> erreurs.authenticationEntryPoint(
                        (requete, reponse, refus) -> reponse.sendError(
                                jakarta.servlet.http.HttpServletResponse.SC_UNAUTHORIZED,
                                "authentification requise")))
                .addFilterBefore(filtre, UsernamePasswordAuthenticationFilter.class)
                .build();
    }

    /**
     * ⚠️ LE NOM DE CE BEAN EST IMPOSE : `corsConfigurationSource`. Nomme
     * autrement, il est ignore EN SILENCE — pas une erreur, pas un
     * avertissement, et pas un en-tete CORS dans les reponses.
     *
     * <p>Et les origines viennent de l'ENVIRONNEMENT, pas du code : c'est
     * exactement ce que le chapitre 6 appelle « configuration externalisee ».
     */
    @Bean
    public CorsConfigurationSource corsConfigurationSource() {
        CorsConfiguration configuration = new CorsConfiguration();
        String origines = System.getenv().getOrDefault(
                "PORTAIL_ORIGINES", "http://localhost:5173");
        configuration.setAllowedOrigins(List.of(origines.split(",")));
        configuration.setAllowedMethods(
                List.of("GET", "POST", "PUT", "DELETE", "OPTIONS"));
        configuration.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        UrlBasedCorsConfigurationSource source =
                new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", configuration);
        return source;
    }
}
