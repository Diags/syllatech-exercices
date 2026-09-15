package fr.portail;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import fr.portail.domaine.Candidat;
import fr.portail.domaine.Competence;
import fr.portail.domaine.Offre;
import fr.portail.tri.Selection;
import java.util.List;
import java.util.TreeMap;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * L'exercice.
 *
 * <p>Sur la branche {@code depart}, ces tests <strong>échouent</strong> :
 * les quatre méthodes marquées de {@code Selection} y sont vides. Les faire
 * passer est le travail demandé — et l'énoncé est ici, pas dans un
 * paragraphe.
 */
class SelectionTest {

    private static final Offre OFFRE = Offre.de(
            "OFF-2026-014", "Developpeuse Java", "Lyon", 4, 52_000,
            Competence.JAVA, Competence.SPRING);

    private static final List<Candidat> VIVIER = List.of(
            Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING, Competence.SQL),
            Candidat.de("Karim Bensaid", 3, Competence.JAVA, Competence.SPRING),
            Candidat.de("Lea Marchand", 9, Competence.JAVA, Competence.SQL),
            Candidat.de("Tom Nkosi", 1, Competence.REACT),
            Candidat.de("Ines Roux", 5, Competence.JAVA, Competence.SPRING),
            Candidat.de("Malik Sy", 12, Competence.JAVA, Competence.SPRING,
                    Competence.KUBERNETES));

    @Test
    @DisplayName("retenus ne garde que ceux qui satisfont l'offre")
    void retenusFiltre() {
        var noms = Selection.retenus(VIVIER, OFFRE).stream()
                .map(Candidat::prenom).toList();
        assertEquals(List.of("Malik", "Awa", "Ines"), noms,
                "Karim manque d'experience, Lea de Spring, Tom des deux");
    }

    @Test
    @DisplayName("retenus trie du plus experimente au moins")
    void retenusTrie() {
        var annees = Selection.retenus(VIVIER, OFFRE).stream()
                .map(Candidat::anneesExperience).toList();
        assertEquals(List.of(12, 6, 5), annees);
    }

    @Test
    @DisplayName("a experience egale, retenus trie par nom")
    void retenusDepartageParLeNom() {
        var exAequo = List.of(
                Candidat.de("Zoe Alba", 6, Competence.JAVA, Competence.SPRING),
                Candidat.de("Awa Diallo", 6, Competence.JAVA, Competence.SPRING));
        assertEquals(List.of("Awa Diallo", "Zoe Alba"),
                Selection.retenus(exAequo, OFFRE).stream().map(Candidat::nom).toList());
    }

    @Test
    @DisplayName("retenus rend une liste vide si personne ne convient")
    void retenusPeutEtreVide() {
        var trop = Offre.de("OFF-999", "Architecte", "Lyon", 30, 90_000,
                Competence.JAVA);
        assertTrue(Selection.retenus(VIVIER, trop).isEmpty());
    }

    @ParameterizedTest(name = "{0} obtient {1} points")
    @CsvSource({"Awa Diallo, 26", "Malik Sy, 44", "Lea Marchand, 25",
                "Ines Roux, 23", "Karim Bensaid, 20", "Tom Nkosi, 0"})
    @DisplayName("le score compte les competences exigees et l'experience en plus")
    void leScore(String nom, int attendu) {
        var candidat = VIVIER.stream().filter(c -> c.nom().equals(nom))
                .findFirst().orElseThrow();
        assertEquals(attendu, Selection.score(candidat, OFFRE));
    }

    @Test
    @DisplayName("le score ne descend jamais sous zero")
    void leScoreResteePositif() {
        var debutant = Candidat.de("Nouvelle Venue", 0);
        assertEquals(0, Selection.score(debutant, OFFRE));
    }

    @Test
    @DisplayName("une competence non exigee ne rapporte rien")
    void lesCompetencesHorsSujet() {
        var avec = Candidat.de("Avec Docker", 4, Competence.DOCKER);
        var sans = Candidat.de("Sans Rien", 4);
        assertEquals(Selection.score(sans, OFFRE), Selection.score(avec, OFFRE));
    }

    @Test
    @DisplayName("classement rend les meilleurs, dans l'ordre")
    void leClassement() {
        assertEquals(List.of("Malik Sy", "Awa Diallo", "Lea Marchand"),
                Selection.classement(VIVIER, OFFRE, 3));
    }

    @Test
    @DisplayName("un candidat peut etre 3e au classement ET refuse")
    void leClassementNEstPasLeVerdict() {
        // Lea a neuf ans d'experience et pas Spring : son anciennete la hisse
        // au classement, l'absence d'une competence EXIGEE l'ecarte. Les deux
        // methodes repondent a deux questions differentes, et melanger les
        // deux est l'erreur classique d'un moteur de tri de CV.
        assertTrue(Selection.classement(VIVIER, OFFRE, 3).contains("Lea Marchand"));
        assertTrue(Selection.motifsDeRefus(VIVIER, OFFRE).containsKey("Lea Marchand"));
        assertTrue(Selection.retenus(VIVIER, OFFRE).stream()
                .noneMatch(c -> c.nom().equals("Lea Marchand")));
    }

    @Test
    @DisplayName("classement ne rend jamais plus que demande")
    void leClassementEstBorne() {
        assertEquals(1, Selection.classement(VIVIER, OFFRE, 1).size());
        assertEquals(VIVIER.size(), Selection.classement(VIVIER, OFFRE, 99).size());
        assertTrue(Selection.classement(VIVIER, OFFRE, 0).isEmpty());
    }

    @Test
    @DisplayName("classement inclut ceux qui ne conviennent pas : c'est un classement, pas un filtre")
    void leClassementNeFiltrePas() {
        assertTrue(Selection.classement(VIVIER, OFFRE, 99).contains("Tom Nkosi"));
    }

    @Test
    @DisplayName("parCompetence compte chaque competence du vivier")
    void lesCompetencesSontComptees() {
        var comptes = Selection.parCompetence(VIVIER);
        assertEquals(5L, comptes.get("Java"));
        assertEquals(4L, comptes.get("Spring"));
        assertEquals(2L, comptes.get("SQL"));
        assertEquals(1L, comptes.get("React"));
        assertEquals(1L, comptes.get("Kubernetes"));
    }

    @Test
    @DisplayName("parCompetence rend une TreeMap : l'ordre est dit, pas subi")
    void lOrdreEstDit() {
        var comptes = Selection.parCompetence(VIVIER);
        assertTrue(comptes instanceof TreeMap,
                "un HashMap rendrait un ordre stable mais arbitraire");
        assertEquals(List.copyOf(comptes.keySet()),
                comptes.keySet().stream().sorted().toList());
    }

    @Test
    @DisplayName("parCompetence sur un vivier vide rend une carte vide")
    void leVivierVide() {
        assertTrue(Selection.parCompetence(List.of()).isEmpty());
    }

    @Test
    @DisplayName("motifsDeRefus explique chaque ecart")
    void lesMotifsDeRefus() {
        var motifs = Selection.motifsDeRefus(VIVIER, OFFRE);
        assertEquals(3, motifs.size());
        assertEquals("1 an(s) d'experience de moins que demande",
                motifs.get("Karim Bensaid"));
        assertEquals("Spring", motifs.get("Lea Marchand"));
        assertTrue(motifs.get("Tom Nkosi").contains("3 an(s) de moins"),
                motifs.get("Tom Nkosi"));
        assertTrue(motifs.get("Tom Nkosi").contains("Java"),
                motifs.get("Tom Nkosi"));
    }

    @Test
    @DisplayName("les retenus ne figurent pas dans les motifs de refus")
    void lesDeuxListesSontDisjointes() {
        var retenus = Selection.retenus(VIVIER, OFFRE).stream()
                .map(Candidat::nom).toList();
        var refuses = Selection.motifsDeRefus(VIVIER, OFFRE).keySet();
        assertTrue(retenus.stream().noneMatch(refuses::contains));
        assertEquals(VIVIER.size(), retenus.size() + refuses.size());
    }
}
