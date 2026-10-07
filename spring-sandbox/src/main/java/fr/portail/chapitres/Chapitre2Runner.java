package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.runner.DemandeExecution;
import fr.portail.runner.Resultat;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.HttpStatusCode;
import org.springframework.web.client.RestClient;

/**
 * Chapitre 2 — Un microservice d'execution dedie.
 *
 * <pre>
 *   mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Runner
 * </pre>
 *
 * <p>Le meme contrat HTTP que le chapitre 1, mais derriere : un processus
 * separe. Ce chapitre mesure ce que le contrat accepte et ce qu'il refuse —
 * parce qu'un contrat etroit est une mesure de securite, pas de la
 * documentation.
 */
public final class Chapitre2Runner {

    private Chapitre2Runner() {
    }

    public static void main(String[] args) {
        try (Banc banc = Banc.durci()) {
            RestClient client = RestClient.builder().baseUrl(banc.url()).build();

            System.out.println("""
                    1. UN SERVICE SEPARE, ET DEUX RECORDS
                    """);
            System.out.printf("   Le runner ecoute sur %s%n%n", banc.url());
            System.out.println("""
                       Le contrat tient en deux enregistrements :

                          record DemandeExecution(String langage, String code)
                          record Resultat(String sortie, String erreurs,
                                          int codeSortie, boolean delaiDepasse,
                                          long millisecondes)

                       Rien d'autre ne traverse la frontiere. Pas de chemin de
                       fichier, pas de variable d'environnement, pas de
                       drapeau : tout ce que l'appelant pourrait ajouter
                       serait une surface d'attaque de plus.
                    """);

            Resultat premier = client.post().uri("/execute")
                    .body(DemandeExecution.script("ecrire bonjour\nsomme 2 40"))
                    .retrieve().body(Resultat.class);
            System.out.println("   Un appel reel :\n");
            Chapitre1Menace.imprimer("POST /execute", premier);
            System.out.printf("      duree mesuree : %d ms%n",
                              premier.millisecondes());

            System.out.println("""

                    2. LE CONTRAT REFUSE AVANT D'EXECUTER
                    """);
            Map<String, DemandeExecution> mauvaises = new LinkedHashMap<>();
            mauvaises.put("code vide", new DemandeExecution("jobportal-script", ""));
            mauvaises.put("langage vide", new DemandeExecution("", "ecrire x"));
            mauvaises.put("code trop long",
                    new DemandeExecution("jobportal-script",
                                         "ecrire x\n".repeat(3000)));

            System.out.printf("   %-18s %s%n", "SOUMISSION", "REPONSE HTTP");
            for (var entree : mauvaises.entrySet()) {
                HttpStatusCode statut = client.post().uri("/execute")
                        .body(entree.getValue())
                        .exchange((requete, reponse) -> reponse.getStatusCode());
                System.out.printf("   %-18s %s%n", entree.getKey(), statut);
            }

            System.out.println("""

                       Les trois sont refusees par la VALIDATION, avant que
                       la moindre ligne ne s'execute. Et la borne de taille
                       est posee ICI, cote runner : un controle qui vit chez
                       celui qui envoie ne protege personne.
                    """);

            System.out.println("""
                    3. « SACRIFIABLE » N'EST PAS UNE FIGURE DE STYLE
                    """);
            System.out.println("""
                       Ce service se deploie autrement que l'application :

                          • sur un noeud DEDIE, marque et isole du reste ;
                          • sous un compte de service qui n'a acces ni a la
                            base du portail, ni a ses secrets, ni a son
                            reseau interne ;
                          • sans variable d'environnement heritee — le
                            processus enfant demarre avec un environnement
                            VIDE, et c'est une ligne de code ;
                          • avec ses propres quotas, pour qu'une saturation
                            reste chez lui.

                       La question a se poser devant chaque acces qu'on lui
                       donne : « si ce service etait compromis ce soir,
                       qu'est-ce que j'aurais perdu ? » Tout ce qui figure
                       dans la reponse est a retirer.
                    """);

            System.out.println("""
                    4. ET LE CONTRAT PROTEGE AUSSI L'APPELANT
                    """);
            Resultat hostile = client.post().uri("/execute")
                    .body(DemandeExecution.script(
                            "ecrire <script>alert('vole')</script>"))
                    .retrieve().body(Resultat.class);
            System.out.println("   Le candidat ecrit du HTML sur sa sortie :\n");
            System.out.printf("      brut      : %s%n", hostile.sortie().strip());
            System.out.printf("      echappe   : %s%n",
                    fr.portail.securite.Sortie.pourAffichage(hostile.sortie())
                            .strip());
            System.out.println("""

                       ⚠️ `Resultat.sortie()` est produit par le code d'un
                       inconnu : c'est une donnee HOSTILE, au meme titre
                       qu'un champ de formulaire. On l'echappe avant tout
                       affichage, on la plafonne, et on ne l'interprete
                       jamais. Le chapitre 4 y revient.
                    """);
        }
    }
}
