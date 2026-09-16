package fr.portail.observabilite;

import java.util.function.Supplier;

/**
 * Un disjoncteur minuscule — parce qu'un bac a sable tombe, lui aussi.
 *
 * <p>Le cas a couvrir n'est pas « le code du candidat echoue » : c'est
 * « le demon de conteneurs ne repond plus ». Sans disjoncteur, chaque
 * soumission attend le delai complet avant d'echouer, les fils
 * d'execution du runner s'accumulent, et la panne du bac a sable devient
 * la panne de l'application.
 *
 * <p>⚠️ Ce disjoncteur ne compte QUE les echecs de DEMARRAGE et les delais
 * depasses — jamais un code de sortie non nul. Un candidat dont la solution
 * plante est un evenement normal ; le compter comme une panne ouvrirait le
 * circuit sur du trafic parfaitement sain.
 */
public final class Disjoncteur {

    public enum Etat { FERME, OUVERT }

    private final int seuil;
    private int echecsConsecutifs;
    private Etat etat = Etat.FERME;

    public Disjoncteur(int seuil) {
        this.seuil = seuil;
    }

    public Etat etat() {
        return etat;
    }

    public int echecsConsecutifs() {
        return echecsConsecutifs;
    }

    /**
     * @param appel ce qu'on protege
     * @param repli ce qu'on rend quand le circuit est ouvert
     * @param estUnePanne ce qui compte comme une panne de l'INFRASTRUCTURE
     */
    public <T> T appeler(Supplier<T> appel, Supplier<T> repli,
                         java.util.function.Predicate<T> estUnePanne) {
        // TODO : rendre le repli SANS appeler tant que le circuit est ouvert, et l'ouvrir apres `seuil` pannes CONSECUTIVES (un succes remet le compteur a zero)
        return appel.get();
    }

    /** Ce que ferait la fenetre « demi-ouverte » apres un delai. */
    public void reessayer() {
        etat = Etat.FERME;
        echecsConsecutifs = 0;
    }
}
