package fr.portail.offre;

import fr.portail.erreurs.EntrepriseInconnue;
import fr.portail.erreurs.PanneMetier;
import fr.portail.offre.dto.CreerOffreDto;
import fr.portail.offre.dto.OffreDto;
import java.util.List;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * La logique métier des offres — et quatre démonstrations de transaction.
 *
 * <p>Les quatre méthodes {@code demo*} existent pour être mesurées par le
 * chapitre 4. Elles écrivent deux offres puis échouent, et la seule question
 * est : <strong>combien de lignes restent en base ?</strong> Zéro veut dire
 * que la transaction a joué son rôle ; deux veut dire qu'elle ne l'a pas
 * joué.
 */
@Service
public class OffreService {

    private final OffreRepository offres;

    private final EntrepriseRepository entreprises;

    /** Combien de fois la logique métier a réellement été atteinte. */
    private final AtomicInteger entrees = new AtomicInteger();

    /**
     * Un seul constructeur : {@code @Autowired} est inutile, et les deux
     * dépendances sont {@code final}. C'est ce que le chapitre 1 défend.
     */
    OffreService(OffreRepository offres, EntrepriseRepository entreprises) {
        this.offres = offres;
        this.entreprises = entreprises;
    }

    public int entrees() {
        return entrees.get();
    }

    public void remettreAZeroLesEntrees() {
        entrees.set(0);
    }

    /**
     * La liste publiée.
     *
     * <p>{@code readOnly = true} n'est pas décoratif : Hibernate n'installe
     * alors aucun instantané de comparaison pour la détection des
     * modifications, et la lecture coûte moins cher en mémoire.
     *
     * <p>La conversion en DTO se fait <strong>ici</strong>, dans la
     * transaction. La faire dans le contrôleur lirait l'association sur une
     * entité détachée — c'est exactement la
     * {@code LazyInitializationException} du chapitre 4.
     */
    @Transactional(readOnly = true)
    public List<OffreDto> listerOffres() {
        return offres.findAllAvecEntreprise().stream().map(OffreDto::de).toList();
    }

    /** La même liste, écrite avec le {@code findAll()} qui produit le N+1. */
    @Transactional(readOnly = true)
    public List<OffreDto> listerOffresNaivement() {
        return offres.findAll().stream().map(OffreDto::de).toList();
    }

    /**
     * Les entités, telles quelles.
     *
     * <p>⚠️ Elles ne devraient jamais sortir de cette couche. Cette méthode
     * n'existe que pour alimenter la route de démonstration du chapitre 3,
     * celle qui montre ce qui fuit quand on publie une entité.
     */
    @Transactional(readOnly = true)
    public List<Offre> listerToutesLesEntites() {
        return offres.findAllAvecEntreprise();
    }

    @Transactional
    public OffreDto creer(CreerOffreDto demande) {
        entrees.incrementAndGet();
        var entreprise = entreprises.findByNom(demande.entreprise())
                .orElseThrow(() -> new EntrepriseInconnue(demande.entreprise()));
        // Le salaire reel n'est PAS dans la demande : il ne peut donc pas
        // venir du client. On le pose ici, a partir du minimum publie.
        var offre = new Offre(demande.titre(), demande.salaireMin(),
                demande.salaireMin() + 5_000, demande.contactEmail());
        entreprise.ajouter(offre);
        offres.save(offre);
        return OffreDto.de(offre);
    }

    public long combien() {
        return offres.count();
    }

    // ── les quatre demonstrations du chapitre 4 ──────────────────────────

    /**
     * (1) Deux écritures, puis une {@link RuntimeException}.
     *
     * <p>Attendu : <strong>zéro</strong> ligne ajoutée. C'est le cas nominal,
     * celui que tout le monde connaît.
     */
    @Transactional
    public void demoRollbackSurRuntime() {
        ecrireDeux("rollback-runtime");
        throw new IllegalStateException("le quota de publication est atteint");
    }

    /**
     * (2) Les mêmes écritures, puis une exception <strong>vérifiée</strong>.
     *
     * <p>Attendu : <strong>deux</strong> lignes. Spring ne fait un rollback
     * que sur {@code RuntimeException} et {@code Error} — une exception
     * vérifiée laisse la transaction se valider. C'est le premier des deux
     * pièges que le cours nomme.
     */
    @Transactional
    public void demoPasDeRollbackSurExceptionVerifiee() throws PanneMetier {
        ecrireDeux("verifiee");
        throw new PanneMetier("le service de paie ne repond pas");
    }

    /**
     * (3) La même chose, avec {@code rollbackFor}.
     *
     * <p>Attendu : <strong>zéro</strong> ligne. Le correctif tient dans un
     * attribut de l'annotation, à condition de savoir qu'il existe.
     */
    @Transactional(rollbackFor = PanneMetier.class)
    public void demoRollbackForSurExceptionVerifiee() throws PanneMetier {
        ecrireDeux("rollback-for");
        throw new PanneMetier("le service de paie ne repond pas");
    }

    /**
     * (4) Un appel <strong>interne</strong> à la méthode (1).
     *
     * <p>Attendu : <strong>deux</strong> lignes. Cette méthode-ci n'est pas
     * transactionnelle ; elle appelle {@code this.demoRollbackSurRuntime()},
     * donc l'appel ne passe pas par le proxy Spring et l'annotation ne
     * s'applique pas. Chaque {@code save} s'exécute alors dans sa propre
     * petite transaction, et se valide.
     *
     * <p>C'est le second piège du cours, et le plus coûteux : le code a
     * l'air correct, l'annotation est bien là, et elle ne sert à rien.
     */
    public void demoAppelInterne() {
        try {
            this.demoRollbackSurRuntime();
        } catch (IllegalStateException attendue) {
            // L'exception est celle qu'on attendait. Ce qui nous interesse
            // est ce qui reste en base APRES.
        }
    }

    /**
     * Écrit deux offres d'essai, rattachées à Nordeau.
     *
     * <p>⚠️ Elle passe par {@code offre.setEntreprise(...)} et NON par
     * {@code entreprise.ajouter(offre)}. Les deux font la même chose du point
     * de vue de la base — le {@code @ManyToOne} est le côté propriétaire, et
     * c'est lui qui porte la colonne. Mais {@code ajouter} touche la
     * collection {@code offres}, qui est {@code LAZY} : appelée par
     * {@code demoAppelInterne}, c'est-à-dire <strong>hors transaction</strong>,
     * elle lève une {@code LazyInitializationException} avant même d'écrire
     * quoi que ce soit.
     *
     * <p>La démonstration de l'appel interne se serait alors arrêtée sur la
     * mauvaise erreur. C'est arrivé en écrivant ce chapitre, et c'est une
     * illustration de plus de la section 4.
     */
    private void ecrireDeux(String marque) {
        var entreprise = entreprises.findByNom("Nordeau")
                .orElseThrow(() -> new EntrepriseInconnue("Nordeau"));
        for (int i = 1; i <= 2; i++) {
            var offre = new Offre("essai " + marque + " " + i, 30_000, 35_000,
                    "essai@exemple.test");
            offre.setEntreprise(entreprise);
            offres.save(offre);
        }
    }

    /** Efface les offres d'essai, pour que chaque démonstration reparte à zéro. */
    @Transactional
    public void effacerLesEssais() {
        offres.deleteAll(offres.findAll().stream()
                .filter(o -> o.getTitre().startsWith("essai "))
                .toList());
    }
}
