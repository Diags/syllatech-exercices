package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import io.micrometer.core.instrument.observation.DefaultMeterObservationHandler;
import io.micrometer.core.instrument.simple.SimpleMeterRegistry;
import io.micrometer.observation.ObservationRegistry;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.evaluation.RelevancyEvaluator;
import org.springframework.ai.chat.observation.ChatModelMeterObservationHandler;
import org.springframework.ai.evaluation.EvaluationRequest;

/**
 * Chapitre 6 — Tests, observabilité et mise en production.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Production
 * </pre>
 *
 * <p>« Les métriques Micrometer suivent tokens et latences. » Ce chapitre les
 * fait apparaître pour de bon : un {@code SimpleMeterRegistry}, les
 * gestionnaires d'observation de Spring AI, et l'impression de
 * <strong>tous</strong> les compteurs produits — noms, étiquettes, valeurs.
 *
 * <p>Il fait ensuite juger une réponse par un modèle, imprime
 * <strong>le prompt du juge</strong>, et montre où cette évaluation est
 * fragile. Puis il chiffre ce que coûtent un réessai et un repli — parce que
 * la résilience se paie en jetons.
 */
public final class Chapitre6Production {

    private Chapitre6Production() {
    }

    private static final String QUESTION =
            "Quelles offres proposent du teletravail ?";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);

            Console.titre(1, "LA METRIQUE QUE LE COURS NOMME");
            var compteurs = new SimpleMeterRegistry();
            var observations = ObservationRegistry.create();
            observations.observationConfig()
                    .observationHandler(new DefaultMeterObservationHandler(compteurs))
                    .observationHandler(
                            new ChatModelMeterObservationHandler(compteurs));
            modele.observer(observations);
            modele.remettreAZero();
            var client = ChatClient.builder(modele).build();
            for (int i = 0; i < 3; i++) {
                client.prompt().user("Donne 3 conseils pour un entretien")
                        .call().content();
            }
            Console.ligne("appels au modele", String.valueOf(modele.appels()), 26);
            System.out.println();
            Console.sousTitre("Les compteurs, tels que l'Actuator les "
                    + "exposerait :");
            Console.tableau(List.of("compteur", "etiquette", "valeur"),
                    mesures(compteurs), List.of(32, 16, 10));
            System.out.println();
            Console.texte("`gen_ai.client.token.usage` existe vraiment, et il "
                    + "porte l'etiquette `gen_ai.token.type` qui separe "
                    + "l'entree de la sortie. C'est la mesure qui compte : "
                    + "les jetons d'entree et de sortie ne sont pas factures "
                    + "au meme prix, souvent du simple au quadruple.");
            System.out.println();
            Console.texte("⚠️ Et voici ce que personne ne dit : ces compteurs "
                    + "n'apparaissent QUE parce que le modele de ce projet "
                    + "ouvre lui-meme l'observation autour de son appel. "
                    + "L'instrumentation est dans le `ChatModel`, pas dans "
                    + "`ChatClient` — un modele ecrit a la main qui ne le fait "
                    + "pas n'expose rien, et le tableau de bord reste vide "
                    + "sans qu'aucune erreur ne le signale.");
            System.out.println();
            Console.texte("⚠️ Deuxieme limite : aucun euro nulle part. La "
                    + "metrique compte des jetons ; le prix du jeton est chez "
                    + "le fournisseur, il change avec le modele et avec le "
                    + "temps. Le cout se calcule en dehors, et c'est une "
                    + "table a tenir a jour.");

            Console.titre(2, "UN MODELE QUI EN JUGE UN AUTRE");
            modele.remettreAZero();
            modele.repondre(prompt -> prompt.contains("evaluate if the response")
                    ? "YES" : null);
            var juge = new RelevancyEvaluator(ChatClient.builder(modele));
            var verdict = juge.evaluate(new EvaluationRequest(QUESTION,
                    fr.portail.rag.Corpus.OFFRES.subList(0, 2),
                    "OFF-014 et OFF-021 proposent du teletravail."));
            Console.ligne("verdict", verdict.isPass() ? "PASSE" : "REFUSE", 22);
            System.out.println();
            Console.sousTitre("Le prompt que le juge a recu :");
            Console.bloc(modele.dernierTexte(), 6);
            System.out.println();
            Console.texte("Voila « un LLM qui juge un LLM » : un second appel, "
                    + "avec la question, la reponse, le contexte, et la "
                    + "consigne de repondre YES ou NO. Rien de magique — un "
                    + "prompt, et une facture de plus.");

            Console.titre(3, "LA FRAGILITE DU JUGE");
            var nuances = new ArrayList<List<String>>();
            for (var reponseDuJuge : List.of("YES", "yes", "Yes, absolument.",
                    "YES.", "NO")) {
                modele.remettreAZero();
                modele.repondre(prompt ->
                        prompt.contains("evaluate if the response")
                                ? reponseDuJuge : null);
                var essai = new RelevancyEvaluator(ChatClient.builder(modele))
                        .evaluate(new EvaluationRequest(QUESTION, List.of(),
                                "OFF-014 propose du teletravail."));
                nuances.add(List.of("« " + reponseDuJuge + " »",
                        essai.isPass() ? "PASSE" : "REFUSE"));
            }
            Console.tableau(List.of("ce que le juge repond",
                    "ce que `isPass()` rend"), nuances, List.of(28, 24));
            System.out.println();
            Console.texte("`isPass()` n'est pas une note : c'est une "
                    + "comparaison de chaine. Spring AI compare la reponse du "
                    + "juge a « YES », sans tenir compte de la casse, apres "
                    + "avoir enleve les espaces. Tout le reste est un echec — "
                    + "y compris un « Yes, absolument. » qui veut dire oui, et "
                    + "y compris un « YES. » avec un point.");
            System.out.println();
            Console.texte("⚠️ C'est la source de faux echecs la plus banale "
                    + "dans un test d'evaluation : le juge etait d'accord, le "
                    + "test est rouge, et l'equipe cherche la panne du mauvais "
                    + "cote. Le remede tient en une ligne — un "
                    + "`promptTemplate` a soi, qui exige le mot seul — et il "
                    + "commence par savoir que le probleme existe.");
            System.out.println();
            Console.texte("⚠️ Plus grave : le juge est un modele comme "
                    + "l'autre. Il se trompe, il coute, et il n'a aucune "
                    + "autorite particuliere. Une evaluation automatique "
                    + "detecte une DERIVE entre deux versions ; elle ne "
                    + "prouve pas qu'une reponse est vraie.");

            Console.titre(4, "CE QUE COUTE LA RESILIENCE");
            var lignes = new ArrayList<List<String>>();
            lignes.add(essai(modele, "aucun filet", 0, false));
            lignes.add(essai(modele, "repli, sans reessai", 0, true));
            lignes.add(essai(modele, "3 reessais", 3, false));
            Console.tableau(List.of("politique", "appels", "jetons comptes",
                    "ce que l'appelant recoit"),
                    lignes, List.of(22, 9, 16, 26));
            System.out.println();
            Console.texte("Le modele de cette section echoue deux fois sur "
                    + "trois. Sans filet, l'appelant recoit l'exception. Avec "
                    + "un repli, il recoit une phrase ecrite dans votre code — "
                    + "gratuite, immediate, et bien meilleure qu'une page "
                    + "d'erreur. Avec trois reessais, il finit par recevoir la "
                    + "vraie reponse, au prix de trois appels.");
            System.out.println();
            Console.texte("⚠️ Maintenant regardez la colonne des jetons. "
                    + "Trois appels, et le compteur n'en retient qu'un seul : "
                    + "`gen_ai.client.token.usage` ne compte que les appels "
                    + "QUI ABOUTISSENT, parce qu'un fournisseur en panne ne "
                    + "renvoie pas d'usage. Vos reessais sont invisibles dans "
                    + "le compteur de jetons ; ils apparaissent dans "
                    + "`gen_ai.client.operation`, qui compte les appels. "
                    + "Surveiller le cout demande les deux.");
            System.out.println();
            Console.texte("⚠️ Et il existe un cas ou le compteur se trompe "
                    + "vraiment : quand la panne arrive APRES que le modele a "
                    + "repondu — un delai depasse, une coupure reseau. Le "
                    + "fournisseur a calcule, il facture, et votre compteur ne "
                    + "voit rien. La section suivante fabrique ce cas-la.");

            Console.titre(5, "LE DELAI D'ATTENTE N'EST PAS DANS `ChatClient`");
            modele.remettreAZero();
            modele.repondre(prompt -> {
                dormir(300);
                return "Reponse lente.";
            });
            var lent = ChatClient.builder(modele).build();
            long debut = System.nanoTime();
            lent.prompt().user(QUESTION).call().content();
            long duree = (System.nanoTime() - debut) / 1_000_000;
            Console.ligne("le modele met", duree + " ms", 30);
            Console.ligne("ChatClient a-t-il coupe", "non", 30);
            String coupe;
            try {
                CompletableFuture
                        .supplyAsync(() -> lent.prompt().user(QUESTION)
                                .call().content())
                        .get(100, TimeUnit.MILLISECONDS);
                coupe = "aucune coupure";
            } catch (Exception erreur) {
                coupe = erreur.getClass().getSimpleName();
            }
            Console.ligne("avec un delai de 100 ms autour", coupe, 34);
            Console.ligne("le modele a-t-il quand meme repondu",
                    String.valueOf(modele.appels() >= 2), 40);
            System.out.println();
            Console.texte("`ChatClient` n'a pas de delai d'attente. Il "
                    + "attendra aussi longtemps que le modele voudra bien "
                    + "repondre — et un appel bloque tient un thread de votre "
                    + "serveur pendant tout ce temps.");
            System.out.println();
            Console.texte("La derniere ligne est le cas annonce plus haut : "
                    + "l'appelant a abandonne au bout de 100 ms, et le modele "
                    + "a termine son travail quand meme. Chez un vrai "
                    + "fournisseur, ce travail est calcule et facture — "
                    + "personne ne l'a lu, tout le monde l'a paye.");
            System.out.println();
            Console.texte("⚠️ En production, le delai se regle sur le CLIENT "
                    + "HTTP du fournisseur, pas ici : c'est le `RestClient` ou "
                    + "le `WebClient` que le starter configure. Couper plus "
                    + "tot economise un thread, jamais une facture.");

            Console.titre(6, "TESTER SANS FOURNISSEUR");
            Console.ligne("cles d'API dans ce projet", "aucune", 38);
            Console.ligne("starter OpenAI dans le classpath",
                    presente("org.springframework.ai.openai.OpenAiChatModel")
                            ? "present" : "absent", 38);
            Console.ligne("starter Anthropic dans le classpath",
                    presente("org.springframework.ai.anthropic.AnthropicChatModel")
                            ? "present" : "absent", 38);
            Console.ligne("starter Ollama dans le classpath",
                    presente("org.springframework.ai.ollama.OllamaChatModel")
                            ? "present" : "absent", 38);
            Console.ligne("le modele de tout ce cours",
                    modele.getClass().getSimpleName(), 38);
            System.out.println();
            Console.texte("C'est la reponse pratique du chapitre 6, et c'est "
                    + "tout ce projet : un `ChatModel` ecrit a la main rend "
                    + "les tests deterministes, gratuits et hors ligne. Les "
                    + "tests de ce depot verifient ce que Spring AI "
                    + "CONSTRUIT — le schema, le contexte injecte, "
                    + "l'aller-retour d'outil, les compteurs — et cela ne "
                    + "demande aucun fournisseur.");
            System.out.println();
            Console.texte("⚠️ Et voici la limite, ecrite noir sur blanc : ce "
                    + "projet ne mesure JAMAIS la qualite d'une reponse. "
                    + "Aucune ligne de ces six chapitres ne dit qu'un modele "
                    + "repond bien. Pour cela il faut un vrai fournisseur, un "
                    + "jeu d'evaluation, et l'acceptation qu'une partie du "
                    + "resultat restera une appreciation humaine.");
            System.out.println();
            Console.texte("La bonne pratique tient en deux couches : des "
                    + "tests rapides et hors ligne pour votre code — ceux-ci "
                    + "— et une petite serie d'appels reels, lancee a la "
                    + "main ou la nuit, pour la qualite. Confondre les deux "
                    + "donne une suite lente, chere et instable.");
            System.out.println();
        }
    }

    /**
     * Une politique de résilience, jouée sur un modèle qui échoue deux fois
     * sur trois.
     *
     * <p>Le réessai est écrit à la main, en cinq lignes. Ce n'est pas une
     * économie de dépendance : c'est pour que le comptage soit visible.
     * {@code RetryTemplate} ou {@code @Retryable} font la même chose, avec
     * un délai croissant en plus — et la même facture.
     */
    private static List<String> essai(ModeleFactice modele, String nom,
                                      int reessais, boolean repli) {
        var compteurs = new SimpleMeterRegistry();
        var observations = ObservationRegistry.create();
        observations.observationConfig().observationHandler(
                new ChatModelMeterObservationHandler(compteurs));
        modele.remettreAZero();
        modele.observer(observations);
        var pannes = new AtomicInteger();
        modele.repondre(prompt -> {
            if (pannes.incrementAndGet() % 3 != 0) {
                throw new IllegalStateException("503 chez le fournisseur");
            }
            return "Trois offres proposent du teletravail.";
        });
        var client = ChatClient.builder(modele).build();
        String recu = null;
        for (int tentative = 0; tentative <= reessais && recu == null; tentative++) {
            try {
                recu = client.prompt().user(QUESTION).call().content();
            } catch (RuntimeException panne) {
                if (tentative == reessais) {
                    recu = repli ? "(repli) Consultez les offres du portail."
                            : "l'exception " + panne.getClass().getSimpleName();
                }
            }
        }
        return List.of(nom, String.valueOf(modele.appels()),
                String.valueOf(jetons(compteurs)), court(recu));
    }

    /** Le total de `gen_ai.client.token.usage`, toutes étiquettes confondues. */
    private static long jetons(SimpleMeterRegistry compteurs) {
        double total = 0;
        for (var compteur : compteurs.getMeters()) {
            if (compteur.getId().getName().contains("token.usage")) {
                for (var mesure : compteur.measure()) {
                    total += mesure.getValue();
                }
            }
        }
        return (long) total;
    }

    /** Tous les compteurs du registre, dans l'ordre alphabétique. */
    private static List<List<String>> mesures(SimpleMeterRegistry compteurs) {
        var lignes = new ArrayList<List<String>>();
        for (var compteur : compteurs.getMeters()) {
            double total = 0;
            for (var mesure : compteur.measure()) {
                total += mesure.getValue();
            }
            // Seule l'etiquette qui DISTINGUE deux lignes du meme compteur
            // est affichee. `gen_ai.system=factice` est sur toutes : la
            // montrer cinq fois remplirait la colonne sans rien apprendre.
            var etiquettes = new ArrayList<String>();
            for (var etiquette : compteur.getId().getTags()) {
                if (etiquette.getKey().contains("token.type")) {
                    etiquettes.add(etiquette.getValue());
                }
            }
            lignes.add(List.of(compteur.getId().getName(),
                    String.join(" ", etiquettes),
                    "%.0f".formatted(total)));
        }
        lignes.sort((a, b) -> (a.get(0) + a.get(1))
                .compareTo(b.get(0) + b.get(1)));
        return lignes;
    }

    /** La classe est-elle dans le classpath ? Demandé à la JVM, pas affirmé. */
    private static boolean presente(String nom) {
        try {
            Class.forName(nom);
            return true;
        } catch (ClassNotFoundException absente) {
            return false;
        }
    }

    private static void dormir(long millisecondes) {
        try {
            Thread.sleep(millisecondes);
        } catch (InterruptedException interrompu) {
            Thread.currentThread().interrupt();
        }
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(rien)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 24 ? plat : plat.substring(0, 21) + "...";
    }
}
