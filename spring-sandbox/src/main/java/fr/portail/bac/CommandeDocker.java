package fr.portail.bac;

import java.util.ArrayList;
import java.util.List;

/**
 * La ligne {@code docker run} durcie du cours — construite, et AUDITEE.
 *
 * <p>⚠️ CE PROJET NE LANCE PAS DOCKER. Il n'y a ni demon, ni image, ni
 * gVisor : un cours ne peut pas les exiger. Ce que cette classe apporte est
 * la seule chose qui se verifie hors ligne, et c'est deja beaucoup — la
 * ligne de commande EXACTE, et un audit qui dit, drapeau par drapeau,
 * quelle porte chacun ferme et laquelle reste ouverte quand il manque.
 *
 * <p>C'est utilisable tel quel : l'audit tourne sur VOTRE commande, dans
 * votre integration continue, et il echoue quand quelqu'un retire un
 * drapeau « juste pour deboguer ».
 */
public final class CommandeDocker {

    private final List<String> arguments = new ArrayList<>();
    private String image = "runner:jobportal-script";

    private CommandeDocker() {
    }

    /** La commande du cours : tout ce qui ferme une porte est present. */
    public static CommandeDocker durcie() {
        return new CommandeDocker()
                // >>> depart: fermer les onze portes de AuditDurcissement.PORTES, qui dit pour chacune ce qu'elle coute en restant ouverte
                //     .avec("--rm");
                .avec("--rm")                       // sandbox jetable
                .avec("--interactive")              // le script arrive par stdin
                .avec("--runtime=runsc")            // gVisor : noyau en espace utilisateur
                .avec("--network=none")             // exfiltration
                .avec("--read-only")                // porte derobee
                .avec("--user", "1000:1000")        // pas de root
                .avec("--cap-drop=ALL")             // privileges
                .avec("--security-opt", "no-new-privileges")
                .avec("--pids-limit=64")            // fork bomb
                .avec("--memory=256m")              // saturation memoire
                .avec("--cpus=0.5")                 // saturation CPU
                .avec("--tmpfs", "/tmp:rw,noexec,nosuid,size=16m");
                // <<<
    }

    /**
     * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
     *
     * <p>La commande qu'on trouve dans la moitie des tutoriels. Elle
     * fonctionne, elle execute le code, et elle n'isole a peu pres rien.
     */
    public static CommandeDocker naive() {
        return new CommandeDocker().avec("--rm");
    }

    public CommandeDocker avec(String... morceaux) {
        arguments.addAll(List.of(morceaux));
        return this;
    }

    public CommandeDocker image(String image) {
        this.image = image;
        return this;
    }

    /**
     * La commande complete, telle qu'un {@code ProcessBuilder} la prendrait.
     *
     * <p>⚠️ LE SCRIPT N'Y EST PAS, ET C'EST DELIBERE. Il arrive sur l'ENTREE
     * STANDARD du conteneur — d'ou le drapeau {@code --interactive}. Passe en
     * argument, il serait lisible dans {@code ps}, dans
     * {@code docker inspect} et dans les journaux du demon : c'est-a-dire
     * archive, sur un noeud partage, par du code qu'on ne controle pas.
     */
    public List<String> argv() {
        List<String> commande = new ArrayList<>();
        commande.add("docker");
        commande.add("run");
        commande.addAll(arguments);
        commande.add(image);
        return List.copyOf(commande);
    }

    /**
     * ⚠️ PIECE A CONVICTION — NE PAS « REPARER ».
     *
     * <p>La forme qu'on voit partout : le script concatene dans la ligne de
     * commande. Elle fonctionne, et elle publie le code du candidat dans la
     * table des processus du noeud.
     */
    public List<String> argvAvecLeScriptEnClair(String script) {
        List<String> commande = new ArrayList<>(argv());
        commande.add("-c");
        commande.add(script);
        return List.copyOf(commande);
    }

    public List<String> drapeaux() {
        return List.copyOf(arguments);
    }

    public String image() {
        return image;
    }

    @Override
    public String toString() {
        return String.join(" ", argv());
    }
}
