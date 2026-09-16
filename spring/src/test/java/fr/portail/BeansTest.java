package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import fr.portail.coeur.Brouillon;
import fr.portail.coeur.CompteurDeVues;
import fr.portail.coeur.CompteurSur;
import fr.portail.coeur.CycleDeVie;
import fr.portail.offre.OffreController;
import fr.portail.offre.OffreService;
import java.lang.reflect.Modifier;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executors;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.BeanCurrentlyInCreationException;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.context.ApplicationContext;
import org.springframework.context.annotation.AnnotationConfigApplicationContext;
import org.springframework.context.annotation.Bean;

/** Chapitre 1 — IoC, portées, injection. */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
class BeansTest {

    @Autowired
    ApplicationContext contexte;

    @Nested
    @DisplayName("les portees")
    class Portees {

        @Test
        @DisplayName("un service est un singleton : deux demandes, un objet")
        void leSingleton() {
            assertThat(contexte.getBean(OffreService.class))
                    .isSameAs(contexte.getBean(OffreService.class));
        }

        @Test
        @DisplayName("un prototype est construit a chaque demande")
        void lePrototype() {
            var premier = contexte.getBean(Brouillon.class);
            var second = contexte.getBean(Brouillon.class);
            assertThat(premier).isNotSameAs(second);
            assertThat(premier.numero()).isNotEqualTo(second.numero());
        }

        @Test
        @DisplayName("un prototype porte son propre etat")
        void lEtatDuPrototype() {
            var premier = contexte.getBean(Brouillon.class).titre("A");
            var second = contexte.getBean(Brouillon.class).titre("B");
            assertThat(premier.titre()).isEqualTo("A");
            assertThat(second.titre()).isEqualTo("B");
        }
    }

    @Nested
    @DisplayName("le cycle de vie")
    class Cycle {

        @Test
        @DisplayName("le constructeur voit deja sa dependance")
        void laDependanceEstLaDesLeConstructeur() {
            assertThat(CycleDeVie.journal())
                    .anyMatch(e -> e.startsWith("constructeur")
                            && e.endsWith("true"));
        }

        @Test
        @DisplayName("@PostConstruct vient apres le constructeur")
        void lOrdre() {
            var journal = CycleDeVie.journal();
            int construction = indexDe(journal, "constructeur");
            int apres = indexDe(journal, "@PostConstruct");
            assertThat(construction).isNotNegative();
            assertThat(apres).isGreaterThan(construction);
        }

        @Test
        @DisplayName("la dependance injectee est bien le bean du conteneur")
        void cEstLeMemeBean() {
            assertThat(contexte.getBean(CycleDeVie.class).parConstructeur())
                    .isSameAs(contexte.getBean(CompteurSur.class));
        }

        private int indexDe(java.util.List<String> journal, String debut) {
            for (int i = 0; i < journal.size(); i++) {
                if (journal.get(i).startsWith(debut)) {
                    return i;
                }
            }
            return -1;
        }
    }

    @Nested
    @DisplayName("l'injection par constructeur")
    class Injection {

        @Test
        @DisplayName("le controleur a un seul constructeur et des champs final")
        void leControleur() {
            assertThat(OffreController.class.getDeclaredConstructors()).hasSize(1);
            assertThat(OffreController.class.getDeclaredFields())
                    .allMatch(champ -> Modifier.isFinal(champ.getModifiers()),
                            "tous les champs du controleur doivent etre final");
        }

        @Test
        @DisplayName("aucun @Autowired n'est necessaire avec un seul constructeur")
        void pasDAutowired() {
            assertThat(OffreController.class.getDeclaredConstructors()[0]
                    .getAnnotation(Autowired.class)).isNull();
        }

        @Test
        @DisplayName("une dependance circulaire par constructeur est refusee")
        void leCercleParConstructeur() {
            assertThatThrownBy(() -> {
                try (var jetable = new AnnotationConfigApplicationContext()) {
                    jetable.register(CercleParConstructeur.class);
                    jetable.refresh();
                }
            }).rootCause().isInstanceOf(BeanCurrentlyInCreationException.class);
        }

        @Test
        @DisplayName("la meme, par champ, demarre sans rien dire")
        void leCercleParChamp() {
            try (var jetable = new AnnotationConfigApplicationContext()) {
                jetable.register(CercleParChamp.class);
                jetable.refresh();
                var a = jetable.getBean(CercleParChamp.A.class);
                assertThat(a.b).isNotNull();
                assertThat(a.b.a).isSameAs(a);
            }
        }
    }

    @Nested
    @DisplayName("un singleton avec etat, sous la charge")
    class SousLaCharge {

        @Test
        @DisplayName("le compteur AtomicLong ne perd rien")
        void leCompteurSur() {
            var compteur = contexte.getBean(CompteurSur.class);
            compteur.remettreAZero();
            enParallele(500, i -> compteur.enregistrer("client-" + i));
            assertThat(compteur.vues()).isEqualTo(500);
        }

        @Test
        @DisplayName("le champ `long vues++` en perd")
        void leCompteurAvecEtat() {
            var compteur = contexte.getBean(CompteurDeVues.class);
            compteur.remettreAZero();
            enParallele(20_000, i -> compteur.enregistrer("client-" + i));
            assertThat(compteur.vues())
                    .as("PIECE A CONVICTION : `vues++` n'est pas indivisible. "
                        + "C'est une course : si ce test echoue un jour, "
                        + "relancez-le avant de conclure")
                    .isLessThan(20_000);
        }

        @Test
        @DisplayName("et il laisse une requete lire le nom d'une autre")
        void leCroisementDeDonnees() {
            var compteur = contexte.getBean(CompteurDeVues.class);
            compteur.remettreAZero();
            var croisements = ConcurrentHashMap.<String>newKeySet();
            enParallele(2_000, i -> {
                String mien = "client-" + i;
                compteur.enregistrer(mien);
                if (!mien.equals(compteur.dernierUtilisateur())) {
                    croisements.add(mien);
                }
            });
            assertThat(croisements)
                    .as("le champ partage laisse fuir des donnees entre appels")
                    .isNotEmpty();
        }

        private void enParallele(int combien, java.util.function.IntConsumer geste) {
            try (var executeur = Executors.newVirtualThreadPerTaskExecutor()) {
                for (int i = 0; i < combien; i++) {
                    int numero = i;
                    executeur.submit(() -> geste.accept(numero));
                }
            }
        }
    }

    // Enregistrees a la main : annotees, elles deviendraient des beans de
    // l'application, et leurs deux `a()` se percuteraient au demarrage.
    static class CercleParConstructeur {

        static class A {
            A(B b) {
            }
        }

        static class B {
            B(A a) {
            }
        }

        @Bean
        A a(B b) {
            return new A(b);
        }

        @Bean
        B b(A a) {
            return new B(a);
        }
    }

    static class CercleParChamp {

        static class A {
            @Autowired
            B b;
        }

        static class B {
            @Autowired
            A a;
        }

        @Bean
        A a() {
            return new A();
        }

        @Bean
        B b() {
            return new B();
        }
    }
}
