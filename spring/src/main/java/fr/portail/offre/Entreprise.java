package fr.portail.offre;

import com.fasterxml.jackson.annotation.JsonIgnore;
import jakarta.persistence.CascadeType;
import jakarta.persistence.Entity;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.OneToMany;
import java.util.ArrayList;
import java.util.List;

/**
 * Une entreprise qui publie des offres.
 *
 * <p>Le côté « un » de la relation. La liste d'offres est {@code LAZY} —
 * c'est le défaut de JPA pour un {@code @OneToMany}, et c'est ce qui produit
 * la {@code LazyInitializationException} que le chapitre 4 déclenche
 * volontairement.
 */
@Entity
public class Entreprise {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    private String nom;

    private String ville;

    /**
     * Une note qui ne doit jamais sortir de la base.
     *
     * <p>Elle est ici pour le chapitre 3 : une route qui rend l'entité
     * l'expose au client, une route qui rend un DTO ne l'expose pas. La
     * différence se mesure dans le JSON reçu.
     */
    private String noteInterne;

    /**
     * ⚠️ Le {@code @JsonIgnore} n'est pas la pour proteger une donnee : il
     * est la parce que sans lui, Jackson tourne en rond. Une offre renvoie
     * son entreprise, qui renvoie ses offres, qui renvoient leur
     * entreprise — et la serialisation finit en {@code StackOverflowError}.
     *
     * <p>C'est deja une reponse a la question du chapitre 3. Pour publier
     * une entite, il faut commencer a l'annoter POUR HTTP : la classe se met
     * alors a porter deux contrats a la fois, celui de la base et celui de
     * l'API, et toute evolution de l'un touche l'autre. Le DTO separe les
     * deux, et cette annotation disparait.
     */
    @JsonIgnore
    @OneToMany(mappedBy = "entreprise", cascade = CascadeType.ALL,
               fetch = FetchType.LAZY)
    private List<Offre> offres = new ArrayList<>();

    protected Entreprise() {
        // JPA exige un constructeur sans argument. Il reste `protected` :
        // le reste du code doit passer par celui qui remplit les champs.
    }

    public Entreprise(String nom, String ville, String noteInterne) {
        this.nom = nom;
        this.ville = ville;
        this.noteInterne = noteInterne;
    }

    public Long getId() {
        return id;
    }

    public String getNom() {
        return nom;
    }

    public String getVille() {
        return ville;
    }

    public String getNoteInterne() {
        return noteInterne;
    }

    public List<Offre> getOffres() {
        return offres;
    }

    public void ajouter(Offre offre) {
        offres.add(offre);
        offre.setEntreprise(this);
    }
}
