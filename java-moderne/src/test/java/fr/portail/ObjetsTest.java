package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.domaine.Dossier;
import fr.portail.domaine.Evenement;
import fr.portail.mesure.Compilateur;
import fr.portail.pieges.CandidatEcritMain;
import fr.portail.pieges.SacCompteur;
import fr.portail.pieges.SacParComposition;
import java.util.HashSet;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/** Chapitre 2 — records, encapsulation, héritage, hiérarchies scellées. */
class ObjetsTest {

    @Nested
    @DisplayName("ce qu'un record genere")
    class Records {

        @Test
        @DisplayName("equals et hashCode sont coherents entre deux exemplaires")
        void egalite() {
            var a = Candidat.de("Awa Diallo", 6, Competence.JAVA);
            var b = Candidat.de("Awa Diallo", 6, Competence.JAVA);
            assertEquals(a, b);
            assertEquals(a.hashCode(), b.hashCode());
            assertNotEquals(System.identityHashCode(a), System.identityHashCode(b));
        }

        @Test
        @DisplayName("un record se retrouve dans un HashSet")
        void retrouveDansUnEnsemble() {
            var ensemble = new HashSet<Candidat>();
            ensemble.add(Candidat.de("Awa Diallo", 6, Competence.JAVA));
            assertTrue(ensemble.contains(Candidat.de("Awa Diallo", 6, Competence.JAVA)));
        }

        @Test
        @DisplayName("toString nomme la classe et ses composants")
        void toStringEstLisible() {
            String texte = Candidat.de("Awa Diallo", 6).toString();
            assertTrue(texte.startsWith("Candidat["), texte);
            assertTrue(texte.contains("nom=Awa Diallo"), texte);
            assertTrue(texte.contains("anneesExperience=6"), texte);
        }

        @Test
        @DisplayName("un composant different suffit a rompre l'egalite")
        void unComposantSuffit() {
            assertNotEquals(Candidat.de("Awa Diallo", 6),
                    Candidat.de("Awa Diallo", 7));
            assertNotEquals(Candidat.de("Awa Diallo", 6, Competence.JAVA),
                    Candidat.de("Awa Diallo", 6));
        }

        @Test
        @DisplayName("le bloc compact refuse un candidat invalide")
        void leBlocCompactValide() {
            assertThrows(IllegalArgumentException.class,
                    () -> new Candidat("", "a@b", 1, java.util.Set.of()));
            assertThrows(IllegalArgumentException.class,
                    () -> new Candidat("Awa", "sans-arobase", 1, java.util.Set.of()));
            assertThrows(IllegalArgumentException.class,
                    () -> new Candidat("Awa", "a@b", -1, java.util.Set.of()));
        }

        @Test
        @DisplayName("le bloc compact copie l'ensemble recu")
        void leBlocCompactCopie() {
            var modifiable = new HashSet<Competence>();
            modifiable.add(Competence.JAVA);
            var candidat = new Candidat("Awa", "a@b", 3, modifiable);
            modifiable.add(Competence.DOCKER);
            assertEquals(1, candidat.competences().size(),
                    "la copie defensive protege le record apres construction");
        }

        @Test
        @DisplayName("les competences rendues ne sont pas modifiables")
        void lesCompetencesSontFermees() {
            var candidat = Candidat.de("Awa Diallo", 6, Competence.JAVA);
            assertThrows(UnsupportedOperationException.class,
                    () -> candidat.competences().add(Competence.DOCKER));
        }
    }

    @Nested
    @DisplayName("la meme classe ecrite a la main")
    class EcriteALaMain {

        @Test
        @DisplayName("equals dit oui, le HashSet dit non")
        void lOubliDeHashCode() {
            var a = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
            var b = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
            assertEquals(a, b);
            var ensemble = new HashSet<CandidatEcritMain>();
            ensemble.add(a);
            assertFalse(ensemble.contains(b),
                    "PIECE A CONVICTION : hashCode manque volontairement");
        }

        @Test
        @DisplayName("une List, elle, retrouve l'objet : le bug depend de la collection")
        void laListeRetrouve() {
            var a = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
            var b = new CandidatEcritMain("Awa Diallo", "awa@exemple.test", 6);
            assertTrue(List.of(a).contains(b));
        }

        @Test
        @DisplayName("toString n'est pas redefini : la sortie est inutilisable")
        void toStringParDefaut() {
            String texte = new CandidatEcritMain("Awa", "a@b", 1).toString();
            assertTrue(texte.startsWith("fr.portail.pieges.CandidatEcritMain@"), texte);
        }
    }

    @Nested
    @DisplayName("heritage contre composition")
    class Heritage {

        @ParameterizedTest(name = "addAll de {0} elements : le compteur double")
        @ValueSource(ints = {1, 2, 3, 10})
        void lHeritageCompteDouble(int combien) {
            var sac = new SacCompteur<Integer>();
            sac.addAll(java.util.stream.IntStream.range(0, combien).boxed().toList());
            assertEquals(combien * 2, sac.ajoutes(),
                    "PIECE A CONVICTION : HashSet.addAll appelle add");
            assertEquals(combien, sac.size());
        }

        @ParameterizedTest(name = "addAll de {0} elements : la composition compte juste")
        @ValueSource(ints = {1, 2, 3, 10})
        void laCompositionCompteJuste(int combien) {
            var sac = new SacParComposition<Integer>();
            sac.addAll(java.util.stream.IntStream.range(0, combien).boxed().toList());
            assertEquals(combien, sac.ajoutes());
            assertEquals(combien, sac.size());
        }

