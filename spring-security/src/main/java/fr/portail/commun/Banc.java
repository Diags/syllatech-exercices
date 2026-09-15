package fr.portail.commun;

import fr.portail.PortailApplication;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * Le banc d'essai : le portail, démarré sur un port libre.
 *
 * <p>Les chapitres parlent à l'application avec le client HTTP du JDK, et non
 * avec un client Spring. La raison est le chapitre 3 : pour montrer ce que
 * CORS fait, il faut envoyer un en-tête {@code Origin} à la main et lire les
 * en-têtes de la réponse tels qu'ils sortent — y compris une requête
 * {@code OPTIONS} de <em>preflight</em>. Un client de haut niveau range tout
 * cela pour vous, et c'est précisément ce qu'on veut voir.
 */
public final class Banc implements AutoCloseable {

    private static final String[] SILENCE = {
        "logging.level.root=WARN",
        "logging.level.org.springframework.boot.diagnostics=OFF",
        // Le chapitre 1 declenche EXPRES une panne pour montrer ce que le
        // client recoit. Tomcat journalise la trace en ERROR ; elle ne dit
        // rien de plus que la mesure, et elle la noie.
        "logging.level.org.apache.catalina.core.ContainerBase=OFF",
    };

    private final ConfigurableApplicationContext contexte;

    private final int port;

    private final HttpClient client = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            // On ne suit pas les redirections : une redirection vers une page
            // de connexion EST une reponse, et le chapitre 1 la mesure.
            .followRedirects(HttpClient.Redirect.NEVER)
            .build();

    private Banc(ConfigurableApplicationContext contexte) {
        this.contexte = contexte;
        this.port = Integer.parseInt(
                contexte.getEnvironment().getProperty("local.server.port", "0"));
    }

    public static Banc demarrer(String... proprietes) {
        var construction = new SpringApplicationBuilder(PortailApplication.class)
                .properties("server.port=0")
                .properties(SILENCE)
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false);
        var arguments = new java.util.ArrayList<String>();
        for (var propriete : proprietes) {
            arguments.add("--" + propriete);
        }
        return new Banc(construction.run(arguments.toArray(String[]::new)));
    }

    public ConfigurableApplicationContext contexte() {
        return contexte;
    }

    public <T> T bean(Class<T> type) {
        return contexte.getBean(type);
    }

    public String adresse() {
        return "http://localhost:" + port;
    }

    /** Un GET, avec les en-têtes qu'on veut, et rien de plus. */
    public Reponse obtenir(String chemin, String... entetes) {
        return envoyer("GET", chemin, null, entetes);
    }

    public Reponse obtenirAvecJeton(String chemin, String jeton) {
        return obtenir(chemin, "Authorization", "Bearer " + jeton);
    }

    public Reponse poster(String chemin, String json, String... entetes) {
        var avecType = new java.util.ArrayList<String>(
                java.util.List.of("Content-Type", "application/json"));
        avecType.addAll(java.util.List.of(entetes));
        return envoyer("POST", chemin, json, avecType.toArray(String[]::new));
    }

    /** Une requête {@code OPTIONS} de preflight, comme un navigateur en fait. */
    public Reponse preflight(String chemin, String origine, String methode) {
        return envoyer("OPTIONS", chemin, null,
                "Origin", origine,
                "Access-Control-Request-Method", methode,
                "Access-Control-Request-Headers", "authorization");
    }

    private Reponse envoyer(String methode, String chemin, String corps,
                            String... entetes) {
        try {
            var construction = HttpRequest.newBuilder()
                    .uri(URI.create(adresse() + chemin))
                    .timeout(Duration.ofSeconds(20));
            for (int i = 0; i + 1 < entetes.length; i += 2) {
                construction.header(entetes[i], entetes[i + 1]);
            }
            construction.method(methode, corps == null
                    ? HttpRequest.BodyPublishers.noBody()
                    : HttpRequest.BodyPublishers.ofString(corps));
            var reponse = client.send(construction.build(),
                    HttpResponse.BodyHandlers.ofString());
            var utiles = new LinkedHashMap<String, String>();
            for (var nom : java.util.List.of("Access-Control-Allow-Origin",
                    "Access-Control-Allow-Methods", "Access-Control-Allow-Headers",
                    "Access-Control-Max-Age", "Set-Cookie", "WWW-Authenticate",
                    "Content-Type", "Vary")) {
                reponse.headers().firstValue(nom)
                        .ifPresent(valeur -> utiles.put(nom, valeur));
            }
            // ⚠️ TOUS les `Set-Cookie`, et non le premier. Une reponse de la
            // chaine de session en pose deux — JSESSIONID et XSRF-TOKEN — et
            // le chapitre 3 a besoin du second. Une carte en aurait perdu un.
            var cookies = reponse.headers().allValues("Set-Cookie");
            return new Reponse(reponse.statusCode(), reponse.body(),
                    Map.copyOf(utiles), java.util.List.copyOf(cookies));
        } catch (java.io.IOException | InterruptedException erreur) {
            if (erreur instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            throw new IllegalStateException(
                    "echec de la requete " + methode + " " + chemin, erreur);
        }
    }

    /** Ce qu'une requête a rendu. */
    public record Reponse(int code, String corps, Map<String, String> entetes,
                          java.util.List<String> cookies) {

        /** La valeur d'un cookie posé par cette réponse, s'il y en a un. */
        public String cookie(String nom) {
            for (var pose : cookies) {
                if (pose.startsWith(nom + "=")) {
                    return pose.split(";")[0].substring(nom.length() + 1);
                }
            }
            return "";
        }

        public boolean contient(String fragment) {
            return corps != null && corps.contains(fragment);
        }

        public String entete(String nom) {
            return entetes.getOrDefault(nom, "(absent)");
        }

        /** Une valeur de JSON plat, sans bibliothèque. */
        public String valeur(String champ) {
            if (corps == null) {
                return "";
            }
            var motif = java.util.regex.Pattern.compile(
                    "\"" + champ + "\"\\s*:\\s*\"([^\"]*)\"");
            var trouve = motif.matcher(corps);
            return trouve.find() ? trouve.group(1) : "";
        }

        public String apercu(int largeur) {
            if (corps == null) {
                return "";
            }
            String plat = corps.replaceAll("\\s+", " ").strip();
            return plat.length() <= largeur ? plat
                    : plat.substring(0, largeur - 3) + "...";
        }
    }

    @Override
    public void close() {
        contexte.close();
    }
}
