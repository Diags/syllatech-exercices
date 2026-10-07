package fr.portail.runner;

/**
 * Executer du code non fiable. Deux implantations, et tout le cours est
 * dans leur difference :
 *
 * <ul>
 *   <li>{@link ExecutionDansLaJvm} — la tentation. Elle marche, elle est
 *       rapide, et elle donne au candidat tout ce que votre application
 *       peut faire ;</li>
 *   <li>{@link ExecutionEnBacASable} — un processus separe, avec une
 *       memoire bornee, un delai dur et une politique qui n'accorde rien.
 *       </li>
 * </ul>
 */
public interface ServiceExecution {

    Resultat lancer(DemandeExecution demande);

    /** Le nom affiche par les chapitres et les metriques. */
    String nom();
}
