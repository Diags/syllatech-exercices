package fr.portail.securite;

import fr.portail.api.DemandeConnexion;
import fr.portail.api.Jetons;
import fr.portail.domaine.Compte;
import fr.portail.domaine.CompteRepository;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.security.authentication.BadCredentialsException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * La connexion, et ce qui distingue vraiment les deux jetons.
 *
 * <p>⚠️ UN ACCESS TOKEN NE SE REVOQUE PAS. C'est la propriete qui le rend
 * scalable — le serveur n'a rien a memoriser — et c'est exactement ce qui
 * empeche de l'annuler. On le fait donc vivre COURT.
 *
 * <p>⚠️ UN REFRESH TOKEN, LUI, EST STOCKE. C'est ce qui permet de le
 * revoquer, et c'est la seule raison pour laquelle il peut vivre des jours.
 * Un refresh token « stateless » n'est pas un refresh token : c'est un
 * access token de longue duree, avec tous ses defauts et aucun de ses
 * avantages.
 */
@Service
public class ServiceAuthentification {

    private final CompteRepository comptes;
    private final PasswordEncoder encodeur;
    private final Jeton jeton;
    private final long dureeAccess;
    private final long dureeRefresh;

    /**
     * Les refresh tokens encore valides, par identifiant.
     *
     * <p>⚠️ En memoire ici, pour que le projet tourne sans Redis. En
     * production, c'est un magasin partage — sinon deux instances derriere
     * un repartiteur ne revoquent pas les memes jetons, et le README le
     * dit.
     */
    private final Map<String, String> refreshValides = new ConcurrentHashMap<>();

    public ServiceAuthentification(
            CompteRepository comptes, PasswordEncoder encodeur,
            @Value("${portail.jwt.cle}") String cle,
            @Value("${portail.jwt.duree-access-en-secondes}") long dureeAccess,
            @Value("${portail.jwt.duree-refresh-en-secondes}") long dureeRefresh) {
        this.comptes = comptes;
        this.encodeur = encodeur;
        this.jeton = new Jeton(cle);
        this.dureeAccess = dureeAccess;
        this.dureeRefresh = dureeRefresh;
    }

    public Jetons connecter(DemandeConnexion demande) {
        Optional<Compte> trouve = comptes.findByIdentifiant(demande.identifiant());

        // ⚠️ LE MEME MESSAGE DANS LES DEUX CAS. Distinguer « compte
        // inconnu » de « mot de passe faux » enumere les comptes existants.
        if (trouve.isEmpty()
                || !encodeur.matches(demande.motDePasse(),
                                     trouve.get().getMotDePasse())) {
            throw new BadCredentialsException("identifiants invalides");
        }
        Compte compte = trouve.get();
        if (!compte.estActif()) {
            throw new BadCredentialsException("identifiants invalides");
        }
        return fabriquer(compte);
    }

    /** Echange un refresh token contre un nouvel access token. */
    public Jetons rafraichir(String refreshToken) {
        Jeton.Verdict verdict =
                jeton.verifier(refreshToken, "refresh", Instant.now());
        if (!verdict.valide()) {
            throw new BadCredentialsException(verdict.motif());
        }
        // ⚠️ LA SIGNATURE NE SUFFIT PAS : on verifie aussi que ce jeton
        // precis est TOUJOURS dans la liste. C'est ce controle, et lui
        // seul, qui rend la revocation possible.
        if (!refreshToken.equals(refreshValides.get(verdict.sujet()))) {
            throw new BadCredentialsException("refresh token revoque");
        }
        Compte compte = comptes.findByIdentifiant(verdict.sujet())
                .filter(Compte::estActif)
                .orElseThrow(() -> new BadCredentialsException("compte inactif"));
        return fabriquer(compte);
    }

    /** Ce que fait une deconnexion — ou la desactivation d'un compte. */
    public void revoquer(String identifiant) {
        refreshValides.remove(identifiant);
    }

    private Jetons fabriquer(Compte compte) {
        Instant maintenant = Instant.now();
        String access = jeton.signer(compte.getIdentifiant(), compte.roles(),
                                     "access", dureeAccess, maintenant);
        String refresh = jeton.signer(compte.getIdentifiant(), compte.roles(),
                                      "refresh", dureeRefresh, maintenant);
        refreshValides.put(compte.getIdentifiant(), refresh);
        return new Jetons(access, refresh, dureeAccess);
    }

    public Jeton jeton() {
        return jeton;
    }

    public long dureeAccess() {
        return dureeAccess;
    }
}
