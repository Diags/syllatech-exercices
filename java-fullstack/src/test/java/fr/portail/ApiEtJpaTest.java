package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.api.OffreService;
import fr.portail.domaine.CompteRepository;
import fr.portail.domaine.CompteurDeRequetes;
import fr.portail.domaine.OffreRepository;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.core.env.Environment;

/**
 * L'API et la couche JPA, interrogees pour de vrai : une application Spring
 * Boot complete, une base H2 versionnee par Flyway, et un compteur de SQL.
 */
@SpringBootTest(classes = ApplicationPortail.class,
                webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT,
                properties = {"spring.main.banner-mode=off",
                              "logging.level.root=WARN"})
class ApiEtJpaTest {

    @Autowired
    private Environment environnement;

    @Autowired
    private OffreService service;

    @Autowired
    private OffreRepository offres;

    @Autowired
    private CompteRepository comptes;

    @Autowired
    private CompteurDeRequetes compteur;

    private HttpClient client;
    private String url;

    @BeforeEach
    void ouvrir() {
        client = HttpClient.newHttpClient();
        url = "http://localhost:"
              + environnement.getProperty("local.server.port");
    }

    // -- le schema et les donnees -----------------------------------------

    @Test
    @DisplayName("Flyway a pose le schema et les donnees, Hibernate les a valides")
    void leSchemaEstVersionne() {
        // ⚠️ `ddl-auto=validate` : si une entite derivait du schema, le
        // contexte n'aurait pas demarre et ce test n'existerait pas.
        assertThat(offres.count()).isGreaterThanOrEqualTo(6);
        assertThat(comptes.findByIdentifiant("awa")).isPresent();
        assertThat(comptes.findByIdentifiant("bilal")).isPresent();
    }

    @Test
    @DisplayName("le mot de passe est une empreinte BCrypt de 60 caracteres")
    void leMotDePasseEstUneEmpreinte() {
        String empreinte = comptes.findByIdentifiant("awa").orElseThrow()
                .getMotDePasse();

        assertThat(empreinte).hasSize(60).startsWith("$2");
        assertThat(empreinte)
                .as("jamais le mot de passe en clair")
                .doesNotContain("motdepasse");
    }

    // -- le N+1 ------------------------------------------------------------

    @Test
    @DisplayName("⚠️ LA MESURE : 4 requetes sans `join fetch`, 1 avec")
    void leNPlusUnSeCompte() {
        compteur.demarrer();
        service.listerAvecUnNPlusUn();
        compteur.arreter();
        int sansJointure = compteur.selects().size();

        compteur.demarrer();
        service.lister();
        compteur.arreter();
        int avecJointure = compteur.selects().size();

        // 1 pour la liste, puis une par entreprise DISTINCTE : le cache de
        // premier niveau d'Hibernate deduplique. Sur un catalogue reel ou
        // chaque offre a son entreprise, c'est une requete par ligne.
        assertThat(sansJointure).isEqualTo(4);
        assertThat(avecJointure)
                .as("`join fetch` : une seule requete, quelle que soit la taille")
                .isEqualTo(1);
    }

    @Test
    @DisplayName("les deux facons rendent EXACTEMENT le meme resultat")
    void lesDeuxFaconsSontEquivalentes() {
        // C'est ce qui rend le N+1 si difficile a voir : le resultat est
        // juste. Seul le nombre de requetes change.
        assertThat(service.lister())
                .containsExactlyElementsOf(service.listerAvecUnNPlusUn());
    }

    @Test
    @DisplayName("le nom de la methode est la requete")
    void laRequeteDeriveeDuNom() {
        assertThat(offres.findByTitreContainingIgnoreCase("JAVA"))
                .as("insensible a la casse, comme le nom le promet")
                .hasSize(2);
        assertThat(offres.findByPile("devops")).hasSize(3);
        assertThat(offres.findByPile("cobol")).isEmpty();
    }

    // -- le contrat HTTP ---------------------------------------------------

