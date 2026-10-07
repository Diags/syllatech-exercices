package fr.portail.domaine;

import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

/**
 * Le dossier d'une candidature : la suite de ses événements.
 *
 * <p>Une classe, pas un record — parce qu'un dossier <em>change</em> : on y
 * ajoute des événements. La distinction est le sujet du chapitre 2 : un
 * record décrit une valeur qui ne bouge pas, une classe décrit une chose
 * qui a une vie.
 */
public final class Dossier {

    private final Candidat candidat;
    private final Offre offre;
    private final List<Evenement> evenements = new ArrayList<>();

    public Dossier(Candidat candidat, Offre offre, LocalDate depot) {
        this.candidat = candidat;
        this.offre = offre;
        evenements.add(new Evenement.Deposee(depot, candidat, offre));
    }

    public Dossier ajouter(Evenement evenement) {
        evenements.add(evenement);
        return this;
    }

    public Candidat candidat() {
        return candidat;
    }

    public Offre offre() {
        return offre;
    }

    /**
     * La liste, <strong>non modifiable</strong>.
     *
     * <p>{@code List.copyOf} et non la liste elle-même : rendre le champ
     * exposerait l'intérieur du dossier, et n'importe quel appelant pourrait
     * y ajouter un événement sans passer par {@link #ajouter}. Le chapitre 3
     * mesure ce que « non modifiable » veut dire exactement — et ce que cela
     * ne veut pas dire.
     */
    public List<Evenement> evenements() {
        return List.copyOf(evenements);
    }

    /** L'issue, si le dossier est clos. */
    public java.util.Optional<Evenement.Issue> issue() {
        for (int i = evenements.size() - 1; i >= 0; i--) {
            if (evenements.get(i) instanceof Evenement.Decision(
                    LocalDate ignore, Evenement.Issue issue, String c)) {
                return java.util.Optional.of(issue);
            }
        }
        return java.util.Optional.empty();
    }

    /** Un dossier de démonstration, complet, pour les chapitres. */
    public static Dossier exemple() {
        var candidat = Candidat.de("Awa Diallo", 6,
                Competence.JAVA, Competence.SPRING, Competence.SQL);
        var offre = Offre.de("OFF-2026-014", "Developpeuse Java", "Lyon",
                4, 52_000, Competence.JAVA, Competence.SPRING);
        return new Dossier(candidat, offre, LocalDate.of(2026, 3, 2))
                .ajouter(new Evenement.Triee(
                        LocalDate.of(2026, 3, 3), true, "6 ans >= 4 ans"))
                .ajouter(new Evenement.Entretien(
                        LocalDate.of(2026, 3, 11), "Karim B.", 17))
                .ajouter(new Evenement.Decision(
                        LocalDate.of(2026, 3, 18), Evenement.Issue.EMBAUCHE,
                        "prise de poste le 2 mai"));
    }
}
