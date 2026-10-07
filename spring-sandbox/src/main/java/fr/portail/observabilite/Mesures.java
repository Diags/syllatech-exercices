package fr.portail.observabilite;

import fr.portail.runner.Resultat;
import io.micrometer.core.instrument.Counter;
import io.micrometer.core.instrument.MeterRegistry;
import io.micrometer.core.instrument.Timer;
import java.util.concurrent.TimeUnit;

/**
 * Ce qu'on regarde en production — et ce n'est pas le taux de reussite.
 *
 * <p>Quatre compteurs, et chacun repond a une question d'exploitation :
 * <ul>
 *   <li>la DUREE dit si le bac a sable ralentit ;</li>
 *   <li>le taux de DELAI DEPASSE dit si les soumissions bouclent — et une
 *       hausse brutale signale une attaque par epuisement ;</li>
 *   <li>les REFUS DE PRIVILEGE comptent les tentatives d'evasion. Zero est
 *       normal ; un pic ne l'est pas ;</li>
 *   <li>les ECHECS DE DEMARRAGE disent que le bac a sable lui-meme est en
 *       panne, ce qui est un incident distinct d'un code candidat fautif.</li>
 * </ul>
 *
 * <p>⚠️ Le troisieme est le seul qui soit specifique a un bac a sable, et
 * c'est le plus utile : il transforme « quelqu'un a peut-etre essaye » en
 * une serie temporelle sur laquelle on met une alerte.
 */
public final class Mesures {

    /** Le code de sortie que l'interprete rend sur un refus de privilege. */
    public static final int CODE_REFUS = 77;

    private final Timer duree;
    private final Counter delaisDepasses;
    private final Counter refusDePrivilege;
    private final Counter echecsDeDemarrage;
    private final Counter executions;

    public Mesures(MeterRegistry registre) {
        this.duree = Timer.builder("sandbox.execution.duree")
                .description("duree d'une execution de code candidat")
                .register(registre);
        this.delaisDepasses = Counter.builder("sandbox.delai.depasse")
                .description("executions tuees par le delai dur")
                .register(registre);
        this.refusDePrivilege = Counter.builder("sandbox.privilege.refuse")
                .description("tentatives d'acces refusees par la politique")
                .register(registre);
        this.echecsDeDemarrage = Counter.builder("sandbox.demarrage.echec")
                .description("le bac a sable n'a pas demarre")
                .register(registre);
        this.executions = Counter.builder("sandbox.execution.total")
                .register(registre);
    }

    public void enregistrer(Resultat resultat) {
        executions.increment();
        duree.record(resultat.millisecondes(), TimeUnit.MILLISECONDS);
        // >>> depart: incrementer les trois compteurs d'incident — delai depasse, refus de privilege (code 77) et echec de DEMARRAGE (code -2) — et rien du tout pour un code candidat fautif
        if (resultat.delaiDepasse()) {
            delaisDepasses.increment();
        }
        if (resultat.codeSortie() == CODE_REFUS) {
            refusDePrivilege.increment();
        }
        if (resultat.codeSortie() == -2) {
            echecsDeDemarrage.increment();
        }
        // <<<
    }

    public long executions() {
        return (long) executions.count();
    }

    public long delaisDepasses() {
        return (long) delaisDepasses.count();
    }

    public long refusDePrivilege() {
        return (long) refusDePrivilege.count();
    }

    public long echecsDeDemarrage() {
        return (long) echecsDeDemarrage.count();
    }

    public double dureeMoyenneEnMillisecondes() {
        return duree.mean(TimeUnit.MILLISECONDS);
    }

    public double tauxDeDelaiDepasse() {
        long total = executions();
        return total == 0 ? 0.0 : (double) delaisDepasses() / total;
    }
}
