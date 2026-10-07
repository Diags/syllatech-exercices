package fr.portail.securite;

import fr.portail.comptes.ServiceDUtilisateurs;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.annotation.Order;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.ProviderManager;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.JwtDecoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

/**
 * La politique de sécurité du portail — <strong>deux</strong> chaînes.
 *
 * <p>C'est le point que le chapitre 1 mesure : une application a rarement une
 * seule chaîne de filtres. Ici il y en a deux, et {@code @Order} décide
 * laquelle examine une requête donnée. La première dont le
 * {@code securityMatcher} correspond gagne, et <strong>les suivantes ne sont
 * pas consultées</strong> — y compris quand la première refuse.
 *
 * <ul>
 *   <li>{@link #chaineDeSession} couvre {@code /session/**} : une session par
 *       cookie, avec CSRF actif. C'est le monde du formulaire de connexion ;</li>
 *   <li>{@link #chaineApi} couvre tout le reste : un resource server JWT,
 *       sans session, sans CSRF.</li>
 * </ul>
 *
 * <p>Les deux cohabitent dans la même application, et le chapitre 3 s'en sert
 * pour montrer que « désactiver CSRF » n'est pas une opinion : cela dépend de
 * la façon dont la requête porte son identité.
 */
@Configuration
@EnableMethodSecurity
public class SecurityConfig {

    /** L'origine de la SPA du portail. La seule autorisée. */
    public static final String ORIGINE_AUTORISEE = "https://app.portail.test";

    /**
     * La chaîne « session + cookie », pour {@code /session/**}.
     *
     * <p>CSRF y est <strong>actif</strong>, et c'est le bon choix : une
     * requête authentifiée par un cookie part toute seule, même déclenchée
     * depuis un autre site.
     */
    @Bean
    @Order(1)
    SecurityFilterChain chaineDeSession(HttpSecurity http) throws Exception {
        return http
                .securityMatcher("/session/**")
                .authorizeHttpRequests(regles -> regles
                        .requestMatchers("/session/connexion").permitAll()
                        .anyRequest().authenticated())
                .httpBasic(org.springframework.security.config.Customizer.withDefaults())
                .sessionManagement(s -> s
                        .sessionCreationPolicy(SessionCreationPolicy.IF_REQUIRED))
                // ⚠️ Sans cette ligne, le contexte de securite n'est PAS
                // range dans la session : depuis Spring Security 6, `httpBasic`
                // ne le persiste plus par defaut. Le cookie JSESSIONID sortait
                // bien, mais ne suffisait pas a etre authentifie — et la
                // demonstration CSRF du chapitre 3 mesurait deux 401 au lieu
                // d'un 403 et d'un 200.
                .securityContext(contexte -> contexte.securityContextRepository(
                        new org.springframework.security.web.context
                                .HttpSessionSecurityContextRepository()))
                // CSRF actif. Le jeton est lisible par le JavaScript de la
                // page — c'est la forme « cookie-to-header », celle qu'une
                // SPA sait utiliser.
                //
                // ⚠️ LE `CsrfTokenRequestAttributeHandler` N'EST PAS UN DETAIL.
                // Depuis Spring Security 6, le gestionnaire par defaut est
                // `XorCsrfTokenRequestAttributeHandler` : il masque le jeton a
                // chaque reponse pour gener l'attaque BREACH, et attend donc
                // dans l'en-tete une valeur MASQUEE, pas celle du cookie. Une
                // SPA qui lit `XSRF-TOKEN` et le renvoie tel quel se fait
                // refuser, avec un 403 que rien n'explique. Le gestionnaire
                // simple retablit la forme « cookie-to-header » attendue.
                .csrf(csrf -> csrf
                        .csrfTokenRepository(org.springframework.security.web.csrf
                                .CookieCsrfTokenRepository.withHttpOnlyFalse())
                        .csrfTokenRequestHandler(
                                new org.springframework.security.web.csrf
                                        .CsrfTokenRequestAttributeHandler()))
                // ⚠️ ET UN GESTIONNAIRE DE REFUS EXPLICITE. Celui par defaut
                // appelle `sendError`, ce qui declenche une SECONDE passe vers
                // `/error` — laquelle retraverse les chaines de filtres,
                // tombe dans celle de l'API, et repond 401 « Bearer ». Le
                // chapitre 3 mesurait donc trois 401 la ou il attendait un
                // 403 et un 200. Ecrire la reponse soi-meme evite la passe.
                .exceptionHandling(erreurs -> erreurs.accessDeniedHandler(
                        (requete, reponse, refus) -> {
                            reponse.setStatus(403);
                            reponse.setContentType("application/json");
                            reponse.getWriter().write(
                                    "{\"erreur\":\"jeton CSRF absent ou invalide\"}");
                        }))
                .build();
    }