        @Test
        @DisplayName("un add direct compte juste des deux cotes")
        void lAddDirectEstJuste() {
            var parHeritage = new SacCompteur<String>();
            parHeritage.add("cv.pdf");
            var parComposition = new SacParComposition<String>();
            parComposition.add("cv.pdf");
            assertEquals(1, parHeritage.ajoutes());
            assertEquals(1, parComposition.ajoutes());
        }

        @Test
        @DisplayName("la composition ne rend pas son interieur")
        void laCompositionNeFuitPas() {
            var sac = new SacParComposition<String>();
            sac.add("cv.pdf");
            assertThrows(UnsupportedOperationException.class,
                    () -> sac.contenu().add("intrus.pdf"));
            assertEquals(1, sac.size());
        }
    }

    @Nested
    @DisplayName("encapsulation")
    class Encapsulation {

        @Test
        @DisplayName("la liste rendue par le dossier ne se modifie pas")
        void laListeRendueEstFermee() {
            var dossier = Dossier.exemple();
            var evenements = dossier.evenements();
            assertThrows(UnsupportedOperationException.class,
                    () -> evenements.add(new Evenement.Triee(
                            java.time.LocalDate.now(), false, "intrus")));
        }

        @Test
        @DisplayName("le dossier garde le meme nombre d'evenements")
        void leDossierResteIntact() {
            var dossier = Dossier.exemple();
            int avant = dossier.evenements().size();
            try {
                dossier.evenements().add(new Evenement.Triee(
                        java.time.LocalDate.now(), false, "intrus"));
            } catch (UnsupportedOperationException attendu) {
                // c'est le comportement voulu
            }
            assertEquals(avant, dossier.evenements().size());
        }

        @Test
        @DisplayName("ajouter passe par la methode, et l'ordre est conserve")
        void ajouterPasseParLaMethode() {
            var dossier = Dossier.exemple();
            int avant = dossier.evenements().size();
            dossier.ajouter(new Evenement.Triee(
                    java.time.LocalDate.of(2026, 4, 1), false, "doublon"));
            assertEquals(avant + 1, dossier.evenements().size());
            assertEquals(java.time.LocalDate.of(2026, 4, 1),
                    dossier.evenements().getLast().date());
        }
    }

    @Nested
    @DisplayName("la hierarchie scellee")
    class Scellee {

        @Test
        @DisplayName("Evenement permet exactement quatre cas")
        void quatreCas() {
            var permis = Evenement.class.getPermittedSubclasses();
            assertEquals(4, permis.length);
            assertEquals(List.of("Deposee", "Triee", "Entretien", "Decision"),
                    java.util.Arrays.stream(permis).map(Class::getSimpleName).toList());
        }

        @Test
        @DisplayName("les quatre cas sont des records")
        void tousDesRecords() {
            for (var cas : Evenement.class.getPermittedSubclasses()) {
                assertTrue(cas.isRecord(), cas.getSimpleName() + " devrait etre un record");
            }
        }

        @Test
        @DisplayName("un switch exhaustif sans default compile")
        void lExhaustiviteCompile() {
            assertTrue(Compilateur.compiler("Extrait", SWITCH_COMPLET).compile());
        }

        @Test
        @DisplayName("le meme switch avec un cas en moins est refuse")
        void leCasManquantEstRefuse() {
            var verdict = Compilateur.compiler("Extrait", SWITCH_INCOMPLET);
            assertTrue(verdict.refuse());
            assertTrue(verdict.mentionne("does not cover all possible input values"),
                    verdict.erreurs().toString());
        }

        @Test
        @DisplayName("ajouter un `default` fait compiler le switch incomplet")
        void leDefaultBaillonne() {
            String avecDefaut = SWITCH_INCOMPLET.replace("    };",
                    "      default -> 0;\n    };");
            assertTrue(Compilateur.compiler("Extrait", avecDefaut).compile(),
                    "c'est l'avertissement du chapitre : le default masque l'oubli");
        }

        @Test
        @DisplayName("ajouter un cas au permits casse le switch qui etait complet")
        void ajouterUnCasCasseLeSwitch() {
            String avecTriangle = SWITCH_COMPLET
                    .replace("permits Cercle, Rectangle",
                            "permits Cercle, Rectangle, Triangle")
                    .replace("  record Rectangle(double l, double h) implements Forme {}",
                            "  record Rectangle(double l, double h) implements Forme {}\n"
                            + "  record Triangle(double b, double h) implements Forme {}");
            assertTrue(Compilateur.compiler("Extrait", avecTriangle).refuse());
        }

        @Test
        @DisplayName("une classe hors du permits ne peut pas implementer l'interface")
        void horsDuPermits() {
            String intruse = SWITCH_COMPLET.replace("}\n",
                    "  record Losange(double d) implements Forme {}\n}\n");
            var verdict = Compilateur.compiler("Extrait", intruse);
            assertTrue(verdict.refuse());
            assertTrue(verdict.mentionne("not allowed to extend sealed")
                    || verdict.mentionne("may not have Forme as a supertype")
                    || verdict.mentionne("is not allowed in the sealed interface"),
                    verdict.erreurs().toString());
        }
    }

    private static final String SWITCH_COMPLET = """
            public class Extrait {
              sealed interface Forme permits Cercle, Rectangle {}
              record Cercle(double rayon) implements Forme {}
              record Rectangle(double l, double h) implements Forme {}
              static double aire(Forme f) {
                return switch (f) {
                  case Cercle c    -> Math.PI * c.rayon() * c.rayon();
                  case Rectangle r -> r.l() * r.h();
                };
              }
            }
            """;

    private static final String SWITCH_INCOMPLET = SWITCH_COMPLET.replace(
            "      case Rectangle r -> r.l() * r.h();\n", "");
}
