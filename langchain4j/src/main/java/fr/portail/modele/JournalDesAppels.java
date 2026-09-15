package fr.portail.modele;

import dev.langchain4j.model.chat.listener.ChatModelErrorContext;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.listener.ChatModelRequestContext;
import dev.langchain4j.model.chat.listener.ChatModelResponseContext;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicLong;

/**
 * L'écouteur du chapitre 6 — latence, jetons, erreurs.
 *
 * <p>C'est exactement ce que le cours décrit : un {@link ChatModelListener}
 * s'intercale autour de chaque appel, journalise la requête, la réponse, la
 * latence, et surtout la consommation de jetons. Branché sur Micrometer, cela
 * devient un tableau de bord ; ici, cela devient un tableau imprimé.
 *
 * <p>⚠️ <strong>La date de départ voyage dans les attributs, pas dans un
 * champ.</strong> {@code onRequest} et {@code onResponse} peuvent concerner
 * des appels différents en même temps : stocker l'instant de départ dans
 * l'écouteur donnerait des latences fausses dès deux requêtes simultanées.
 * La {@code Map} d'attributs est là exactement pour cela — elle est propre à
 * chaque appel.
 */
public class JournalDesAppels implements ChatModelListener {

    private static final String DEPART = "depart";

    private final AtomicInteger requetes = new AtomicInteger();
    private final AtomicInteger reponses = new AtomicInteger();
    private final AtomicInteger erreurs = new AtomicInteger();
    private final AtomicLong jetonsEntree = new AtomicLong();
    private final AtomicLong jetonsSortie = new AtomicLong();
    private final AtomicLong latenceTotale = new AtomicLong();

    @Override
    public void onRequest(ChatModelRequestContext contexte) {
        requetes.incrementAndGet();
        contexte.attributes().put(DEPART, System.nanoTime());
    }

    @Override
    public void onResponse(ChatModelResponseContext contexte) {
        reponses.incrementAndGet();
        var depart = contexte.attributes().get(DEPART);
        if (depart instanceof Long debut) {
            latenceTotale.addAndGet((System.nanoTime() - debut) / 1_000_000);
        }
        var usage = contexte.chatResponse().tokenUsage();
        if (usage != null) {
            jetonsEntree.addAndGet(valeur(usage.inputTokenCount()));
            jetonsSortie.addAndGet(valeur(usage.outputTokenCount()));
        }
    }

    @Override
    public void onError(ChatModelErrorContext contexte) {
        erreurs.incrementAndGet();
    }

    private static long valeur(Integer nombre) {
        return nombre == null ? 0 : nombre;
    }

    public int requetes() {
        return requetes.get();
    }

    public int reponses() {
        return reponses.get();
    }

    public int erreurs() {
        return erreurs.get();
    }

    public long jetonsEntree() {
        return jetonsEntree.get();
    }

    public long jetonsSortie() {
        return jetonsSortie.get();
    }

    public long latenceMoyenneMs() {
        int compte = reponses.get();
        return compte == 0 ? 0 : latenceTotale.get() / compte;
    }
}
