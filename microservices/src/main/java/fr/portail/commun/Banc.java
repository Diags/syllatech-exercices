package fr.portail.commun;

import fr.portail.annuaire.EurekaServeur;
import fr.portail.passerelle.Passerelle;
import fr.portail.services.OffresService;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.WebApplicationType;
import org.springframework.boot.builder.SpringApplicationBuilder;
import org.springframework.context.ConfigurableApplicationContext;

/**
 * Le banc d'essai : tout l'écosystème, dans une seule JVM.
 *
 * <p>Un vrai serveur Eureka, de vraies instances du service des offres qui
 * s'y enregistrent, et une vraie passerelle qui les trouve par leur nom.
 * Chaque application démarre sur un port libre, et les chapitres les
 * interrogent avec le client HTTP du JDK — donc en vrai HTTP, sur la boucle
 * locale.
 *
 * <p>⚠️ <strong>Les intervalles d'Eureka sont raccourcis, et c'est capital
 * à comprendre.</strong> Par défaut, un service met environ trente secondes
 * à apparaître dans l'annuaire des autres, et une instance morte y reste
 * <strong>quatre-vingt-dix secondes</strong>. Ces valeurs sont raisonnables
 * en production — elles évitent qu'un hoquet réseau vide l'annuaire — mais
 * elles rendraient ces chapitres interminables. Elles sont donc ramenées à
 * la seconde, et le chapitre 2 imprime les deux jeux de valeurs pour que
 * personne ne les confonde.
 *
 * <p>⚠️ <strong>L'auto-préservation est coupée.</strong> Eureka refuse par
 * défaut d'évincer des instances quand trop de cœurs manquent à l'appel : sur
 * un annuaire de trois instances, cela signifie qu'il n'évince jamais rien.
 * C'est un excellent réflexe en production et un piège en développement.
 */
public final class Banc implements AutoCloseable {

    /** Le nom sous lequel le service s'enregistre — la clé de tout. */
    public static final String SERVICE = "offres-service";

    private static final HttpClient CLIENT = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();

    private final ConfigurableApplicationContext eureka;
    private final List<ConfigurableApplicationContext> instances = new ArrayList<>();
    private ConfigurableApplicationContext passerelle;

    private Banc(int nombreDInstances, boolean avecPasserelle) {
        this.eureka = demarrerEureka();
        for (int rang = 0; rang < nombreDInstances; rang++) {
            instances.add(demarrerUneInstance());
        }
        if (avecPasserelle) {
            this.passerelle = demarrerLaPasserelle();
        }
    }

    /** Un annuaire seul — chapitre 1. */
    public static Banc annuaireSeul() {
        return new Banc(0, false);
    }

    /** L'annuaire et des instances — chapitre 2. */
    public static Banc avecInstances(int nombre) {
        return new Banc(nombre, false);
    }

    /** Tout l'écosystème, passerelle comprise — chapitre 3. */
    public static Banc complet(int nombre) {
        return new Banc(nombre, true);
    }

    // ── les demarrages ───────────────────────────────────────────────────

    /**
     * Le port de l'annuaire — fixe, et volontairement.
     *
     * <p>⚠️ Tout le reste de ce projet tourne sur des ports libres, mais pas
     * l'annuaire. Un serveur Eureka est <em>aussi</em> un client de
     * lui-même : il tente de se répliquer vers les pairs listés dans
     * {@code eureka.client.service-url.defaultZone}, et ce réglage doit être
     * connu <strong>avant</strong> le démarrage — donc avant qu'un port
     * aléatoire soit attribué. Sans port fixe, le serveur passe son temps à
     * essayer de joindre le 8761 par défaut, et journalise l'échec.
     *
     * <p>8761 est d'ailleurs le port conventionnel d'Eureka, celui que le
     * cours utilise.
     */
    public static final int PORT_EUREKA = 8761;

