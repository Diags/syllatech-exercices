package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.domaine.Dossier;
import fr.portail.domaine.Evenement;
import fr.portail.domaine.Offre;
import fr.portail.tri.Journal;
import java.time.LocalDate;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;
import org.junit.jupiter.params.provider.ValueSource;

/** Le modèle du portail, et le journal qui le raconte. */
class DomaineTest {

    @Nested
    @DisplayName("Competence")
    class Competences {

        @ParameterizedTest(name = "{0} a un libelle non vide")
        @EnumSource(Competence.class)
        void chaqueCompetenceEstNommee(Competence competence) {
            assertFalse(competence.libelle().isBlank());
        }

        @Test
        @DisplayName("les libelles sont tous distincts")
        void lesLibellesSontUniques() {
            var libelles = java.util.Arrays.stream(Competence.values())
                    .map(Competence::libelle).collect(java.util.stream.Collectors.toSet());
            assertEquals(Competence.values().length, libelles.size());
        }

        @Test
        @DisplayName("un enum en valeur d'offre rend la faute de frappe impossible")
        void lEnumFermeLeDomaine() {
            assertEquals(8, Competence.values().length);
            assertEquals(Competence.JAVA, Competence.valueOf("JAVA"));
            assertThrows(IllegalArgumentException.class,
                    () -> Competence.valueOf("JAVVA"));
        }
    }

    @Nested
    @DisplayName("Candidat")
    class Candidats {

        @Test
        @DisplayName("la fabrique construit un courriel plausible")
        void laFabrique() {
            var candidat = Candidat.de("Awa Diallo", 6);
            assertEquals("awa.diallo@exemple.test", candidat.courriel());
            assertEquals("Awa", candidat.prenom());
        }

        @Test
        @DisplayName("un nom sans espace est son propre prenom")
        void lePrenomSansEspace() {
            assertEquals("Malik", Candidat.de("Malik", 2).prenom());
        }

        @ParameterizedTest(name = "{0} annees d'experience est accepte")
        @ValueSource(ints = {0, 1, 40})
        void lExperienceValide(int annees) {
            assertEquals(annees, Candidat.de("Test Nom", annees).anneesExperience());
        }

        @Test
        @DisplayName("maitrise repond sur les competences declarees")
        void laMaitrise() {
            var candidat = Candidat.de("Awa Diallo", 6, Competence.JAVA);
            assertTrue(candidat.maitrise(Competence.JAVA));
            assertFalse(candidat.maitrise(Competence.SPRING));
        }

        @Test
        @DisplayName("un candidat sans competence en a un ensemble vide, pas null")
        void lEnsembleVide() {
            assertEquals(Set.of(), Candidat.de("Sans Rien", 0).competences());
        }
    }

    @Nested
    @DisplayName("Offre")
    class Offres {

        @Test
        @DisplayName("manquantes liste ce qui fait defaut")
        void lesManquantes() {
            var offre = Offre.de("OFF-1", "Dev", "Lyon", 3, 50_000,
                    Competence.JAVA, Competence.SPRING);
            var candidat = Candidat.de("Awa Diallo", 5, Competence.JAVA);
            assertEquals(Set.of(Competence.SPRING), offre.manquantes(candidat));
        }

        @Test
        @DisplayName("convient exige les competences ET l'experience")
        void leDoubleCritere() {
            var offre = Offre.de("OFF-1", "Dev", "Lyon", 5, 50_000, Competence.JAVA);
            assertTrue(offre.convient(Candidat.de("Assez", 5, Competence.JAVA)));
            assertFalse(offre.convient(Candidat.de("Trop Jeune", 4, Competence.JAVA)));
            assertFalse(offre.convient(Candidat.de("Sans Java", 9)));
        }

        @Test
        @DisplayName("une offre sans exigence convient a tout le monde")
        void lOffreOuverte() {
            var offre = Offre.de("OFF-2", "Stage", "Lyon", 0, 20_000);
            assertTrue(offre.convient(Candidat.de("Debutante", 0)));
        }

        @Test
        @DisplayName("une reference vide est refusee")
        void laReferenceEstObligatoire() {
            assertThrows(IllegalArgumentException.class,
                    () -> new Offre("", "Dev", "Lyon", 0, 0, Set.of()));
        }

        @Test
        @DisplayName("les competences requises ne se modifient pas apres coup")
        void lesRequisesSontFermees() {
            var offre = Offre.de("OFF-1", "Dev", "Lyon", 0, 0, Competence.JAVA);
            assertThrows(UnsupportedOperationException.class,
                    () -> offre.requises().add(Competence.SPRING));
        }
    }

    @Nested
    @DisplayName("Dossier et Journal")
    class Dossiers {

        @Test
        @DisplayName("le dossier d'exemple a quatre evenements, dans l'ordre")
        void lExemple() {
            var evenements = Dossier.exemple().evenements();
            assertEquals(4, evenements.size());
            assertEquals(Evenement.Deposee.class, evenements.get(0).getClass());
            assertEquals(Evenement.Triee.class, evenements.get(1).getClass());
            assertEquals(Evenement.Entretien.class, evenements.get(2).getClass());
            assertEquals(Evenement.Decision.class, evenements.get(3).getClass());
        }

