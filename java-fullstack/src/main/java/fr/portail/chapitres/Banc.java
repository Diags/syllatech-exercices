package fr.portail.chapitres;

import fr.portail.ApplicationPortail;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Map;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * Le banc d'essai : un VRAI portail Spring Boot, sur un port libre.
 *
 * <p>Les chapitres demarrent ici l'application complete — base H2, Flyway,
 * chaine de filtres, controleurs — et l'interrogent avec le client HTTP du
 * JDK. Rien n'est simule.
 *
 * <p>⚠️ LE PORT EST CHOISI PAR LE SYSTEME (`server.port=0`). Un port fixe
 * ferait echouer deux executions paralleles et, pire, ferait passer un
 * chapitre en se connectant a un service laisse ouvert par la fois
 * precedente.
 */
public final class Banc implements AutoCloseable {

    private final ConfigurableApplicationContext contexte;
    private final HttpClient client;
    private final String url;

    private Banc(ConfigurableApplicationContext contexte) {
        this.contexte = contexte;
        this.client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10)).build();
        this.url = "http://localhost:" + contexte.getEnvironment()
                .getProperty("local.server.port", "0");
    }

    public static Banc demarrer() {
        return new Banc(new SpringApplicationBuilder(ApplicationPortail.class)
                .properties(Map.of("server.port", "0",
                                   "spring.main.banner-mode", "off",
                                   "logging.level.root", "WARN",
                                   "logging.level.org.springframework.boot", "WARN"))
                .run());
    }

    public String url() {
        return url;
    }

    public <T> T bean(Class<T> type) {
        return contexte.getBean(type);
    }

    /** Une reponse HTTP : le statut, et le corps. */
    public record Reponse(int statut, String corps) {

        public boolean reussi() {
            return statut >= 200 && statut < 300;
        }
    }

    public Reponse get(String chemin, String jeton) {
        return envoyer(requete(chemin, jeton).GET().build());
    }

    public Reponse post(String chemin, String corps, String jeton) {
        return envoyer(requete(chemin, jeton)
                .header("Content-Type", "application/json")
                .POST(HttpRequest.BodyPublishers.ofString(corps))
                .build());
    }

    public Reponse postAvecEnTete(String chemin, String corps, String nom,
                                  String valeur) {
        return envoyer(HttpRequest.newBuilder(URI.create(url + chemin))
                .header("Content-Type", "application/json")
                .header(nom, valeur)
                .POST(HttpRequest.BodyPublishers.ofString(corps))
                .build());
    }

    public Reponse supprimer(String chemin, String jeton) {
        return envoyer(requete(chemin, jeton).DELETE().build());
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

    private Reponse envoyer(HttpRequest requete) {
        try {
            HttpResponse<String> reponse =
                    client.send(requete, HttpResponse.BodyHandlers.ofString());
            return new Reponse(reponse.statusCode(), reponse.body());
        } catch (java.io.IOException erreur) {
            throw new IllegalStateException("appel HTTP impossible", erreur);
        } catch (InterruptedException interruption) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("appel interrompu", interruption);
        }
    }

    /** Se connecte et rend l'access token. */
    public String connecter(String identifiant, String motDePasse) {
        Reponse reponse = post("/api/auth/connexion",
                """
                {"identifiant":"%s","motDePasse":"%s"}
                """.formatted(identifiant, motDePasse), null);
        if (!reponse.reussi()) {
            throw new IllegalStateException(
                    "connexion refusee : " + reponse.statut());
        }
        return entre(reponse.corps(), "\"accessToken\":\"", "\"");
    }

    /** Une extraction minuscule : le projet n'a pas besoin d'un client JSON. */
    public static String entre(String texte, String debut, String fin) {
        int depart = texte.indexOf(debut);
        if (depart < 0) {
            return "";
        }
        depart += debut.length();
        int arrivee = texte.indexOf(fin, depart);
        return arrivee < 0 ? texte.substring(depart)
                : texte.substring(depart, arrivee);
    }

    @Override
    public void close() {
        contexte.close();
    }
}