    /**
     * La chaîne de l'API : JWT, sans état, sans CSRF.
     */
    @Bean
    @Order(2)
    SecurityFilterChain chaineApi(HttpSecurity http, JwtDecoder decodeur,
                                  ConvertisseurDeRoles convertisseur)
            throws Exception {
        return http
                // >>> depart: ouvrir /api/public/**, /oauth2/** et /.well-known/**, reserver /api/rh/** au role RH, fermer le reste
                //     .authorizeHttpRequests(regles -> regles
                //             .anyRequest().permitAll())
                .authorizeHttpRequests(regles -> regles
                        .requestMatchers("/api/public/**").permitAll()
                        .requestMatchers("/oauth2/**", "/.well-known/**").permitAll()
                        .requestMatchers("/api/rh/**").hasRole("RH")
                        .anyRequest().authenticated())
                // <<<
                .oauth2ResourceServer(oauth -> oauth
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(convertisseur)))
                // Sans session : le contexte de securite est reconstruit a
                // chaque requete depuis le jeton, puis jete. Le chapitre 1
                // mesure qu'aucun cookie JSESSIONID ne sort d'ici.
                .sessionManagement(s -> s
                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                // Pas de CSRF : un en-tete `Authorization` ne part jamais
                // tout seul. Le chapitre 3 le demontre plutot que de
                // l'affirmer.
                .csrf(csrf -> csrf.disable())
                .cors(org.springframework.security.config.Customizer.withDefaults())
                .build();
    }

    /**
     * La politique CORS : des origines nommées, jamais {@code *}.
     *
     * <p>⚠️ <strong>Le nom de cette méthode compte.</strong> {@code cors()}
     * cherche un bean nommé {@code corsConfigurationSource}. Nommée
     * autrement, la configuration est simplement ignorée : aucune erreur,
     * aucun avertissement, et pas un seul en-tête CORS dans les réponses.
     * C'est ce qui est arrivé en écrivant ce chapitre, et c'est la panne la
     * plus déroutante de CORS — la configuration est là, elle est juste, et
     * personne ne la lit.
     *
     * <p>⚠️ {@code *} et {@code allowCredentials(true)} sont incompatibles, et
     * Spring lève une exception à la construction plutôt que de servir une
     * configuration dangereuse. Le chapitre 3 déclenche cette exception pour
     * montrer que le garde-fou existe.
     */
    @Bean
    CorsConfigurationSource corsConfigurationSource() {
        var config = new CorsConfiguration();
        // >>> depart: nommer l'origine autorisee, les methodes, les en-tetes, et une duree de cache d'une heure
        //     config.setAllowedOrigins(List.of("*"));
        config.setAllowedOrigins(List.of(ORIGINE_AUTORISEE));
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "DELETE"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        config.setMaxAge(3600L);
        // <<<
        var source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }

    @Bean
    PasswordEncoder encodeur() {
        return new BCryptPasswordEncoder();
    }

    /**
     * Le {@code AuthenticationManager} de Spring, exposé pour être mesuré.
     *
     * <p>Le chapitre 2 chronomètre ses deux chemins — compte inconnu, mot de
     * passe faux — et les compare à ceux de
     * {@link fr.portail.comptes.AuthentificationNaive}. C'est la seule façon
     * de voir ce que {@code mitigateAgainstTimingAttack} achète.
     */
    @Bean
    AuthenticationManager gestionnaireDAuthentification(
            ServiceDUtilisateurs utilisateurs, PasswordEncoder encodeur) {
        var fournisseur = new DaoAuthenticationProvider(utilisateurs);
        fournisseur.setPasswordEncoder(encodeur);
        return new ProviderManager(fournisseur);
    }
}
