package fr.portail.application;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicLong;

/**
 * La file d'evaluation : on accepte vite, on evalue apres.
 *
 * <p>Un test technique prend plusieurs secondes — le demarrage du bac a
 * sable, l'execution, la comparaison. Bloquer une requete HTTP pendant ce
 * temps a trois defauts, et le troisieme est le pire :
 *
 * <ul>
 *   <li>le candidat regarde une page qui tourne ;</li>
 *   <li>un fil d'execution du serveur est immobilise par soumission ;</li>
 *   <li>et un pic de soumissions — la fin d'une campagne de recrutement —
 *       epuise le pool avant d'epuiser le bac a sable. L'application tombe
 *       pour une raison qui n'a rien a voir avec elle.</li>
 * </ul>
 *
 * <p>⚠️ La file borne le nombre d'evaluations SIMULTANEES. C'est elle, et
 * non le bac a sable, qui empeche mille soumissions de lancer mille
 * processus. Le bac a sable protege de ce qu'une soumission fait ; la file
 * protege de leur NOMBRE.
 */
public final class FileDEvaluation implements AutoCloseable {

    public enum Etat { EN_ATTENTE, TERMINEE }

    public record Suivi(long candidature, Etat etat, Note note) {
    }

    private final ServiceEvaluation service;
    private final ExecutorService ouvriers;
    private final Map<Long, Suivi> suivis = new ConcurrentHashMap<>();
    private final AtomicLong acceptees = new AtomicLong();

    public FileDEvaluation(ServiceEvaluation service, int ouvriers) {
        this.service = service;
        this.ouvriers = Executors.newFixedThreadPool(ouvriers);
    }

    /** Accepte la soumission et rend la main tout de suite. */
    public Suivi soumettre(long candidature, String code,
                           List<String> attendus) {
        acceptees.incrementAndGet();
        Suivi enAttente = new Suivi(candidature, Etat.EN_ATTENTE, null);
        suivis.put(candidature, enAttente);
        ouvriers.submit(() -> {
            Note note = service.evaluer(candidature, code, attendus);
            suivis.put(candidature, new Suivi(candidature, Etat.TERMINEE, note));
        });
        return enAttente;
    }

    public Suivi consulter(long candidature) {
        return suivis.get(candidature);
    }

    public long acceptees() {
        return acceptees.get();
    }

    public boolean attendreLaFin(long secondes) throws InterruptedException {
        ouvriers.shutdown();
        return ouvriers.awaitTermination(secondes, TimeUnit.SECONDS);
    }

    @Override
    public void close() {
        ouvriers.shutdownNow();
    }
}
