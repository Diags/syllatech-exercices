package fr.portail.runner;

import fr.portail.langage.Interprete;
import fr.portail.langage.Politique;
import java.util.function.Function;

/**
 * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
 *
 * <p>C'est la tentation, et elle fonctionne parfaitement : on prend le code
 * du candidat, on l'evalue dans la JVM de l'application, on rend la sortie.
 * Dix lignes, aucune dependance, aucun conteneur a deployer.
 *
 * <p>C'est aussi la pire chose qu'on puisse faire, et le chapitre 1 le
 * MESURE plutot que de l'affirmer :
 *
 * <ul>
 *   <li>le script lit les fichiers du serveur — pas les siens, les VOTRES ;</li>
 *   <li>il lit les proprietes de l'application, donc ses secrets. Ce n'est
 *       pas une faille : c'est le fonctionnement normal d'un moteur de
 *       script, qui recoit le contexte de l'appelant ;</li>
 *   <li>il ouvre des connexions sortantes avec l'identite du serveur ;</li>
 *   <li>et une boucle sans fin fige le fil d'execution qui l'a appele —
 *       il n'y a personne pour le tuer, puisque le tueur serait dans le
 *       meme processus.</li>
 * </ul>
 *
 * <p>⚠️ ET AUCUN REGLAGE NE RATTRAPE CELA. Le {@code SecurityManager} de
 * Java, qui promettait exactement ce service, est deprecie depuis Java 17 et
 * desactive depuis Java 24 : une politique interne au processus ne resiste
 * pas a du code qui s'execute dans ce processus. La reponse n'est pas un
 * meilleur reglage, c'est une frontiere de processus.
 */
public final class ExecutionDansLaJvm implements ServiceExecution {

    private final Function<String, String> lecteurDeSecrets;

    public ExecutionDansLaJvm(Function<String, String> lecteurDeSecrets) {
        this.lecteurDeSecrets = lecteurDeSecrets;
    }

    @Override
    public Resultat lancer(DemandeExecution demande) {
        long depart = System.nanoTime();
        // ⚠️ `toutPermis` n'est pas une negligence de ce projet : c'est ce
        // qu'un moteur de script offre. Il n'y a rien a configurer, parce
        // qu'il n'y a rien qui refuse.
        Interprete interprete = new Interprete(Politique.toutPermis(),
                                               lecteurDeSecrets);
        Interprete.Trace trace = interprete.executer(demande.code());
        long millisecondes = (System.nanoTime() - depart) / 1_000_000;
        return new Resultat(trace.sortie(), trace.erreurs(), trace.code(),
                            false, millisecondes);
    }

    @Override
    public String nom() {
        return "dans la JVM de l'application";
    }
}
