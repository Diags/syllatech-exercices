package fr.portail.commun;

import fr.portail.PortailApplication;
import java.util.Map;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpStatusCode;
import org.springframework.web.client.RestClient;

/**
 * Le banc d'essai des six chapitres : une <strong>vraie</strong> application
 * Spring Boot, démarrée sur un port libre.
 *
 * <p>Aucun chapitre ne simule Spring. Chacun ouvre un {@code Banc}, obtient un
 * contexte complet — conteneur, base H2, chaîne de filtres, serveur Tomcat —
 * et lui envoie des requêtes HTTP réelles. Un 401 mesuré ici est le 401 que
 * le portail renverrait en production.
 *
 * <p>Le port est choisi par le système ({@code server.port=0}) : deux
 * chapitres lancés en même temps ne se gênent pas, et rien ne dépend d'un
 * 8080 libre sur la machine de l'apprenant.
 */
public final class Banc implements AutoCloseable {

    /**
     * Les journaux d'amorcage de Spring noieraient la mesure d'un chapitre.
     * On ne les supprime pas — un avertissement ou une erreur sort toujours.
     */
    private static final String[] SILENCE = {
        "logging.level.root=WARN",
        // Le chapitre 1 construit expres un contexte qui echoue, et
        // affiche lui-meme le verdict. La trace de Spring par-dessus
        // ne dirait rien de plus et couvrirait la mesure.
        "logging.level.org.springframework.context.annotation.AnnotationConfigApplicationContext=OFF",
        "logging.level.org.springframework.boot.diagnostics=OFF",
    };

    /** Combien de bancs ont été ouverts : sert à nommer leur base. */
    private static final java.util.concurrent.atomic.AtomicInteger BANCS =
            new java.util.concurrent.atomic.AtomicInteger();

    private final ConfigurableApplicationContext contexte;

    private final int port;

    private Banc(ConfigurableApplicationContext contexte) {
        this.contexte = contexte;
        this.port = Integer.parseInt(
                contexte.getEnvironment().getProperty("local.server.port", "0"));
    }

    /** Démarre le portail avec le profil {@code dev}, sur un port libre. */
    public static Banc demarrer() {
        return demarrer("dev");
    }

    public static Banc demarrer(String profil, String... proprietes) {
        var construction = new SpringApplicationBuilder(PortailApplication.class)
                .profiles(profil)
                .properties("server.port=0")
                .properties(SILENCE)
                // Un chapitre n'est pas un demarrage de production : la
                // banniere et les journaux d'amorcage noieraient la mesure.
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false);
        // ⚠️ UNE BASE PAR BANC. Le profil dev pointe tous les demarrages
        // vers `jdbc:h2:mem:portail`, et `ddl-auto: create-drop` efface le
        // schema a la fermeture du contexte. Le chapitre 3, qui ouvre un
        // second banc pour comparer deux reglages, detruisait donc la base
        // du premier en le refermant : la suite du chapitre repondait
        // « Table ENTREPRISE not found ». Un nom de base par banc supprime
        // le probleme, et rend aussi les chapitres lancables en parallele.
        String base = "jdbc:h2:mem:portail-" + BANCS.incrementAndGet()
                + ";DB_CLOSE_DELAY=-1";

