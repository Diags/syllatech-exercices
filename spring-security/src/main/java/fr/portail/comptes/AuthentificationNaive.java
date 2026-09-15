package fr.portail.comptes;

import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * L'authentification qu'on écrit soi-même — et sa fuite.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> Ce code est
 * celui que presque tout le monde écrit la première fois, et il est juste sur
 * tout ce qui se voit : il ne dit pas si le compte existe, il renvoie le même
 * message dans les deux cas, il compare des empreintes BCrypt.
 *
 * <p>Il fuit par le <strong>temps</strong>. Sur un compte inconnu, il rend la
 * main tout de suite ; sur un compte connu au mauvais mot de passe, il a
 * d'abord fait tourner BCrypt — une centaine de millisecondes. Un attaquant
 * qui chronomètre les réponses énumère donc les comptes existants, sans
 * jamais lire un message d'erreur.
 *
 * <p>Le chapitre 2 mesure les deux chemins, puis mesure les mêmes sur le
 * {@code AuthenticationManager} de Spring — qui, lui, fait tourner BCrypt
 * contre une empreinte factice quand le compte n'existe pas. Cette méthode
 * porte d'ailleurs un nom dans le code de Spring Security :
 * {@code mitigateAgainstTimingAttack}.
 */
@Service
public class AuthentificationNaive {

    private final ServiceDUtilisateurs utilisateurs;

    private final PasswordEncoder encodeur;

    AuthentificationNaive(ServiceDUtilisateurs utilisateurs,
                          PasswordEncoder encodeur) {
        this.utilisateurs = utilisateurs;
        this.encodeur = encodeur;
    }

    /**
     * Vérifie un couple identifiant / mot de passe.
     *
     * @return vrai si les deux concordent — et rien de plus, jamais
     */
    public boolean verifier(String identifiant, String motDePasse) {
        if (!utilisateurs.existe(identifiant)) {
            // Le defaut est ICI, et il est invisible : on part sans avoir
            // rien calcule. Un compte inconnu coute donc mille fois moins
            // cher qu'un compte connu.
            return false;
        }
        return encodeur.matches(motDePasse,
                utilisateurs.compte(identifiant).empreinte());
    }
}
