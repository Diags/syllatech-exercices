package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.runner.ApplicationRunner;
import fr.portail.runner.DemandeExecution;
import fr.portail.runner.ExecutionCommutable;
import fr.portail.runner.ExecutionEnBacASable;
import fr.portail.runner.Resultat;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.web.client.RestClient;

/**
 * Le runner, interroge par de VRAIES requetes HTTP.
 *
 * <p>Le contrat d'entree est etroit a dessein — deux champs, deux
 * contraintes. Chaque champ qu'on ajouterait (un chemin, une variable
 * d'environnement, un drapeau) serait une surface d'attaque de plus, et le
 * plus souvent pour une commodite.
 *
 * <p>⚠️ La taille du code est bornee COTE RUNNER. Un controle qui vit chez
 * l'appelant ne protege personne : l'appelant, ici, peut etre compromis.
 */
@SpringBootTest(classes = ApplicationRunner.class,
                webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
                properties = {"spring.main.banner-mode=off",
                              "logging.level.root=WARN",
                              // Le delai de production est de 5 s. Ici, 20 :
                              // le PREMIER demarrage d'une JVM enfant, disques
                              // et caches froids, peut couter plusieurs
                              // secondes, et un refus de privilege ressortirait
                              // alors en « delai depasse ». Un test de CONTRAT
                              // ne doit pas dependre de la vitesse du disque.
                              "jobportal.sandbox.delai-en-secondes=20"})
class RunnerHttpTest {

    @Autowired
    private Environment environnement;

    @Autowired
    private ExecutionCommutable serviceExecution;

    private static boolean bacChauffe;

    private RestClient client;

    @BeforeEach
    void ouvrirLeClient() {
        // Le port est choisi par le systeme (`RANDOM_PORT`) et republie dans
        // l'environnement : un port fixe ferait passer un test en se
        // connectant a un service laisse ouvert par l'execution precedente.
        String port = environnement.getProperty("local.server.port");
        client = RestClient.builder()
                .baseUrl("http://localhost:" + port)
                .build();

        // Une execution a vide, une seule fois : elle paie le demarrage a
        // froid de la JVM enfant, pour qu'aucune assertion ne le paie.
        if (!bacChauffe) {
            executer(DemandeExecution.script("ecrire chauffe"));
            bacChauffe = true;
        }
    }

    /** Le corps, quand on s'attend a un 200. */
    private Resultat executer(DemandeExecution demande) {
        return client.post().uri("/execute").body(demande)
                .retrieve().body(Resultat.class);
    }

    /** Le statut seul, sans lever d'exception sur un 4xx. */
    private HttpStatusCode statut(DemandeExecution demande) {
        return client.post().uri("/execute").body(demande)
                .exchange((requete, reponse) -> reponse.getStatusCode());
    }

    @Test
    @Timeout(120)
    @DisplayName("une soumission honnete traverse HTTP et revient notee")
    void laSoumissionHonnete() {
        Resultat resultat = executer(DemandeExecution.script("""
                ecrire bonjour
                somme 21 21
                """));

        assertThat(resultat).isNotNull();
        assertThat(resultat.sortie().strip().lines())
                .containsExactly("bonjour", "42");
        assertThat(resultat.reussi()).isTrue();
    }

    @Test
    @Timeout(120)
    @DisplayName("le service par defaut est le bac a sable, jamais l'autre")
    void leServiceParDefautEstLeBon() {
        // ⚠️ La verification qui compte : le runner livre par defaut ne doit
        // PAS pouvoir lire les proprietes de l'application. Si quelqu'un
        // changeait le bean pour `ExecutionDansLaJvm`, ce test tomberait.
        Resultat resultat = executer(
                DemandeExecution.script("secret jobportal.cle-api"));

        assertThat(resultat).isNotNull();
        assertThat(resultat.codeSortie()).isEqualTo(77);
        assertThat(resultat.sortie()).isEmpty();

        // Et pourtant la propriete EXISTE bien dans cette application.
        assertThat(environnement.getProperty("jobportal.cle-api"))
                .isEqualTo("sk-secret-de-production-a-ne-jamais-divulguer");
    }

    @Test
    @DisplayName("un code vide est refuse par le contrat, pas par l'interprete")
    void leCodeVideEstRefuse() {
        assertThat(statut(DemandeExecution.script("   ")))
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    @DisplayName("un langage vide est refuse")
    void leLangageVideEstRefuse() {
        assertThat(statut(new DemandeExecution("", "ecrire x")))
                .isEqualTo(HttpStatus.BAD_REQUEST);
    }

    @Test
    @DisplayName("⚠️ un code de 20 001 caracteres est refuse AVANT toute execution")
    void laTailleEstBornee() {
        String enorme = "ecrire " + "A".repeat(20_001);
        long depart = System.nanoTime();
        HttpStatusCode statut = statut(DemandeExecution.script(enorme));
        long millisecondes = (System.nanoTime() - depart) / 1_000_000;

        assertThat(statut).isEqualTo(HttpStatus.BAD_REQUEST);
        // Aucun processus n'a ete lance : la reponse arrive bien avant le
        // temps de demarrage d'une JVM.
        assertThat(millisecondes)
                .as("le refus doit couter moins qu'un demarrage de bac a sable")
                .isLessThan(1_000);
    }

    @Test
    @Timeout(120)
    @DisplayName("la sortie hostile du candidat traverse HTTP telle quelle — a l'application de l'echapper")
    void laSortieHostileTraverse() {
        Resultat resultat = executer(DemandeExecution.script(
                "ecrire <script>alert('vole')</script>"));

        assertThat(resultat).isNotNull();
        // ⚠️ Le runner ne modifie rien : ce serait mentir sur ce que le
        // candidat a produit. L'echappement est la responsabilite de CELUI
        // QUI AFFICHE, et il depend du contexte d'affichage.
        assertThat(resultat.sortie()).contains("<script>");
        assertThat(fr.portail.securite.Sortie.pourAffichage(resultat.sortie()))
                .doesNotContain("<script>")
                .contains("&lt;script&gt;");
    }

    @Test
    @DisplayName("⚠️ le delai dur est une ENTREE DECLAREE, lue dans la configuration")
    void leDelaiVientDeLaConfiguration() {
        // Le principe n'est pas negociable : sans delai, une seule soumission
        // fige le runner. Sa VALEUR, elle, est une decision — cinq secondes
        // pour un test technique, davantage pour une compilation. La coder en
        // dur oblige a redeployer pour la changer, et pousse a la retirer.
        assertThat(serviceExecution.delegue())
                .isInstanceOf(ExecutionEnBacASable.class);
        ExecutionEnBacASable bac =
                (ExecutionEnBacASable) serviceExecution.delegue();

        assertThat(bac.delaiEnSecondes())
                .as("la propriete de ce test doit atteindre le bean")
                .isEqualTo(20);
        assertThat(bac.memoireMaximale())
                .as("non reglee ici : la valeur par defaut s'applique")
                .isEqualTo(48);
        assertThat(bac.commande()).contains("-Xmx48m");
    }
}
