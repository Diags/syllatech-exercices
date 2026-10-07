package fr.portail.chapitres;

import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionDansLaJvm;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import java.util.List;

/**
 * Chapitre 3 — Piloter un bac a sable depuis Java.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre3Piloter
 * </pre>
 *
 * <p>Le runner n'execute pas : il LANCE, et il TUE. Ce chapitre imprime la
 * ligne de commande reelle, puis mesure les trois garde-fous — le delai dur,
 * la memoire bornee, la sortie plafonnee.
 */
public final class Chapitre3Piloter {

    private Chapitre3Piloter() {
    }

    public static void main(String[] args) {
        ExecutionEnBacASable bac = new ExecutionEnBacASable(3, 48);

        System.out.println("""
                1. LE RUNNER LANCE UN PROCESSUS, IL N'EXECUTE RIEN
                """);
        System.out.println("   La commande, telle que ProcessBuilder la recoit :\n");
        for (String morceau : bac.commande()) {
            String court = morceau.length() > 68
                    ? morceau.substring(0, 34) + " … " + morceau.substring(
                            morceau.length() - 28)
                    : morceau;
            System.out.printf("      %s%n", court);
        }
        System.out.println("""

                   Chaque drapeau ferme une porte, exactement comme ceux de
                   `docker run` au chapitre 4 :

                      -Xmx48m                      la saturation memoire
                      -XX:+ExitOnOutOfMemoryError  une mort nette, pas un agonie
                      -XX:ActiveProcessorCount=1   un seul cœur, pas la machine
                      -cp <classes du bac>         ni Spring, ni le metier

                   Et l'environnement est VIDE : `environment().clear()`.
                   Aucune variable de l'application ne traverse — c'est une
                   ligne, et elle empeche un jeton d'API de passer sans qu'on
                   y pense.
                """);

        System.out.println("""
                2. LA MESURE : LE DELAI DUR
                """);
        Resultat boucle = bac.lancer(DemandeExecution.script(
                "ecrire je pars en boucle\nboucle"));
        System.out.printf("   Soumission : « boucle »  (delai regle a 3 s)%n%n");
        System.out.printf("      delai depasse : %b%n", boucle.delaiDepasse());
        System.out.printf("      code de sortie: %d%n", boucle.codeSortie());
        System.out.printf("      duree mesuree : %d ms%n", boucle.millisecondes());
        System.out.printf("      erreurs       : %s%n", boucle.erreurs().strip());
        System.out.println("""

                   `waitFor(3, SECONDS)` rend faux, `destroyForcibly()` tue.
                   Le processus disparait, et le runner rend la main.

                   ⚠️ `destroy()` — sans le « Forcibly » — envoie SIGTERM et
                   demande poliment. Un script hostile n'ecoute pas. C'est la
                   difference entre un garde-fou et une suggestion.

                   ⚠️ Et comparez au chapitre 1 : dans la JVM de
                   l'application, la meme boucle occupe un fil d'execution
                   pour toujours. `Thread.stop` est supprime depuis Java 20 ;
                   il n'existe AUCUNE facon d'arreter un fil qui ne coopere
                   pas. Le seul tueur qui fonctionne est le systeme
                   d'exploitation.
                """);

        System.out.println("""
                3. LA MESURE : LA MEMOIRE BORNEE
                """);
        Resultat memoire = bac.lancer(DemandeExecution.script("memoire 400"));
        System.out.println("   Soumission : « memoire 400 »  (-Xmx48m)\n");
        System.out.printf("      code de sortie: %d%n", memoire.codeSortie());
        System.out.printf("      delai depasse : %b%n", memoire.delaiDepasse());
        System.out.printf("      erreurs       : %s%n",
                memoire.erreurs().isBlank() ? "(aucune)"
                        : Chapitre1Menace.premiereLigne(memoire.erreurs()));
        System.out.println("""

                   L'enfant meurt, le runner vit. Aucune politique n'est
                   intervenue : c'est la JVM enfant qui touche son plafond.

                   ⚠️ Et remarquez la ligne « erreurs » : elle est VIDE.
                   `-XX:+ExitOnOutOfMemoryError` termine le processus a
                   l'instant du manque, sans laisser le `catch` s'executer ni
                   la moindre trace sortir. C'est voulu — une JVM qui manque
                   de memoire passe son temps a ramasser les miettes et
                   devient imprevisible ; mieux vaut une mort nette. Le
                   diagnostic se lit alors dans le CODE DE SORTIE, pas dans
                   un message, et c'est une chose a savoir avant de chercher
                   une pile d'appels qui n'existe pas.
                """);

        System.out.println("""
                4. LA MESURE : LA SORTIE PLAFONNEE
                """);
        Resultat flot = bac.lancer(DemandeExecution.script(
                "ecrire " + "A".repeat(200) + "\n".repeat(1)
                + "ecrire " + "B".repeat(200)));
        Resultat enorme = bac.lancer(DemandeExecution.script(
                ("ecrire " + "X".repeat(500) + "\n").repeat(60)));
        System.out.printf("      sortie courte  : %d caracteres%n",
                          flot.sortie().length());
        System.out.printf("      sortie enorme  : %d caracteres, tronquee : %b%n",
                          enorme.sortie().length(),
                          enorme.sortie().endsWith("(tronque)"));
        System.out.printf("      plafond        : %d%n",
                          fr.portail.langage.Interprete.PLAFOND_DE_SORTIE);
        System.out.println("""

                   ⚠️ La taille de la sortie est choisie par le CANDIDAT.
                   Sans plafond, une soumission de dix millions de lignes
                   sature la memoire du runner — et le plafond doit etre pose
                   avant que la chaine ne traverse HTTP, pas apres.
                """);

        System.out.println("""
                5. CE QUE LA FRONTIERE N'APPORTE PAS
                """);
        var dansLaJvm = new ExecutionDansLaJvm(nom -> "valeur-de-l-application");
        Resultat fuite = dansLaJvm.lancer(
                DemandeExecution.script("secret jobportal.cle-api"));
        Resultat bloque = bac.lancer(
                DemandeExecution.script("secret jobportal.cle-api"));
        System.out.printf("   %-24s %-12s %s%n", "IMPLANTATION", "CODE", "SORTIE");
        System.out.printf("   %-24s %-12d %s%n", "dans la JVM",
                fuite.codeSortie(), fuite.sortie().strip());
        System.out.printf("   %-24s %-12d %s%n", "processus separe",
                bloque.codeSortie(), bloque.erreurs().strip());
        System.out.println("""

                   Le second echoue, et pas pour la raison qu'on croit : la
                   politique refuse, oui — mais meme sans elle, ce processus
                   n'a PAS de contexte Spring a lire. On ne protege pas un
                   tas, on en change.

                   ⚠️ ET VOICI CE QUI MANQUE ENCORE. Un processus separe
                   partage le NOYAU. Une faille du noyau, un appel systeme
                   mal filtre, un montage oublie : la frontiere tombe. C'est
                   pour cela que le cours demande un conteneur durci, et
                   gVisor par-dessus — le chapitre 4 construit cette ligne de
                   commande et l'audite, sans pouvoir la lancer ici.
                """);
        System.out.printf("   (commande du bac a sable : %d arguments)%n",
                          List.copyOf(bac.commande()).size());
    }
}
