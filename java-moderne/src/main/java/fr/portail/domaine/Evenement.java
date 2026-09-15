package fr.portail.domaine;

import java.time.LocalDate;

/**
 * Ce qui arrive à une candidature, au fil du temps.
 *
 * <p>Une interface <strong>scellée</strong> : la liste des cas est close et
 * connue du compilateur. C'est ce qui lui permet de vérifier qu'un
 * {@code switch} les traite <em>tous</em>, et de refuser le code s'il en
 * manque un — sans {@code default}, donc sans le piège classique du
 * {@code default} qui avale silencieusement le cas ajouté l'an prochain.
 *
 * <p>Le chapitre 6 ne se contente pas de l'affirmer : il compile un
 * {@code switch} incomplet pendant l'exécution et affiche le refus du
 * compilateur, mot pour mot.
 */
public sealed interface Evenement
        permits Evenement.Deposee, Evenement.Triee, Evenement.Entretien,
                Evenement.Decision {

    LocalDate date();

    /** La candidature a été déposée. */
    record Deposee(LocalDate date, Candidat candidat, Offre offre)
            implements Evenement {
    }

    /** Un premier tri automatique a été passé (ou non). */
    record Triee(LocalDate date, boolean retenue, String motif)
            implements Evenement {
    }

    /** Un entretien a eu lieu. */
    record Entretien(LocalDate date, String interlocuteur, int note)
            implements Evenement {

        public Entretien {
            if (note < 0 || note > 20) {
                throw new IllegalArgumentException("note hors bornes : " + note);
            }
        }
    }

    /** Le portail a tranché. */
    record Decision(LocalDate date, Issue issue, String commentaire)
            implements Evenement {
    }

    /** Les trois fins possibles d'une candidature. */
    enum Issue { EMBAUCHE, REFUS, DESISTEMENT }
}
