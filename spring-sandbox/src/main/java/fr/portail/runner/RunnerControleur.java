package fr.portail.runner;

import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

/**
 * Le runner : un seul point d'entree, un contrat de deux records.
 *
 * <p>⚠️ Ce controleur n'execute rien lui-meme. Il delegue a un
 * {@link ServiceExecution}, et c'est ce qui permet au chapitre 1 de
 * remplacer l'implantation par la mauvaise et de mesurer la difference sans
 * toucher a une ligne d'application.
 *
 * <p>Ce service se deploie sur un noeud dedie, sous un compte de service qui
 * n'a acces ni a la base, ni aux secrets de production. Il est
 * SACRIFIABLE : sa compromission ne doit rien couter d'autre que lui-meme.
 */
@RestController
public class RunnerControleur {

    private final ServiceExecution execution;

    public RunnerControleur(ServiceExecution execution) {
        this.execution = execution;
    }

    @PostMapping("/execute")
    public Resultat executer(@RequestBody @Valid DemandeExecution demande) {
        return execution.lancer(demande);
    }
}
