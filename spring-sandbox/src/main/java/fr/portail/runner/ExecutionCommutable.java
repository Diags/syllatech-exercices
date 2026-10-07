package fr.portail.runner;

/**
 * Une indirection d'une ligne, et elle sert le cours.
 *
 * <p>Le runner expose UN contrat HTTP. Derriere, l'implantation se change :
 * les chapitres font tourner la MEME requete contre
 * {@link ExecutionDansLaJvm} puis contre {@link ExecutionEnBacASable}, et
 * comparent. Sans cette indirection, il faudrait deux applications, deux
 * ports, et la comparaison perdrait sa force.
 *
 * <p>⚠️ En production, on ne commute rien : le bean est construit une fois,
 * et l'implantation dangereuse n'est meme pas sur le chemin de classes du
 * service deploye.
 */
public final class ExecutionCommutable implements ServiceExecution {

    private volatile ServiceExecution delegue;

    public ExecutionCommutable(ServiceExecution delegue) {
        this.delegue = delegue;
    }

    public void commuter(ServiceExecution nouveau) {
        this.delegue = nouveau;
    }

    public ServiceExecution delegue() {
        return delegue;
    }

    @Override
    public Resultat lancer(DemandeExecution demande) {
        return delegue.lancer(demande);
    }

    @Override
    public String nom() {
        return delegue.nom();
    }
}
