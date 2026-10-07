package fr.portail.application;

import fr.portail.observabilite.Mesures;
import fr.portail.runner.DemandeExecution;
import fr.portail.runner.Resultat;
import fr.portail.securite.Sortie;
import java.util.List;
import org.springframework.web.client.RestClient;

/**
 * Le service de l'APPLICATION : il orchestre, il note, il n'execute rien.
 *
 * <p>C'est la moitie la plus importante du cours, et la moins spectaculaire :
 * l'application ne connait du danger que deux records et une URL. Elle envoie
 * le code au runner, recoit un {@link Resultat}, compare la sortie aux
 * assertions attendues, et range une {@link Note}.
 *
 * <p>⚠️ REGARDEZ CE QUE `comparer` NE FAIT PAS : il n'evalue rien. La sortie
 * du candidat est comparee ligne a ligne a des chaines attendues, jamais
 * passee a un moteur d'expression, jamais concatenee dans une requete. Rendre
 * l'execution au candidat APRES la lui avoir retiree est l'erreur qui annule
 * tout le reste.
 */
public final class ServiceEvaluation {

    private final RestClient runner;
    private final Mesures mesures;

    public ServiceEvaluation(String urlDuRunner, Mesures mesures) {
        this.runner = RestClient.builder().baseUrl(urlDuRunner).build();
        this.mesures = mesures;
    }

    /** Appelle le runner par un VRAI appel HTTP. */
    public Resultat executer(String code) {
        Resultat resultat = runner.post()
                .uri("/execute")
                .body(DemandeExecution.script(code))
                .retrieve()
                .body(Resultat.class);
        if (resultat != null && mesures != null) {
            mesures.enregistrer(resultat);
        }
        return resultat;
    }

    public Note evaluer(long candidature, String code, List<String> attendus) {
        Resultat resultat = executer(code);
        int reussis = comparer(resultat.sortie(), attendus);
        boolean bloquee = resultat.codeSortie() == Mesures.CODE_REFUS;
        return new Note(candidature, reussis, attendus.size(),
                        resultat.delaiDepasse(), bloquee);
    }

    /**
     * Comparaison de chaines, et rien d'autre.
     *
     * <p>⚠️ La tentation serait d'evaluer la sortie pour « etre souple ».
     * Elle rendrait au candidat l'execution qu'on vient de lui retirer, et
     * cette fois dans le processus de l'application.
     */
    public static int comparer(String sortie, List<String> attendus) {
        // TODO : comparer des CHAINES, ligne a ligne, et rien d'autre — jamais d'evaluation, jamais de moteur de modeles, jamais de requete
        return 0;
    }
}
