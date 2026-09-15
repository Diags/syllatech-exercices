package fr.portail.web;

import fr.portail.comptes.ServiceDUtilisateurs;
import fr.portail.jeton.ServiceDeJetons;
import jakarta.servlet.http.HttpServletRequest;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Les routes du portail, réunies : il y en a peu, et les éparpiller
 * obligerait à ouvrir six fichiers pour lire une politique de sécurité.
 *
 * <p>Chaque route existe pour être mesurée par un chapitre, et le compteur
 * {@link #entrees} dit combien de fois le <em>code métier</em> a réellement
 * été atteint — la seule façon de vérifier « la requête n'atteint jamais
 * votre code ».
 */
@RestController
public class Controleurs {

    private static final AtomicInteger ENTREES = new AtomicInteger();

    /** Là où la chaîne de session range l'identité : dans la session HTTP. */
    private static final org.springframework.security.web.context
            .HttpSessionSecurityContextRepository DEPOT =
            new org.springframework.security.web.context
                    .HttpSessionSecurityContextRepository();

    private final ServiceDeJetons jetons;

    private final ServiceDUtilisateurs utilisateurs;

    private final fr.portail.comptes.AuthentificationNaive naive;

    Controleurs(ServiceDeJetons jetons, ServiceDUtilisateurs utilisateurs,
                fr.portail.comptes.AuthentificationNaive naive) {
        this.jetons = jetons;
        this.utilisateurs = utilisateurs;
        this.naive = naive;
    }

    public static int entrees() {
        return ENTREES.get();
    }

    public static void remettreAZero() {
        ENTREES.set(0);
    }

    // ── ouvert a tous ────────────────────────────────────────────────────

    @GetMapping("/api/public/offres")
    List<Map<String, Object>> offres() {
        ENTREES.incrementAndGet();
        return List.of(
                Map.of("reference", "OFF-014", "intitule", "Developpeuse Java",
                        "ville", "Lyon"),
                Map.of("reference", "OFF-021", "intitule", "Ingenieure SRE",
                        "ville", "Toulouse"));
    }

    /**
     * Échange des identifiants contre une paire de jetons.
     *
     * <p>C'est le rôle que tiendrait un serveur d'autorisation. Le tenir
     * soi-même est exactement ce que les chapitres 5 et 6 déconseillent — il
     * est ici pour que le projet puisse émettre de vrais jetons hors ligne.
     */
    @PostMapping("/api/public/connexion")
    ResponseEntity<Map<String, Object>> connexion(
            @RequestBody Map<String, String> demande) {
        ENTREES.incrementAndGet();
        String identifiant = demande.getOrDefault("identifiant", "");
        String motDePasse = demande.getOrDefault("motDePasse", "");
        if (!naive.verifier(identifiant, motDePasse)) {
            // Le MEME message dans les deux cas : compte inconnu ou mot de
            // passe faux. Le chapitre 2 mesure que le TEMPS, lui, differe.
            return ResponseEntity.status(401)
                    .body(Map.of("erreur", "identifiants invalides"));
        }
        var compte = utilisateurs.compte(identifiant);
        return ResponseEntity.ok(Map.of(
                "access_token", jetons.acces(identifiant, compte.roles()),
                "id_token", jetons.identite(identifiant, compte.courriel(),
                        compte.nom()),
                "refresh_token", jetons.rafraichissement(identifiant),
                "token_type", "Bearer",
                "expires_in", ServiceDeJetons.DUREE_ACCES.toSeconds()));
    }

    @PostMapping("/api/public/rafraichir")
    ResponseEntity<Map<String, Object>> rafraichir(
            @RequestBody Map<String, String> demande) {
        ENTREES.incrementAndGet();
        var porteur = jetons.porteurDu(demande.getOrDefault("refresh_token", ""));
        if (porteur.isEmpty()) {
            return ResponseEntity.status(401)
                    .body(Map.of("erreur", "refresh token inconnu ou revoque"));
        }
        var compte = utilisateurs.compte(porteur.get());
        return ResponseEntity.ok(Map.of(
                "access_token", jetons.acces(porteur.get(), compte.roles()),
                "token_type", "Bearer"));
    }

    /**
     * Une route publique qui tombe en panne.
     *
     * <p>⚠️ Pièce à conviction. Le chapitre 1 mesure ce que le client reçoit :
     * pas un 500.
     */
    @GetMapping("/api/public/panne")
    Map<String, Object> panne() {
        ENTREES.incrementAndGet();
        throw new IllegalStateException("l'annuaire ne repond pas");
    }

    // ── il faut un jeton ─────────────────────────────────────────────────

    /** Qui parle, vu depuis le contrôleur — reconstruit à chaque requête. */
    @GetMapping("/api/moi")
    Map<String, Object> moi(Authentication authentification,
                            HttpServletRequest requete) {
        ENTREES.incrementAndGet();
        var jeton = (Jwt) authentification.getPrincipal();
        return Map.of(
                "sujet", authentification.getName(),
                "autorites", authentification.getAuthorities().stream()
                        .map(Object::toString).sorted().toList(),
                "rolesDuJeton", fr.portail.securite.ConvertisseurDeRoles
                        .rolesDu(jeton),
                "expireLe", String.valueOf(jeton.getExpiresAt()),
                // ⚠️ Une session HTTP a-t-elle ete creee ? `false` veut dire
                // « ne m'en cree pas une pour repondre ». Le chapitre 1
                // mesure que la reponse est toujours « aucune ».
                "sessionHttp", requete.getSession(false) == null
                        ? "aucune" : requete.getSession(false).getId(),
                "memeContexteHorsRequete", String.valueOf(
                        SecurityContextHolder.getContext().getAuthentication()
                                == authentification));
    }

    @GetMapping("/api/rh/candidatures")
    Map<String, Object> candidatures() {
        ENTREES.incrementAndGet();
        return Map.of("candidatures", 42, "acces", "RH par regle d'URL");
    }

    // ── securite au niveau methode ───────────────────────────────────────

    /**
     * La même URL pour tout le monde, et un droit qui dépend de la ressource.
     *
     * <p>Aucune règle d'URL ne peut exprimer « seulement si l'offre vous
     * appartient » : le chemin est le même pour l'auteur et pour les autres.
     * Le chapitre 6 mesure les deux réponses.
     */
    @GetMapping("/api/offres/{reference}/brouillon")
    // TODO : n'autoriser que l'auteur de l'offre, en interrogeant le bean `proprietaire`
    @PreAuthorize("isAuthenticated()")
    Map<String, Object> brouillon(@PathVariable String reference) {
        ENTREES.incrementAndGet();
        return Map.of("reference", reference, "etat", "brouillon",
                "note", "salaire reel negociable jusqu'a 70000");
    }

    @GetMapping("/api/rh/statistiques")
    @PreAuthorize("hasRole('RH')")
    Map<String, Object> statistiques() {
        ENTREES.incrementAndGet();
        return Map.of("offres", 2, "candidatures", 42);
    }

    // ── le monde a session, pour le chapitre 3 ───────────────────────────

    @GetMapping("/session/connexion")
    Map<String, Object> connexionParSession(HttpServletRequest requete,
            jakarta.servlet.http.HttpServletResponse reponse) {
        ENTREES.incrementAndGet();
        // On demande EXPRESSEMENT une session : c'est ce qui fait sortir le
        // cookie JSESSIONID que le chapitre 1 compare a l'API sans etat.
        var session = requete.getSession(true);
        // ⚠️ ET ON Y RANGE LE CONTEXTE. Depuis Spring Security 6,
        // `httpBasic` ne persiste plus l'authentification dans la session :
        // chaque requete doit represente ses identifiants. Sans cette ligne,
        // le cookie sortait bien et n'authentifiait rien — la demonstration
        // CSRF du chapitre 3 mesurait alors deux 401 au lieu d'un 403 et
        // d'un 200. C'est ici que « la session porte l'identite » devient
        // vrai, et c'est exactement ce que CSRF protege.
        DEPOT.saveContext(SecurityContextHolder.getContext(), requete, reponse);
        // ⚠️ IL FAUT LIRE LE JETON POUR QU'IL EXISTE. Depuis Spring Security
        // 6, `CsrfFilter` ne pose l'attribut que sous forme paresseuse : tant
        // que personne n'appelle `getToken()`, aucun jeton n'est engendre et
        // aucun cookie `XSRF-TOKEN` ne sort. Une SPA qui cherche ce cookie
        // avant d'avoir appele une route qui le reveille ne le trouve jamais.
        var csrf = (org.springframework.security.web.csrf.CsrfToken)
                requete.getAttribute(
                        org.springframework.security.web.csrf.CsrfToken.class.getName());
        return Map.of("session", session.getId(),
                "csrfEnTete", csrf == null ? "" : csrf.getHeaderName(),
                "csrfJeton", csrf == null ? "" : csrf.getToken());
    }

    /** Qui parle, vu depuis la chaîne de session — sans Basic, juste le cookie. */
    @GetMapping("/session/moi")
    Map<String, Object> moiParSession(Authentication authentification) {
        ENTREES.incrementAndGet();
        return Map.of("sujet", authentification.getName(),
                "portePar", "le cookie de session");
    }

    @PostMapping("/session/candidater")
    Map<String, Object> candidaterParSession() {
        ENTREES.incrementAndGet();
        return Map.of("resultat", "candidature enregistree");
    }
}