        // ⚠️ EN ARGUMENTS DE LIGNE DE COMMANDE, ET NON EN `properties()`.
        // `properties()` pose une source de proprietes PAR DEFAUT, celle qui
        // a la plus basse priorite : un document de profil d'application.yml
        // la couvre. Le chapitre 2 demarrait le profil prod en croyant
        // forcer `ddl-auto=create-drop`, et Hibernate lisait `validate` —
        // l'application refusait de demarrer. Un argument `--cle=valeur`,
        // lui, passe devant le fichier.
        var arguments = new java.util.ArrayList<String>();
        arguments.add("--spring.datasource.url=" + base);
        for (var propriete : proprietes) {
            arguments.add("--" + propriete);
        }
        return new Banc(construction.run(arguments.toArray(String[]::new)));
    }

    /**
     * Le portail avec le profil et les propriétés donnés.
     *
     * <p>⚠️ Il n'y a <strong>pas</strong> de variante « sans serveur web ».
     * La première version en avait une, pour épargner une seconde de
     * démarrage au chapitre 1 — et {@code SecurityConfig} refusait de se
     * construire, parce que le bean {@code HttpSecurity} n'existe que dans
     * un contexte web. Le raccourci coûtait donc la moitié de ce que les
     * chapitres mesurent. Tous démarrent la vraie application.
     */
    public ConfigurableApplicationContext contexte() {
        return contexte;
    }

    public Environment environnement() {
        return contexte.getEnvironment();
    }

    public <T> T bean(Class<T> type) {
        return contexte.getBean(type);
    }

    public int port() {
        return port;
    }

    public String adresse() {
        return "http://localhost:" + port;
    }

    /** Un client HTTP anonyme — celui d'un visiteur qui n'a pas de compte. */
    public RestClient anonyme() {
        return RestClient.builder().baseUrl(adresse()).build();
    }

    /** Un client HTTP authentifié en HTTP Basic. */
    public RestClient comme(String utilisateur, String motDePasse) {
        var jeton = java.util.Base64.getEncoder().encodeToString(
                (utilisateur + ":" + motDePasse)
                        .getBytes(java.nio.charset.StandardCharsets.UTF_8));
        return RestClient.builder().baseUrl(adresse())
                .defaultHeader("Authorization", "Basic " + jeton)
                .build();
    }

    /**
     * Un GET qui ne lève jamais : il rend le code et le corps, quels qu'ils
     * soient.
     *
     * <p>Par défaut, {@code RestClient} lève sur un 4xx ou un 5xx. Or ce
     * projet <em>mesure</em> des 401 et des 403 : ce sont des résultats, pas
     * des accidents. D'où ce petit enrobage, présent dans tous les chapitres.
     */
    public static Reponse obtenir(RestClient client, String chemin) {
        return client.get().uri(chemin).exchange((requete, reponse) ->
                new Reponse(reponse.getStatusCode(),
                        lire(reponse.getBody()),
                        entetes(reponse)));
    }

    /** Un POST JSON qui ne lève jamais non plus. */
    public static Reponse poster(RestClient client, String chemin, String json) {
        return client.post().uri(chemin)
                .contentType(org.springframework.http.MediaType.APPLICATION_JSON)
                .body(json)
                .exchange((requete, reponse) ->
                        new Reponse(reponse.getStatusCode(),
                                lire(reponse.getBody()),
                                entetes(reponse)));
    }

    /** Ce qu'une requête a rendu : le code, le corps, les en-têtes utiles. */
    public record Reponse(HttpStatusCode code, String corps,
                          Map<String, String> entetes) {

        public int valeur() {
            return code.value();
        }

        public boolean contient(String fragment) {
            return corps != null && corps.contains(fragment);
        }

        /** Le corps, sur une ligne, tronqué pour tenir dans un tableau. */
        public String apercu(int largeur) {
            if (corps == null) {
                return "";
            }
            String plat = corps.replaceAll("\\s+", " ").strip();
            return plat.length() <= largeur ? plat
                    : plat.substring(0, largeur - 3) + "...";
        }
    }

    private static String lire(java.io.InputStream flux) {
        try (flux) {
            return new String(flux.readAllBytes(),
                    java.nio.charset.StandardCharsets.UTF_8);
        } catch (java.io.IOException erreur) {
            return "";
        }
    }

    private static Map<String, String> entetes(
            org.springframework.http.client.ClientHttpResponse reponse) {
        var utiles = new java.util.LinkedHashMap<String, String>();
        for (var nom : java.util.List.of("Content-Type", "Location",
                "WWW-Authenticate")) {
            String valeur = reponse.getHeaders().getFirst(nom);
            if (valeur != null) {
                utiles.put(nom, valeur);
            }
        }
        return Map.copyOf(utiles);
    }

    @Override
    public void close() {
        contexte.close();
    }
}
