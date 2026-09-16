package fr.portail.domaine;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;

/**
 * Une offre du portail — l'entite JPA.
 *
 * <p>⚠️ CETTE CLASSE NE SORT JAMAIS DE L'APPLICATION. Elle decrit la table,
 * pas le contrat de l'API. Le jour ou la colonne {@code salaire_ke} change
 * de nom, c'est une migration Flyway ; si React lisait l'entite, ce serait
 * aussi un deploiement du front. Le DTO du chapitre 2 est ce qui separe les
 * deux cycles de vie.
 *
 * <p>⚠️ ET LE CHARGEMENT N'EST PAS SYMETRIQUE. Selon la specification JPA,
 * {@code @ManyToOne} est EAGER par defaut, {@code @OneToMany} est LAZY.
 * C'est cette dissymetrie qui fabrique le N+1 : ici, on a ecrit
 * {@code LAZY} explicitement, et le chapitre 3 COMPTE les requetes des deux
 * facons.
 */
@Entity
public class Offre {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, length = 160)
    private String titre;

    @Column(nullable = false, length = 40)
    private String pile;

    @Column(name = "salaire_ke", nullable = false)
    private int salaireEnKiloEuros;

    /**
     * ⚠️ {@code FetchType.LAZY} est ECRIT, parce que le defaut de
     * {@code @ManyToOne} est EAGER. Sans ce mot, chaque chargement d'offre
     * tire son entreprise, meme quand personne ne la demande — et le N+1
     * arrive par l'autre bout : une requete supplementaire par offre.
     */
    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "entreprise_id", nullable = false)
    private Entreprise entreprise;

    protected Offre() {
        // requis par JPA
    }

    public Offre(String titre, String pile, int salaireEnKiloEuros,
                 Entreprise entreprise) {
        this.titre = titre;
        this.pile = pile;
        this.salaireEnKiloEuros = salaireEnKiloEuros;
        this.entreprise = entreprise;
    }

    public Long getId() {
        return id;
    }

    public String getTitre() {
        return titre;
    }

    public String getPile() {
        return pile;
    }

    public int getSalaireEnKiloEuros() {
        return salaireEnKiloEuros;
    }

    public Entreprise getEntreprise() {
        return entreprise;
    }
}