    private ConfigurableApplicationContext demarrerEureka() {
        return new SpringApplicationBuilder(EurekaServeur.class)
                .web(WebApplicationType.SERVLET)
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false)
                .run(
                    "--server.port=" + PORT_EUREKA,
                    "--spring.application.name=eureka-serveur",
                    "--eureka.client.service-url.defaultZone=http://localhost:"
                    + PORT_EUREKA + "/eureka/",
                    // Un serveur Eureka est aussi un client : sans cela, il
                    // tente de se repliquer vers un voisin inexistant.
                    "--eureka.client.register-with-eureka=false",
                    "--eureka.client.fetch-registry=false",
                    // ⚠️ Sans cette ligne, Eureka n'evince JAMAIS une
                    // instance morte sur un petit annuaire.
                    "--eureka.server.enable-self-preservation=false",
                    "--eureka.server.eviction-interval-timer-in-ms=1000",
                    "--eureka.server.response-cache-update-interval-ms=500",
                    // Meme raison que pour les clients, et un bruit en
                    // moins : sans cela le serveur tente de joindre un
                    // voisin sur le port 8761 et journalise l'echec.
                    "--eureka.client.jersey.enabled=false",
                    "--logging.level.root=WARN",
                    "--logging.level.com.netflix=OFF",
                    "--logging.level.jakarta.ws.rs=OFF");
    }

    private ConfigurableApplicationContext demarrerUneInstance() {
        return new SpringApplicationBuilder(OffresService.class)
                .web(WebApplicationType.SERVLET)
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false)
                .run(communes(SERVICE));
    }

    private ConfigurableApplicationContext demarrerLaPasserelle() {
        var arguments = new ArrayList<>(List.of(communes("passerelle")));
        arguments.addAll(List.of(
                // Le disjoncteur : trois appels suffisent a decider, et la
                // moitie d'echecs ouvre le circuit. Des valeurs volontairement
                // BASSES, pour que le chapitre 3 puisse les atteindre.
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".sliding-window-size=4",
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".minimum-number-of-calls=4",
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".failure-rate-threshold=50",
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".wait-duration-in-open-state=2s",
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".permitted-number-of-calls-in-half-open-state=2",
                "--resilience4j.circuitbreaker.instances.offresCB"
                + ".automatic-transition-from-open-to-half-open-enabled=true",
                // Le meme disjoncteur, pour la route qui compte les 500.
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".sliding-window-size=4",
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".minimum-number-of-calls=4",
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".failure-rate-threshold=50",
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".wait-duration-in-open-state=2s",
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".permitted-number-of-calls-in-half-open-state=2",
                "--resilience4j.circuitbreaker.instances.offresStrictCB"
                + ".automatic-transition-from-open-to-half-open-enabled=true",
                "--management.endpoints.web.exposure.include=health,circuitbreakers",
                "--management.health.circuitbreakers.enabled=true",
                // Au demarrage, la passerelle est prete avant que les
                // services ne soient enregistres : chaque requete d'attente
                // produit alors un « No servers available » et une trace de
                // servlet. C'est attendu, et cela noierait la sortie des
                // chapitres.
                "--logging.level.org.springframework.cloud.loadbalancer=OFF",
                "--logging.level.org.apache.catalina=OFF"));
        return new SpringApplicationBuilder(Passerelle.class)
                .web(WebApplicationType.SERVLET)
                .bannerMode(org.springframework.boot.Banner.Mode.OFF)
                .logStartupInfo(false)
                .run(arguments.toArray(String[]::new));
    }

    /** Les propriétés communes à tous les clients de l'annuaire. */
    private String[] communes(String nom) {
        return new String[] {
            "--server.port=0",
            "--spring.application.name=" + nom,
            "--eureka.client.service-url.defaultZone=" + urlEureka() + "/eureka/",
            // Les trois lignes qui font la difference entre « ca marche en
            // trente secondes » et « ca marche en deux ».
            "--eureka.client.registry-fetch-interval-seconds=1",
            "--eureka.instance.lease-renewal-interval-in-seconds=1",
            "--eureka.instance.lease-expiration-duration-in-seconds=2",
            // >>> depart: donner a chaque instance un identifiant UNIQUE dans l'annuaire
            //     "--eureka.instance.instance-id=${spring.application.name}",
            // Sans cela, deux instances sur la meme machine se declarent avec
            // le meme identifiant et l'annuaire n'en voit qu'une.
            "--eureka.instance.instance-id=${spring.application.name}:${random.uuid}",
            // <<<
            "--eureka.instance.prefer-ip-address=true",
            // ⚠️ La ligne qui a coute le plus de temps a trouver. Le client
            // Eureka choisit son transport selon ce qu'il voit au classpath :
            // si Jersey est PRESENT et non desactive, il le prefere au
            // `RestClient`. Or le starter du SERVEUR Eureka amene Jersey —
            // et dans une JVM qui heberge les deux, le client part sur un
            // transport dont les fabriques ne sont pas la. Le message
            // d'erreur, lui, parle d'un bean `TransportClientFactories`
            // manquant : rien qui oriente vers Jersey.
            "--eureka.client.jersey.enabled=false",
            "--logging.level.root=WARN",
            // A l'arret, le client Eureka journalise une erreur sur des
            // connexions deja fermees. Elle est sans consequence, et elle
            // salirait la sortie de chaque chapitre.
            "--logging.level.com.netflix=OFF",
        };
    }

    // ── ce que les chapitres interrogent ─────────────────────────────────

    public int portEureka() {
        return port(eureka);
    }

    public String urlEureka() {
        return "http://localhost:" + portEureka();
    }

    public List<Integer> portsDesInstances() {
        return instances.stream().map(Banc::port).toList();
    }

    public int portPasserelle() {
        return port(passerelle);
    }

    public String urlPasserelle() {
        return "http://localhost:" + portPasserelle();
    }

    /** Démarre une instance de plus, une fois le banc lancé. */
    public int ajouterUneInstance() {
        var contexte = demarrerUneInstance();
        instances.add(contexte);
        return port(contexte);
    }

    /** Arrête l'instance qui écoute sur ce port — une panne, pour de vrai. */
    public void tuerLInstance(int portCherche) {
        for (var contexte : List.copyOf(instances)) {
            if (port(contexte) == portCherche) {
                instances.remove(contexte);
                contexte.close();
                return;
            }
        }
    }

    private static int port(ConfigurableApplicationContext contexte) {
        return Integer.parseInt(contexte.getEnvironment()
                .getProperty("local.server.port", "0"));
    }

    // ── un client HTTP, pour interroger tout cela en vrai ────────────────

    public record Reponse(int code, String corps) {
    }

    public static Reponse get(String url) {
        return envoyer(HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10)).GET().build());
    }

    public static Reponse post(String url) {
        return envoyer(HttpRequest.newBuilder(URI.create(url))
                .timeout(Duration.ofSeconds(10))
                .POST(HttpRequest.BodyPublishers.noBody()).build());
    }

    private static Reponse envoyer(HttpRequest requete) {
        try {
            var reponse = CLIENT.send(requete,
                    HttpResponse.BodyHandlers.ofString());
            return new Reponse(reponse.statusCode(), reponse.body());
        } catch (java.io.IOException | InterruptedException panne) {
            if (panne instanceof InterruptedException) {
                Thread.currentThread().interrupt();
            }
            return new Reponse(0, panne.getClass().getSimpleName());
        }
    }

    /**
     * Attend qu'une condition devienne vraie, sans dépasser un délai.
     *
     * <p>⚠️ Indispensable, et pas une commodité : l'enregistrement dans
     * Eureka est <strong>asynchrone</strong>. Mesurer juste après le
     * démarrage donnerait zéro instance, et le chiffre dépendrait de la
     * machine. Le chapitre 2 imprime d'ailleurs le temps que cela a pris.
     */
    public static boolean attendre(java.util.function.BooleanSupplier condition,
                                   Duration limite) {
        long fin = System.nanoTime() + limite.toNanos();
        while (System.nanoTime() < fin) {
            if (condition.getAsBoolean()) {
                return true;
            }
            try {
                Thread.sleep(100);
            } catch (InterruptedException interrompu) {
                Thread.currentThread().interrupt();
                return false;
            }
        }
        return condition.getAsBoolean();
    }

    @Override
    public void close() {
        if (passerelle != null) {
            passerelle.close();
        }
        for (var instance : instances) {
            instance.close();
        }
        eureka.close();
    }
}
