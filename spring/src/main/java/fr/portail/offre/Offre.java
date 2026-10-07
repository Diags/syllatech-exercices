package fr.portail.offre;

import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.ManyToOne;

/**
 * Une offre d'emploi — l'entité JPA.
 *
 * <p>⚠️ Elle ne sort <strong>jamais</strong> de l'application telle quelle.
 * Le chapitre 3 montre ce que coûte de la renvoyer : le client reçoit
 * {@code noteInterne} de l'entreprise, le {@code salaireReel}, et la
 * structure exacte des tables. Le DTO est le contrat public ; ceci est le
 * schéma.
 *
 * <p>Le {@code @ManyToOne} est {@code LAZY} — ce n'est <em>pas</em> le défaut
 * de JPA, qui est {@code EAGER} de ce côté-là. C'est un choix, et le
 * chapitre 4 mesure ce qu'il change : avec {@code EAGER}, un
 * {@code findAll()} émet quand même une requête par ligne. Passer en
 * {@code EAGER} ne corrige donc pas le N+1 — seul un {@code join fetch} le
 * fait.
 */
@Entity
public class Offre {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String titre;

    private int salaireMin;

    /** Ce que l'entreprise est prête à payer. Jamais publié. */
    private int salaireReel;

    private String contactEmail;

    @ManyToOne(fetch = FetchType.LAZY)
    private Entreprise entreprise;

    protected Offre() {
        // Pour JPA.
    }

    public Offre(String titre, int salaireMin, int salaireReel,
                 String contactEmail) {
        this.titre = titre;
        this.salaireMin = salaireMin;
        this.salaireReel = salaireReel;
        this.contactEmail = contactEmail;
    }

    public Long getId() {
        return id;
    }

    public String getTitre() {
        return titre;
    }

    public int getSalaireMin() {
        return salaireMin;
    }

    public int getSalaireReel() {
        return salaireReel;
    }

    public String getContactEmail() {
        return contactEmail;
    }

    public Entreprise getEntreprise() {
        return entreprise;
    }

    void setEntreprise(Entreprise entreprise) {
        this.entreprise = entreprise;
    }
}
