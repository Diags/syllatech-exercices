package fr.portail.securite;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Instant;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Le filtre qui valide le jeton — devant les controleurs, une fois par
 * requete.
 *
 * <p>⚠️ AUCUN CONTROLEUR N'A A S'EN SOUCIER. C'est tout l'interet : quand le
 * controleur s'execute, l'identite est deja dans le {@code SecurityContext},
 * ou la requete a deja ete refusee. Un `if (token == null)` dans un
 * controleur est le signe que ce filtre manque.
 *
 * <p>⚠️ ET IL NE REFUSE RIEN LUI-MEME. Un jeton absent ou invalide laisse
 * simplement le contexte vide ; c'est la chaine de filtres, plus loin, qui
 * decide si la route exige une identite. Melanger les deux roles fait des
 * routes publiques qui exigent un jeton sans que personne comprenne
 * pourquoi.
 */
@Component
public class FiltreJwt extends OncePerRequestFilter {

    private static final String PREFIXE = "Bearer ";

    private final ServiceAuthentification authentification;
    private final AtomicInteger requetesVues = new AtomicInteger();
    private final AtomicInteger jetonsAcceptes = new AtomicInteger();
    private final AtomicInteger jetonsRefuses = new AtomicInteger();

    public FiltreJwt(ServiceAuthentification authentification) {
        this.authentification = authentification;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest requete,
                                    HttpServletResponse reponse,
                                    FilterChain suite)
            throws ServletException, IOException {
        requetesVues.incrementAndGet();
        String entete = requete.getHeader("Authorization");
        if (entete != null && entete.startsWith(PREFIXE)) {
            String presente = entete.substring(PREFIXE.length());
            Jeton.Verdict verdict = authentification.jeton()
                    .verifier(presente, "access", Instant.now());
            if (verdict.valide()) {
                jetonsAcceptes.incrementAndGet();
                var autorites = verdict.roles().stream()
                        .map(SimpleGrantedAuthority::new).toList();

                // On cree un contexte plutot que de muter celui qui existe :
                // c'est la forme recommandee depuis Spring Security 6.
                SecurityContext contexte =
                        SecurityContextHolder.createEmptyContext();
                contexte.setAuthentication(new UsernamePasswordAuthenticationToken(
                        verdict.sujet(), null, autorites));
                SecurityContextHolder.setContext(contexte);
            } else {
                jetonsRefuses.incrementAndGet();
            }
        }
        suite.doFilter(requete, reponse);
    }

    // -- l'instrument du chapitre 4 ---------------------------------------

    public int requetesVues() {
        return requetesVues.get();
    }

    public int jetonsAcceptes() {
        return jetonsAcceptes.get();
    }

    public int jetonsRefuses() {
        return jetonsRefuses.get();
    }

    public void reinitialiser() {
        requetesVues.set(0);
        jetonsAcceptes.set(0);
        jetonsRefuses.set(0);
    }
}