        @Test
        @DisplayName("les dates ne reculent pas")
        void lesDatesAvancent() {
            LocalDate precedente = null;
            for (var evenement : Dossier.exemple().evenements()) {
                if (precedente != null) {
                    assertFalse(evenement.date().isBefore(precedente),
                            evenement + " precede " + precedente);
                }
                precedente = evenement.date();
            }
        }

        @Test
        @DisplayName("l'issue du dossier d'exemple est une embauche")
        void lIssue() {
            assertEquals(Evenement.Issue.EMBAUCHE,
                    Dossier.exemple().issue().orElseThrow());
            assertEquals(Evenement.Issue.EMBAUCHE,
                    Journal.issue(Dossier.exemple()).orElseThrow());
        }

        @Test
        @DisplayName("un dossier sans decision n'a pas d'issue")
        void sansDecision() {
            var dossier = new Dossier(Candidat.de("Awa Diallo", 6),
                    Offre.de("OFF-1", "Dev", "Lyon", 0, 0),
                    LocalDate.of(2026, 1, 1));
            assertTrue(dossier.issue().isEmpty());
            assertTrue(Journal.issue(dossier).isEmpty());
            assertTrue(Journal.delaiEnJours(dossier).isEmpty());
        }

        @Test
        @DisplayName("le delai se compte du depot a la decision")
        void leDelai() {
            assertEquals(16, Journal.delaiEnJours(Dossier.exemple()).orElseThrow(),
                    "du 2 au 18 mars 2026");
        }

        @Test
        @DisplayName("le journal rend une ligne par evenement")
        void uneLigneParEvenement() {
            var dossier = Dossier.exemple();
            assertEquals(dossier.evenements().size(), Journal.lignes(dossier).size());
        }

        @Test
        @DisplayName("chaque ligne commence par sa date et decrit son cas")
        void lesLignesSontLisibles() {
            var lignes = Journal.lignes(Dossier.exemple());
            assertTrue(lignes.get(0).startsWith("2026-03-02"), lignes.get(0));
            assertTrue(lignes.get(0).contains("Awa Diallo"), lignes.get(0));
            assertTrue(lignes.get(0).contains("OFF-2026-014"), lignes.get(0));
            assertTrue(lignes.get(1).contains("retenue"), lignes.get(1));
            assertTrue(lignes.get(2).contains("17/20"), lignes.get(2));
            assertTrue(lignes.get(3).contains("embauche"), lignes.get(3));
        }

        @Test
        @DisplayName("le texte du journal joint les lignes sans en perdre")
        void leTexteComplet() {
            var dossier = Dossier.exemple();
            assertEquals(Journal.lignes(dossier).size(),
                    Journal.texte(dossier).lines().count());
        }

        @Test
        @DisplayName("decrire traite les quatre cas sans exception")
        void lesQuatreCas() {
            var cas = List.<Evenement>of(
                    new Evenement.Deposee(LocalDate.of(2026, 1, 1),
                            Candidat.de("Awa Diallo", 6),
                            Offre.de("OFF-1", "Dev", "Lyon", 0, 0)),
                    new Evenement.Triee(LocalDate.of(2026, 1, 2), false, "trop court"),
                    new Evenement.Entretien(LocalDate.of(2026, 1, 3), "Karim B.", 12),
                    new Evenement.Decision(LocalDate.of(2026, 1, 4),
                            Evenement.Issue.REFUS, "poste pourvu"));
            for (var evenement : cas) {
                String ligne = Journal.decrire(evenement);
                assertFalse(ligne.isBlank(),
                        "aucun cas ne doit rendre une ligne vide : " + evenement);
                assertTrue(ligne.startsWith(evenement.date().toString()),
                        "chaque ligne commence par sa date : " + ligne);
                assertFalse(ligne.contains("["),
                        "une ligne de journal se lit ; le toString d'un record, non : "
                        + ligne);
            }
        }

        @Test
        @DisplayName("une note d'entretien hors bornes est refusee")
        void laNoteEstBornee() {
            assertThrows(IllegalArgumentException.class,
                    () -> new Evenement.Entretien(LocalDate.now(), "Karim B.", 21));
            assertThrows(IllegalArgumentException.class,
                    () -> new Evenement.Entretien(LocalDate.now(), "Karim B.", -1));
        }

        @ParameterizedTest(name = "l'issue {0} est une fin de dossier")
        @EnumSource(Evenement.Issue.class)
        void chaqueIssueClot(Evenement.Issue issue) {
            var dossier = new Dossier(Candidat.de("Awa Diallo", 6),
                    Offre.de("OFF-1", "Dev", "Lyon", 0, 0),
                    LocalDate.of(2026, 1, 1))
                    .ajouter(new Evenement.Decision(
                            LocalDate.of(2026, 1, 10), issue, "fin"));
            assertEquals(issue, dossier.issue().orElseThrow());
            assertEquals(9, Journal.delaiEnJours(dossier).orElseThrow());
        }
    }
}
