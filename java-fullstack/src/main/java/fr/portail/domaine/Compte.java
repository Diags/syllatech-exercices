package fr.portail.domaine;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import java.util.List;

/**
 * Un compte du portail.
 *
 * <p>⚠️ LE MOT DE PASSE N'EST JAMAIS STOCKE EN CLAIR, et cette classe ne
 * sait pas le verifier : elle porte une EMPREINTE. C'est le
 * {@code PasswordEncoder} qui compare, et lui seul.
 */
@Entity
public class Compte {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true, length = 60)
    private String identifiant;

    /**
     * ⚠️ 60 CARACTERES, ET C'EST UNE VALEUR EXACTE. Une empreinte BCrypt en
     * fait toujours 60. Une colonne plus courte la tronque — sans erreur sur
     * certaines bases — et la comparaison echoue alors pour tout le monde,
     * ou pire, reussit pour n'importe quel mot de passe selon l'encodeur.
     */
    @Column(name = "mot_de_passe", nullable = false, length = 60)
    private String motDePasse;

    /** Les roles, separes par des virgules : ROLE_USER,ROLE_RH. */
    @Column(nullable = false, length = 120)
    private String roles;

    @Column(nullable = false)
    private boolean actif = true;

    protected Compte() {
        // requis par JPA
    }

    public Compte(String identifiant, String motDePasse, String roles) {
        this.identifiant = identifiant;
        this.motDePasse = motDePasse;
        this.roles = roles;
    }

    public Long getId() {
        return id;
    }

    public String getIdentifiant() {
        return identifiant;
    }

    public String getMotDePasse() {
        return motDePasse;
    }

    public List<String> roles() {
        return List.of(roles.split(","));
    }

    public boolean estActif() {
        return actif;
    }

    /** Ce que fait un administrateur qui desactive un compte. */
    public void desactiver() {
        this.actif = false;
    }
}
