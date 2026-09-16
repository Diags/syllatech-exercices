package fr.portail.chapitres;

import fr.portail.application.FileDEvaluation;
import fr.portail.application.Note;
import fr.portail.application.ServiceEvaluation;
import fr.portail.commun.Banc;
import java.util.List;

/**
 * Chapitre 5 — Integrer au flux du job portal.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Integrer
 * </pre>
 *
 * <p>L'application orchestre et note ; elle n'execute rien. Ce chapitre
 * mesure les deux formes d'appel — bloquante et en file — et montre ce que
 * la comparaison des sorties ne doit jamais faire.
 */
public final class Chapitre5Integrer {

    private Chapitre5Integrer() {
    }

    private static final List<String> ATTENDUS =
            List.of("bonjour", "42", "fini");

    private static final String SUJET = """
            # Le sujet : ecrire « bonjour », puis 21 + 21, puis « fini ».
            """;

    public static void main(String[] args) throws Exception {
        try (Banc banc = Banc.durci(4, 48)) {
            ServiceEvaluation service =
                    new ServiceEvaluation(banc.url(), banc.mesures());

            System.out.println("""
                    1. L'APPLICATION APPELLE, ELLE N'EXECUTE PAS
                    """);
            System.out.printf("   Le runner ecoute sur %s%n", banc.url());
            System.out.println("""
                       Cote application, tout le danger tient en trois
                       lignes :

                          var resultat = runner.post().uri("/execute")
                                .body(DemandeExecution.script(code))
                                .retrieve().body(Resultat.class);

                       Elle ne connait ni ProcessBuilder, ni conteneur, ni
                       politique. Elle connait une URL et deux records.
                    """);

            System.out.printf("   %-26s %-10s %-12s %s%n",
                              "SOUMISSION", "NOTE", "DUREE", "MENTION");
            for (var essai : List.of(
                    entree("solution juste", """
                            ecrire bonjour
                            somme 21 21
                            ecrire fini
                            """),
                    entree("solution partielle", """
                            ecrire bonjour
                            somme 20 20
                            ecrire fini
                            """),
                    entree("solution qui boucle", """
                            ecrire bonjour
                            boucle
                            """),
                    entree("solution curieuse", """
                            ecrire bonjour
                            lire_fichier "/etc/passwd"
                            """))) {
                long depart = System.nanoTime();
                Note note = service.evaluer(1, essai.code(), ATTENDUS);
                long millisecondes = (System.nanoTime() - depart) / 1_000_000;
                // ⚠️ La colonne NOTE est vide quand la soumission est
                // ECARTEE : la comparaison a bien tourne (la « solution
                // curieuse » avait une ligne juste), mais son resultat n'est
                // pas une note. C'est une decision metier, pas un score.
                System.out.printf("   %-26s %-10s %-12s %s%n",
                        essai.titre(),
                        note.ecartee() ? "—"
                                : note.reussis() + "/" + note.attendus(),
                        millisecondes + " ms", note.mention());
            }

            System.out.println("""

                       La troisieme a coute le delai complet ; la quatrieme a
                       ete ECARTEE, pas notee. Distinguer « mauvaise
                       solution » de « tentative d'acces » est une decision
                       metier, et elle se prend dans l'application — le
                       runner, lui, se contente de rendre un code de sortie.
                    """);

            System.out.println("""
                    2. LA COMPARAISON NE DOIT RIEN EVALUER
                    """);
            System.out.println("""
                       La notation compare des CHAINES, ligne a ligne :

                          lignes.get(rang).strip().equals(attendus.get(rang))

                       ⚠️ La tentation serait d'etre « souple » — evaluer une
                       expression, passer la sortie a un moteur de modeles,
                       la concatener dans une requete de notation. Chacune de
                       ces trois facilites rend au candidat l'execution qu'on
                       venait de lui retirer, et cette fois DANS le processus
                       qui detient la base et les secrets.

                       Tout le travail du chapitre 3 s'annule sur une ligne
                       de commodite.
                    """);

            System.out.println("""
                    3. LA MESURE : BLOQUER OU METTRE EN FILE
                    """);
            String qui_boucle = "ecrire bonjour\nboucle\n";
            long depart = System.nanoTime();
            service.evaluer(2, qui_boucle, ATTENDUS);
            long bloquant = (System.nanoTime() - depart) / 1_000_000;

            try (FileDEvaluation file = new FileDEvaluation(service, 2)) {
                long depuis = System.nanoTime();
                var suivi = file.soumettre(3, qui_boucle, ATTENDUS);
                long enFile = (System.nanoTime() - depuis) / 1_000_000;

                System.out.printf("      appel bloquant   : %5d ms  → %s%n",
                                  bloquant, "reponse finale");
                System.out.printf("      mise en file     : %5d ms  → %s%n",
                                  enFile, suivi.etat());
                System.out.printf("      rapport          : x%d%n",
                                  Math.max(1, bloquant / Math.max(1, enFile)));

                file.attendreLaFin(20);
                var termine = file.consulter(3);
                System.out.printf("      apres traitement : %s, %s%n",
                        termine.etat(), termine.note().mention());
            }

            System.out.println("""

                       Le candidat recoit « evaluation en cours » tout de
                       suite, et le resultat arrive quand il arrive.

                       ⚠️ Et le vrai argument n'est pas le confort : c'est
                       que la file BORNE le nombre d'evaluations
                       simultanees. Sans elle, un pic de soumissions — la fin
                       d'une campagne de recrutement — lance autant de
                       processus qu'il y a de soumissions, et c'est le noeud
                       qui tombe. Le bac a sable protege de ce qu'UNE
                       soumission fait ; la file protege de leur NOMBRE.
                    """);

            System.out.println("""
                    4. CE QUE L'APPLICATION NE DOIT JAMAIS RECUPERER
                    """);
            System.out.println("""
                       Un droit, un seul, et il se donne par accident :
                       l'acces au bac a sable. Si l'application peut lancer
                       des conteneurs — parce qu'on a monte le socket Docker
                       « pour simplifier » — alors la compromission de
                       l'application vaut la compromission du noeud, et tout
                       le decoupage n'aura servi a rien.

                       Le socket Docker se monte dans le RUNNER, jamais dans
                       l'application. Et meme la, c'est un privilege enorme :
                       en production, on lui prefere un service d'execution
                       distant, ou un `Job` Kubernetes cree par un compte de
                       service qui ne peut creer QUE des Jobs, dans un seul
                       espace de noms.
                    """);
        }
    }

    private record Essai(String titre, String code) {
    }

    private static Essai entree(String titre, String code) {
        return new Essai(titre, SUJET + code);
    }
}