    @Test
    @Timeout(60)
    @DisplayName("les codes de statut font partie du contrat")
    void lesCodesDeStatut() {
        assertThat(get("/api/offres", null).statusCode()).isEqualTo(200);
        assertThat(get("/api/offres/1", null).statusCode()).isEqualTo(200);
        assertThat(get("/api/offres/999", null).statusCode())
                .as("404, et non 200 avec un corps vide")
                .isEqualTo(404);
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ 401 et 403 ne disent pas la meme chose")
    void quatreCentUnEtQuatreCentTrois() {
        String corps = """
                {"titre":"Dev Go","pile":"devops","salaireEnKiloEuros":55,
                 "entrepriseId":1}""";

        // ⚠️ Sans `authenticationEntryPoint`, Spring Security rend 403 dans
        // les deux cas. Et sans `dispatcherTypeMatchers(ERROR).permitAll()`,
        // le 403 ressort en 401 : le reacheminement vers `/error` retraverse
        // la chaine, cette fois en anonyme.
        assertThat(post("/api/offres", corps, null).statusCode())
                .as("personne n'est identifie : « connecte-toi »")
                .isEqualTo(401);
        assertThat(post("/api/offres", corps, jeton("bilal")).statusCode())
                .as("identifie, mais sans ROLE_RH : « tu n'as pas le droit »")
                .isEqualTo(403);
        assertThat(post("/api/offres", corps, jeton("awa")).statusCode())
                .isEqualTo(201);
    }

    @Test
    @Timeout(60)
    @DisplayName("la validation refuse a la frontiere, en `problem+json`")
    void laValidationEstALaFrontiere() {
        String jetonRh = jeton("awa");

        HttpResponse<String> titreVide = post("/api/offres", """
                {"titre":"","pile":"java","salaireEnKiloEuros":48,"entrepriseId":1}
                """, jetonRh);
        assertThat(titreVide.statusCode()).isEqualTo(400);
        assertThat(titreVide.body())
                .as("le champ fautif est nomme : React peut l'afficher au bon endroit")
                .contains("champs").contains("titre");

        assertThat(post("/api/offres", """
                {"titre":"Dev","pile":"cobol","salaireEnKiloEuros":48,"entrepriseId":1}
                """, jetonRh).body()).contains("pile inconnue");

        // ⚠️ Celle-ci passe la validation : « cette entreprise existe-t-elle »
        // est une regle METIER, pas une contrainte de format.
        assertThat(post("/api/offres", """
                {"titre":"Dev","pile":"java","salaireEnKiloEuros":48,"entrepriseId":999}
                """, jetonRh).statusCode()).isEqualTo(404);
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ le JSON rendu est celui du DTO, jamais celui de l'entite")
    void leDtoEstLeContrat() {
        String corps = get("/api/offres/1", null).body();

        assertThat(corps).contains("\"entreprise\":\"Clauger\"", "\"ville\":\"Lyon\"");
        assertThat(corps)
                .as("ni la structure de la jointure, ni les noms de colonnes")
                .doesNotContain("entreprise_id").doesNotContain("salaire_ke");
    }

    @Test
    @Timeout(60)
    @DisplayName("⚠️ un access token survit a la desactivation de son compte")
    void leJetonSurvitALaDesactivation() {
        // ⚠️ UN COMPTE DEDIE, cree pour ce test. Desactiver `bilal`
        // marcherait aussi — et casserait tous les tests qui s'y connectent
        // ensuite, dans un ordre que JUnit ne garantit pas.
        var encodeur = new org.springframework.security.crypto.bcrypt
                .BCryptPasswordEncoder();
        comptes.save(new fr.portail.domaine.Compte(
                "ephemere", encodeur.encode("motdepasse"), "ROLE_USER"));

        String jetonEphemere = jeton("ephemere");
        assertThat(get("/api/moi", jetonEphemere).statusCode()).isEqualTo(200);

        var compte = comptes.findByIdentifiant("ephemere").orElseThrow();
        compte.desactiver();
        comptes.save(compte);

        // On ne peut pas revoquer ce qu'on ne stocke pas. Ce n'est pas un
        // defaut : c'est la definition d'un jeton auto-porteur — d'ou une
        // duree de vie courte.
        assertThat(get("/api/moi", jetonEphemere).statusCode())
                .as("l'ancien jeton fonctionne toujours")
                .isEqualTo(200);
        assertThat(post("/api/auth/connexion", """
                {"identifiant":"ephemere","motDePasse":"motdepasse"}
                """, null).statusCode())
                .as("mais on ne peut plus en obtenir de nouveau")
                .isEqualTo(401);
    }

    // -- outillage ---------------------------------------------------------

    private String jeton(String identifiant) {
        HttpResponse<String> reponse = post("/api/auth/connexion", """
                {"identifiant":"%s","motDePasse":"motdepasse"}
                """.formatted(identifiant), null);
        assertThat(reponse.statusCode()).isEqualTo(200);
        String corps = reponse.body();
        int debut = corps.indexOf("\"accessToken\":\"") + 15;
        return corps.substring(debut, corps.indexOf('"', debut));
    }

    private HttpResponse<String> get(String chemin, String jeton) {
        return envoyer(requete(chemin, jeton).GET().build());
    }

    private HttpResponse<String> post(String chemin, String corps, String jeton) {
        return envoyer(requete(chemin, jeton)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(corps)).build());
    }

    private HttpRequest.Builder requete(String chemin, String jeton) {
        HttpRequest.Builder constructeur =
                HttpRequest.newBuilder(URI.create(url + chemin))
                        .timeout(Duration.ofSeconds(20));
        if (jeton != null) {
            constructeur.header("Authorization", "Bearer " + jeton);
        }
        return constructeur;
    }

    private HttpResponse<String> envoyer(HttpRequest requete) {
        try {
            return client.send(requete, HttpResponse.BodyHandlers.ofString());
        } catch (java.io.IOException erreur) {
            throw new IllegalStateException(erreur);
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException(interruption);
        }
    }
}
