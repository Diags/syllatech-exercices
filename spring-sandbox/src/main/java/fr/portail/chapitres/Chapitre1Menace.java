package fr.portail.chapitres;

import fr.portail.application.ServiceEvaluation;
import fr.portail.commun.Banc;
import fr.portail.runner.Resultat;
import java.util.List;

/**
 * Chapitre 1 — Le besoin et la menace cote Spring.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre1Menace
 * </pre>
 *
 * <p>On demarre un VRAI runner Spring Boot dont le service d'execution est
 * celui qu'il ne faut jamais ecrire — le code du candidat tourne dans la JVM
 * de l'application — et on lui envoie trois soumissions hostiles par HTTP.
 * Ce chapitre n'affirme rien : il imprime ce qui revient.
 */
public final class Chapitre1Menace {

    private Chapitre1Menace() {
    }

    public static void main(String[] args) {
        try (Banc banc = Banc.dansLaJvm()) {
            ServiceEvaluation service = new ServiceEvaluation(banc.url(), null);
            System.out.println("""
                    1. LE BESOIN EST REEL, ET LE CODE RECU NE L'EST PAS
                    """);
            System.out.printf(
                    "   Le runner tourne sur %s, et son service d'execution%n",
                    banc.url());
            System.out.println("   est « dans la JVM de l'application ».\n");
            System.out.println("""
                       Le besoin : un test technique. Le candidat envoie sa
                       solution, l'application la fait tourner et la note.
                       La solution honnete fonctionne :
                    """);
            Resultat honnete = service.executer("""
                    ecrire bonjour
                    somme 21 21
                    """);
            imprimer("solution honnete", honnete);

            System.out.println("""

                    2. LA MESURE QUI TRANCHE : CE QUE LE CANDIDAT LIT CHEZ VOUS
                    """);

            Resultat secret = service.executer("secret jobportal.cle-api");
            System.out.println("   Soumission : « secret jobportal.cle-api »\n");
            imprimer("lecture d'une propriete", secret);
            System.out.printf(
                    "      la valeur reelle de la propriete : %s%n",
                    banc.propriete("jobportal.cle-api"));
            System.out.println("""

                       ⚠️ C'est la meme chaine. Le code du candidat vient de
                       lire un secret de l'application — et ce n'est pas une
                       faille : c'est le fonctionnement NORMAL d'un moteur de
                       script, qui recoit le contexte de celui qui l'appelle.
                    """);

            Resultat fichier = service.executer("lire_fichier \"pom.xml\"");
            System.out.println("   Soumission : « lire_fichier \"pom.xml\" »\n");
            System.out.printf("      code de sortie : %d%n", fichier.codeSortie());
            System.out.printf("      premiere ligne lue : %s%n",
                    premiereLigne(fichier.sortie()));
            System.out.println("""

                       Le chemin est relatif au repertoire de travail du
                       SERVEUR. Rien n'empeche « /etc/passwd », le fichier de
                       configuration, ou le magasin de cles.
                    """);

            Resultat sortante = service.executer("connexion \"127.0.0.1\" "
                                                 + banc.port());
            System.out.printf(
                    "   Soumission : « connexion 127.0.0.1 %d »%n%n",
                    banc.port());
            imprimer("connexion sortante", sortante);
            System.out.println("""

                       Avec l'identite du serveur, depuis son reseau. Un
                       candidat peut donc atteindre ce que votre application
                       atteint : une base interne, un service de metadonnees,
                       une API partenaire.
                    """);

            System.out.println("""

                    3. ET AUCUN REGLAGE DE LA JVM NE RATTRAPE CELA
                    """);
            System.out.println("""
                       Le reflexe serait de chercher une option. Il n'y en a
                       pas :

                          • un chargeur de classes restreint se contourne par
                            reflexion, par desserialisation, par un gadget de
                            bibliotheque ;
                          • et rien, dans la JVM, ne borne la memoire ou le
                            temps d'un FIL d'execution : `Thread.stop` est
                            supprime depuis Java 20, et une boucle sans fin
                            occupe un fil jusqu'a l'arret du serveur ;
                          • quant au `SecurityManager`, qui promettait
                            exactement ce service — demandons-le a CETTE
                            JVM plutot que de l'affirmer :
                    """);
            imprimerLeRefusDuSecurityManager();
            System.out.println("""

                       Sa desactivation (JEP 486, Java 24) n'est pas un
                       retrait de fonctionnalite : c'est l'aveu qu'une
                       politique interne au processus ne resiste pas a du code
                       qui s'execute DANS ce processus. L'API existe encore,
                       elle refuse simplement de servir.

                       La reponse n'est donc pas un meilleur reglage. C'est
                       une FRONTIERE DE PROCESSUS — et c'est le chapitre 3.
                    """);

            System.out.println("""
                    4. CE QUE L'APPLICATION AURAIT DU FAIRE
                    """);
            System.out.println("""
                       Ne pas executer. Deleguer a un service dedie,
                       sacrifiable, qui n'a acces ni a la base, ni aux
                       secrets, ni au reseau interne — c'est le chapitre 2.

                       Et la regle qui resume tout : le code non fiable ne
                       s'execute JAMAIS dans le processus qui detient quelque
                       chose a perdre.
                    """);
            System.out.printf("   (assertions de la solution honnete : %s)%n",
                    List.of("bonjour", "42").equals(
                            List.of(honnete.sortie().strip().split("\\R")))
                            ? "conformes" : "non conformes");
        }
    }

    /**
     * Le refus, demande a la JVM qui tourne.
     *
     * <p>⚠️ Beaucoup de documentations disent le `SecurityManager`
     * « supprime ». Il ne l'est pas : la classe existe toujours, et c'est
     * son INSTALLATION qui est refusee depuis Java 24 (JEP 486). La nuance
     * compte, parce qu'un code qui appelle encore `getSecurityManager()`
     * compile, tourne, et recoit `null` — sans la moindre erreur.
     */
    @SuppressWarnings("removal")
    private static void imprimerLeRefusDuSecurityManager() {
        System.out.printf("      java %s%n", Runtime.version());
        try {
            System.setSecurityManager(new SecurityManager());
            System.out.println("      setSecurityManager  : accepte — "
                               + "cette JVM est anterieure a Java 24");
        } catch (Throwable refus) {
            System.out.printf("      setSecurityManager  : %s%n",
                              refus.getClass().getSimpleName());
            System.out.printf("                            « %s »%n",
                              refus.getMessage());
        }
        System.out.printf("      getSecurityManager  : %s%n",
                          System.getSecurityManager());
    }

    static void imprimer(String titre, Resultat resultat) {
        System.out.printf("      %-26s code=%d  delai=%b%n",
                titre, resultat.codeSortie(), resultat.delaiDepasse());
        if (!resultat.sortie().isBlank()) {
            System.out.printf("      sortie  : %s%n",
                    resultat.sortie().strip());
        }
        if (!resultat.erreurs().isBlank()) {
            System.out.printf("      erreurs : %s%n",
                    resultat.erreurs().strip());
        }
    }

    static String premiereLigne(String texte) {
        String[] lignes = texte.strip().split("\\R");
        return lignes.length == 0 ? "" : lignes[0];
    }
}
