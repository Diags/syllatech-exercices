package fr.portail.comptes;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.security.core.userdetails.User;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.security.core.userdetails.UsernameNotFoundException;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * La source de vérité des comptes du portail.
 *
 * <p>Le contrat est minuscule : « d'un identifiant, rends-moi l'utilisateur
 * et ses rôles ». Ici les comptes vivent en mémoire ; en production ils
 * viennent d'une base ou d'un annuaire, et <strong>rien d'autre ne change</strong>.
 *
 * <p>Sur un identifiant inconnu, on lève {@link UsernameNotFoundException} —
 * et c'est {@code DaoAuthenticationProvider} qui décide ensuite quoi en dire
 * au client. Le chapitre 2 mesure ce qu'il en fait : le même message que pour
 * un mot de passe faux, <em>et</em> le même temps de réponse. Les deux
 * comptent, et le second est celui qu'on oublie.
 */
@Service
public class ServiceDUtilisateurs implements UserDetailsService {

    private final Map<String, Compte> comptes = new ConcurrentHashMap<>();

    private final PasswordEncoder encodeur;

    ServiceDUtilisateurs(PasswordEncoder encodeur) {
        this.encodeur = encodeur;
        poser("awa", "motdepasse", "awa.diallo@exemple.test", "Awa Diallo",
                List.of("RH", "USER"));
        poser("karim", "motdepasse", "karim.b@exemple.test", "Karim Bensaid",
                List.of("USER"));
        poser("lea", "motdepasse", "lea.m@exemple.test", "Lea Marchand",
                List.of("ADMIN", "RH", "USER"));
    }

    public final void poser(String identifiant, String motDePasse,
                            String courriel, String nom, List<String> roles) {
        comptes.put(identifiant, new Compte(identifiant,
                encodeur.encode(motDePasse), courriel, nom, roles));
    }

    /** Supprime un compte. Le chapitre 4 s'en sert pour « déconnecter ». */
    public boolean retirer(String identifiant) {
        return comptes.remove(identifiant) != null;
    }

    public boolean existe(String identifiant) {
        return comptes.containsKey(identifiant);
    }

    public Compte compte(String identifiant) {
        var compte = comptes.get(identifiant);
        if (compte == null) {
            throw new UsernameNotFoundException("compte inconnu");
        }
        return compte;
    }

    @Override
    public UserDetails loadUserByUsername(String identifiant) {
        var compte = comptes.get(identifiant);
        if (compte == null) {
            // ⚠️ Le message ne dit PAS que le compte n'existe pas. Spring le
            // remplace de toute facon par « Bad credentials », mais un
            // message precis finit toujours par ressortir dans un journal —
            // et un journal finit toujours par etre lu.
            throw new UsernameNotFoundException("identifiants invalides");
        }
        return User.withUsername(compte.identifiant())
                .password(compte.empreinte())
                .roles(compte.roles().toArray(String[]::new))
                .build();
    }

    /** Un compte du portail. */
    public record Compte(String identifiant, String empreinte, String courriel,
                         String nom, List<String> roles) {
    }
}
