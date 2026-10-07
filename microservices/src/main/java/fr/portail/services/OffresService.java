package fr.portail.services;

import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.core.env.Environment;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Le service « offres » du portail — une vraie application Spring Boot.
 *
 * <p>Il s'enregistre auprès d'Eureka sous le nom {@code offres-service}, et
 * <strong>plusieurs instances</strong> du même service tournent en parallèle
 * dans les chapitres : c'est ce qui permet de mesurer l'équilibrage de charge
 * côté client, puis la bascule quand l'une tombe.
 *
 * <p>Chaque instance répond en donnant <strong>son</strong> port : c'est
 * ainsi que le chapitre 2 compte qui a servi combien de requêtes, sans rien
 * instrumenter.
 *
 * <p>⚠️ La route {@code /panne} n'est pas un gadget : le chapitre 3 en a
 * besoin pour faire tomber le service à volonté et regarder le circuit
 * s'ouvrir. Un service qui ne peut pas tomber ne prouve rien.
 *
 * <p>⚠️ Les compteurs sont <em>statiques</em> parce que les instances
 * partagent une JVM dans ce projet. En production elles seraient dans des
 * conteneurs séparés, et ce comptage passerait par les métriques. Ce qui est
 * mesuré — la répartition entre instances — est le même.
 */
@SpringBootApplication
@RestController
public class OffresService {

    /** Quand ce drapeau est levé, le service répond 500 — à la demande. */
    private static final AtomicBoolean PANNE = new AtomicBoolean();

    /** Le nombre de requêtes servies, par instance (clé : le port). */
    private static final Map<String, AtomicInteger> SERVIES =
            new ConcurrentHashMap<>();

    private final Environment environnement;

    public OffresService(Environment environnement) {
        this.environnement = environnement;
    }

    public static Map<String, AtomicInteger> servies() {
        return SERVIES;
    }

    public static int total() {
        return SERVIES.values().stream().mapToInt(AtomicInteger::get).sum();
    }

    public static void remettreAZero() {
        SERVIES.clear();
        PANNE.set(false);
        LENTEUR.set(0);
    }

    public static boolean enPanne() {
        return PANNE.get();
    }

    /** Le port de CETTE instance, lu au moment de la requête. */
    private String moi() {
        return environnement.getProperty("local.server.port", "?");
    }

    /**
     * Le temps que le service met à répondre, en millisecondes.
     *
     * <p>⚠️ Un service qui répond mal et un service qui répond LENTEMENT ne
     * se soignent pas de la même façon, et le chapitre 3 a besoin des deux.
     * Un service lent est, du point de vue d'un appelant sans délai
     * d'attente, bien pire qu'un service en panne : il retient un thread au
     * lieu de le libérer.
     */
    private static final java.util.concurrent.atomic.AtomicLong LENTEUR =
            new java.util.concurrent.atomic.AtomicLong();

    @PostMapping("/lenteur")
    public String lenteur(@RequestParam long millisecondes) {
        LENTEUR.set(millisecondes);
        return "lenteur=" + millisecondes;
    }

    private static void ralentir() {
        long attente = LENTEUR.get();
        if (attente <= 0) {
            return;
        }
        try {
            Thread.sleep(attente);
        } catch (InterruptedException interrompu) {
            Thread.currentThread().interrupt();
        }
    }

    @GetMapping("/offres")
    public ResponseEntity<List<String>> offres() {
        SERVIES.computeIfAbsent(moi(), p -> new AtomicInteger())
                .incrementAndGet();
        ralentir();
        if (PANNE.get()) {
            // Une panne franche, du type de celles qui font ouvrir un
            // circuit : le service repond, mais mal.
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                    .body(List.of("panne simulee"));
        }
        return ResponseEntity.ok(List.of(
                "OFF-014 Developpeuse Java senior, Lyon",
                "OFF-021 Ingenieure SRE, Toulouse",
                "OFF-033 Analyste donnees, Paris"));
    }

    /** Qui a répondu ? Le chapitre 2 s'en sert pour compter. */
    @GetMapping("/qui")
    public String qui() {
        String moi = moi();
        SERVIES.computeIfAbsent(moi, p -> new AtomicInteger())
                .incrementAndGet();
        return "offres-service:" + moi;
    }

    /**
     * Ce que le service a VRAIMENT reçu dans ses en-têtes.
     *
     * <p>Le chapitre 6 s'en sert pour vérifier qu'un identifiant de
     * corrélation posé à la passerelle arrive bien jusqu'ici — et que le
     * service, lui, ne voit jamais le jeton d'authentification si la
     * passerelle ne le relaie pas.
     */
    @GetMapping("/entetes")
    public Map<String, String> entetes(
            @org.springframework.web.bind.annotation.RequestHeader(
                    name = "X-Request-Id", required = false) String correlation,
            @org.springframework.web.bind.annotation.RequestHeader(
                    name = "Authorization", required = false) String jeton) {
        SERVIES.computeIfAbsent(moi(), p -> new AtomicInteger())
                .incrementAndGet();
        return Map.of(
                "instance", moi(),
                "X-Request-Id", correlation == null ? "(absent)" : correlation,
                "Authorization", jeton == null ? "(absent)" : "(present)");
    }

    @PostMapping("/panne")
    public String panne(@RequestParam boolean active) {
        PANNE.set(active);
        return "panne=" + active;
    }
}
