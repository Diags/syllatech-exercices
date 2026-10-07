package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.erreurs.PanneMetier;
import fr.portail.mesure.CompteurDeRequetes;
import fr.portail.offre.EntrepriseRepository;
import fr.portail.offre.OffreRepository;
import fr.portail.offre.OffreService;
import org.hibernate.LazyInitializationException;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

/** Chapitre 4 — le N+1 compté, et les transactions qui n'en sont pas. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class JpaTest {

    @Autowired
    OffreService service;

    @Autowired
    OffreRepository offres;

    @Autowired
    EntrepriseRepository entreprises;

    @BeforeEach
    void repartirDeZero() {
        service.effacerLesEssais();
    }

    @AfterEach
    void nettoyer() {
        service.effacerLesEssais();
        CompteurDeRequetes.arreter();
    }

    @Test
    @DisplayName("le jeu de donnees est bien celui que les chapitres annoncent")
    void leJeuDeDonnees() {
        assertThat(entreprises.count()).isEqualTo(4);
        assertThat(offres.count()).isEqualTo(10);
    }

    @Nested
    @DisplayName("le N+1")
    class NPlusUn {

        @Test
        @DisplayName("findAll() suivi d'un acces a l'association coute 1 + N")
        void leNPlusUn() {
            var requetes = CompteurDeRequetes.pendant(service::listerOffresNaivement);
            assertThat(requetes)
                    .as("une requete pour la liste, une par entreprise distincte")
                    .hasSize(5);
            assertThat(CompteurDeRequetes.selectsSur(requetes, "entreprise"))
                    .isEqualTo(4);
        }

        @Test
        @DisplayName("findAllAvecEntreprise() n'en coute qu'une")
        void leJoinFetch() {
            var requetes = CompteurDeRequetes.pendant(service::listerOffres);
            assertThat(requetes).hasSize(1);
            assertThat(requetes.getFirst().toLowerCase(java.util.Locale.ROOT))
                    .contains("join");
        }

        @Test
        @DisplayName("les deux rendent exactement le meme resultat")
        void memeResultat() {
            assertThat(service.listerOffresNaivement())
                    .containsExactlyInAnyOrderElementsOf(service.listerOffres());
        }

        @Test
        @DisplayName("une jointure SANS fetch ne charge pas l'association")
        void laJointureSansFetch() {
            var requetes = CompteurDeRequetes.pendant(
                    () -> offres.findByEntrepriseVille("Lyon"));
            assertThat(requetes).hasSize(1);
            assertThat(requetes.getFirst().toLowerCase(java.util.Locale.ROOT))
                    .as("elle joint pour filtrer, mais ne remplit rien")
                    .contains("join");
        }
    }

    @Nested
    @DisplayName("le chargement paresseux")
    class Paresse {

        @Test
        @DisplayName("lire l'association hors transaction echoue")
        void horsTransaction() {
            var detachee = offres.findAll().getFirst();
            assertThatThrownBy(() -> detachee.getEntreprise().getNom())
                    .isInstanceOf(LazyInitializationException.class);
        }

        @Test
        @DisplayName("la convertir dans le service, lui, fonctionne")
        void dansLaTransaction() {
            assertThat(service.listerOffres())
                    .allSatisfy(dto -> assertThat(dto.entreprise()).isNotBlank());
        }

        @Test
        @DisplayName("open-in-view est coupe : c'est ce qui rend l'echec visible")
        void openInViewEstCoupe(
                @Autowired org.springframework.core.env.Environment env) {
            assertThat(env.getProperty("spring.jpa.open-in-view"))
                    .as("laisse a `true`, il masquerait la LazyInitializationException "
                        + "en gardant une connexion ouverte pendant toute la reponse")
                    .isEqualTo("false");
        }
    }

    @Nested
    @DisplayName("ce qui declenche un rollback, et ce qui n'en declenche pas")
    class Transactions {

        @Test
        @DisplayName("une RuntimeException annule les deux ecritures")
        void laRuntimeException() {
            assertThat(ecritesApres(() -> {
                try {
                    service.demoRollbackSurRuntime();
                } catch (IllegalStateException attendue) {
                    // c'est le cas mesure
                }
            })).isZero();
        }

        @Test
        @DisplayName("une exception VERIFIEE les laisse en base")
        void lExceptionVerifiee() {
            assertThat(ecritesApres(() -> {
                try {
                    service.demoPasDeRollbackSurExceptionVerifiee();
                } catch (PanneMetier attendue) {
                    // c'est le cas mesure
                }
            }))
                    .as("PIEGE DU COURS : par defaut, seul un RuntimeException "
                        + "declenche le rollback")
                    .isEqualTo(2);
        }

        @Test
        @DisplayName("rollbackFor corrige le cas precedent")
        void leRollbackFor() {
            assertThat(ecritesApres(() -> {
                try {
                    service.demoRollbackForSurExceptionVerifiee();
                } catch (PanneMetier attendue) {
                    // c'est le cas mesure
                }
            })).isZero();
        }

        @Test
        @DisplayName("un appel interne contourne le proxy, donc la transaction")
        void lAppelInterne() {
            assertThat(ecritesApres(service::demoAppelInterne))
                    .as("PIEGE DU COURS : `this.methodeAnnotee()` ne passe pas "
                        + "par le proxy Spring")
                    .isEqualTo(2);
        }

        @Test
        @DisplayName("le service est bien enveloppe dans un proxy")
        void leProxyExiste() {
            assertThat(org.springframework.aop.support.AopUtils.isAopProxy(service))
                    .as("sans proxy, @Transactional ne ferait rien nulle part")
                    .isTrue();
        }

        private long ecritesApres(Runnable geste) {
            long avant = service.combien();
            geste.run();
            return service.combien() - avant;
        }
    }

    @Nested
    @DisplayName("l'instrument de mesure lui-meme")
    class Instrument {

        @Test
        @DisplayName("il ne compte rien tant qu'on ne l'a pas demande")
        void ilEstEteintParDefaut() {
            CompteurDeRequetes.arreter();
            offres.count();
            assertThat(CompteurDeRequetes.combien()).isZero();
        }

        @Test
        @DisplayName("il rend la main meme si le bloc mesure echoue")
        void ilNAvalePasLesExceptions() {
            assertThatThrownBy(() -> CompteurDeRequetes.pendant(() -> {
                throw new IllegalStateException("boum");
            })).isInstanceOf(IllegalStateException.class).hasMessage("boum");
        }
    }
}
