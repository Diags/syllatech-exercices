package fr.portail.front;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import java.util.function.Consumer;

/**
 * La semantique de {@code useState} et {@code useEffect}, rendue mesurable.
 *
 * <p>POURQUOI CE CODE EXISTE
 * <p>« {@code useEffect} s'execute apres le rendu » et « le tableau de
 * dependances decide de la frequence » sont deux phrases qu'on lit partout
 * et qu'on comprend mal. Ici, on COMPTE : combien de rendus, combien
 * d'executions d'effet, combien de nettoyages — pour chacune des trois
 * formes de dependances.
 *
 * <p>⚠️ CE QUE CE CODE N'EST PAS. Ce n'est ni React, ni un moteur de rendu :
 * c'est la mecanique d'appel que React applique aux hooks, et rien de plus.
 * Il n'y a pas de DOM ici.
 */
public final class Composant {

    /** Les trois formes de dependances, et ce qu'elles veulent dire. */
    public enum Dependances {
        /** {@code useEffect(fn)} — a chaque rendu. */
        AUCUNE,
        /** {@code useEffect(fn, [])} — une seule fois, au montage. */
        VIDES,
        /** {@code useEffect(fn, [x])} — quand `x` change. */
        SURVEILLEES
    }

    private final Dependances forme;
    private final List<Object> journalDesDependances = new ArrayList<>();

    private int rendus;
    private int executionsDEffet;
    private int nettoyages;
    private Object dernieresDependances;
    private boolean monte;

    /** L'etat du composant — ce que `useState` conserve d'un rendu a l'autre. */
    private Object etat;

    public Composant(Dependances forme, Object etatInitial) {
        this.forme = forme;
        this.etat = etatInitial;
    }

    /**
     * Un rendu : la fonction du composant s'execute, PUIS l'effet.
     *
     * <p>⚠️ L'ORDRE EST LE SUJET. L'effet ne s'execute pas pendant le rendu,
     * il s'execute APRES — c'est ce qui permet d'y appeler une API sans
     * bloquer l'affichage, et c'est aussi pourquoi le premier rendu affiche
     * toujours l'etat INITIAL, jamais les donnees chargees.
     */
    public void rendre(Object dependanceSurveillee, Consumer<Composant> effet) {
        rendus++;
        // TODO : decider si l'effet doit s'executer — sans tableau, a chaque rendu ; avec `[]`, au montage seulement ; avec `[x]`, quand `x` a CHANGE
        boolean doitExecuter = true;
        journalDesDependances.add(dependanceSurveillee);
        dernieresDependances = dependanceSurveillee;

        if (doitExecuter) {
            if (monte) {
                // ⚠️ LE NETTOYAGE PRECEDE LA REEXECUTION. Sans lui, un
                // abonnement pose au rendu N survit au rendu N+1 : c'est la
                // fuite la plus courante d'un `useEffect`, et elle se voit
                // comme une requete qui part deux fois, puis quatre.
                nettoyages++;
            }
            executionsDEffet++;
            effet.accept(this);
        }
        monte = true;
    }

    /**
     * {@code setState} : change l'etat, et demande un nouveau rendu.
     *
     * <p>⚠️ Rend {@code false} quand la valeur est IDENTIQUE. React fait de
     * meme : reposer la meme valeur ne declenche pas de rendu. C'est ce qui
     * evite la boucle infinie « je charge dans un effet, je pose l'etat, ce
     * qui relance l'effet » — mais seulement si la valeur est vraiment
     * identique, et un `new ArrayList<>()` ne l'est jamais.
     */
    public boolean poserLEtat(Object nouveau) {
        if (Objects.equals(etat, nouveau)) {
            return false;
        }
        etat = nouveau;
        return true;
    }

    public Object etat() {
        return etat;
    }

    public int rendus() {
        return rendus;
    }

    public int executionsDEffet() {
        return executionsDEffet;
    }

    public int nettoyages() {
        return nettoyages;
    }

    public List<Object> journalDesDependances() {
        return List.copyOf(journalDesDependances);
    }
}
