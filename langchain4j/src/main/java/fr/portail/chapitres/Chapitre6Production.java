package fr.portail.chapitres;

import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.service.AiServices;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.JournalDesAppels;
import fr.portail.modele.ModeleFactice;
import fr.portail.service.AssistantCarriere;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;

/**
 * Chapitre 6 — Production : tests, observabilité, résilience.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre6Production
 * </pre>
 *
 * <p>« Un {@code ChatModelListener} s'intercale autour de chaque appel. »
 * Autour de quel appel, exactement ? Ce chapitre le mesure — et montre que
 * l'exemple de modèle bouchonné du cours, qui redéfinit {@code chat}, rend
 * l'écouteur <strong>totalement muet</strong>.
 *
 * <p>Il chiffre ensuite ce que coûtent un réessai et un repli, et vérifie
 * qu'aucun délai d'attente n'existe là où on le croit.
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

            Console.titre(1, "L'ECOUTEUR QUI VOIT TOUT");
            var journal = new JournalDesAppels();
            modele.remettreAZero();
            modele.ecouter(journal);
            var assistant = AiServices.create(AssistantCarriere.class, modele);
            for (int i = 0; i < 3; i++) {
                assistant.conseiller("Donne 3 conseils pour un entretien");
            }
            Console.ligne("appels au modele", String.valueOf(modele.appels()), 30);
            Console.ligne("vus par `onRequest`",
                    String.valueOf(journal.requetes()), 30);
            Console.ligne("vus par `onResponse`",
                    String.valueOf(journal.reponses()), 30);
            Console.ligne("jetons d'entree",
                    String.valueOf(journal.jetonsEntree()), 30);
            Console.ligne("jetons de sortie",
                    String.valueOf(journal.jetonsSortie()), 30);
            Console.ligne("latence moyenne",
                    journal.latenceMoyenneMs() + " ms", 30);
            System.out.println();
            Console.texte("Voila le nerf de la facture, mesure : les jetons "
                    + "d'entree et de sortie, separes — ils ne sont pas "
                    + "factures au meme prix, souvent du simple au quadruple. "
                    + "Branche sur Micrometer, ce compteur devient un tableau "
                    + "de bord ; ici il devient un tableau imprime.");
            System.out.println();
            Console.texte("⚠️ Aucun euro nulle part. L'ecouteur compte des "
                    + "jetons ; le prix du jeton est chez le fournisseur, il "
                    + "change avec le modele et avec le temps. Le cout se "
                    + "calcule en dehors, et c'est une table a tenir a jour.");

            Console.titre(2, "POURQUOI L'EXEMPLE DU COURS EST MUET");
            var muet = new JournalDesAppels();
            var bouchon = new BouchonDuCours(muet);
            var assistantBouchonne = AiServices.create(AssistantCarriere.class,
                    bouchon);
            for (int i = 0; i < 3; i++) {
                assistantBouchonne.conseiller("Donne 3 conseils");
            }
            Console.tableau(List.of("ce que le modele redefinit",
                    "appels reels", "vus par l'ecouteur"), List.of(
                    List.of("`doChat` (ce projet)",
                            String.valueOf(modele.appels()),
                            String.valueOf(journal.requetes())),
                    List.of("`chat` (exemple du cours)",
                            String.valueOf(bouchon.appels()),
                            String.valueOf(muet.requetes()))),
                    List.of(28, 14, 20));
            System.out.println();
            Console.texte("Trois appels de chaque cote. En haut, l'ecouteur "
                    + "les voit tous les trois ; en bas, il n'en voit AUCUN — "
                    + "et les deux modeles exposent pourtant le meme ecouteur "
                    + "par `listeners()`. La difference tient au nom de la "
                    + "methode redefinie : `chat(ChatRequest)` est "
                    + "l'ENVELOPPE, celle qui previent les "
                    + "`ChatModelListener` avant, apres, et en cas d'erreur, "
                    + "avant de deleguer a `doChat`.");
            System.out.println();
            Console.texte("⚠️ Redefinir `chat` — ce que fait l'exemple de "
                    + "modele bouchonne du chapitre 6 — desactive donc toute "
                    + "l'observabilite, sans erreur et sans message. C'est le "
                    + "genre de detail qui se paie en production : le "
                    + "tableau de bord reste vide, et personne ne sait "
                    + "pourquoi.");
            System.out.println();
            Console.texte("La regle tient en une ligne : dans un `ChatModel` "
                    + "ecrit a la main, on redefinit `doChat`, et on expose "
                    + "ses ecouteurs via `listeners()`.");

            Console.titre(3, "CE QUE COUTE LA RESILIENCE");
            var lignes = new ArrayList<List<String>>();
            lignes.add(essai(modele, "aucun filet", 0, false));
            lignes.add(essai(modele, "repli, sans reessai", 0, true));
            lignes.add(essai(modele, "3 reessais", 3, false));
            Console.tableau(List.of("politique", "appels", "erreurs vues",
                    "jetons comptes", "ce que l'appelant recoit"),
                    lignes, List.of(20, 8, 14, 16, 22));
            System.out.println();
            Console.texte("Le modele de cette section echoue deux fois sur "
                    + "trois. Sans filet, l'appelant recoit l'exception. Avec "
                    + "un repli, il recoit une phrase ecrite dans votre code — "
                    + "gratuite, immediate, et bien meilleure qu'une page "
                    + "d'erreur. Avec trois reessais, il finit par recevoir la "
                    + "vraie reponse, au prix de trois appels.");
            System.out.println();
            Console.texte("⚠️ Regardez la colonne des jetons : trois appels, "
                    + "et le compteur n'en retient qu'un. `onResponse` ne "
                    + "declenche que sur les appels QUI ABOUTISSENT, parce "
                    + "qu'un fournisseur en panne ne renvoie pas d'usage. Les "
                    + "reessais sont invisibles cote jetons, et visibles cote "
                    + "`onError` — la colonne d'a cote. Surveiller le cout "
                    + "demande les deux compteurs.");
            System.out.println();
            Console.texte("⚠️ Et il existe un cas ou le compteur se trompe "
                    + "vraiment : quand la panne arrive APRES que le modele a "
                    + "repondu — un delai depasse, une coupure reseau. Le "
                    + "fournisseur a calcule, il facture, et votre compteur ne "
                    + "voit rien. La section suivante fabrique ce cas-la.");

            Console.titre(4, "LE DELAI D'ATTENTE N'EST PAS DANS `AiServices`");
            modele.remettreAZero();
            modele.repondre(prompt -> {
                dormir(300);
                return "Reponse lente.";
            });
            var lent = AiServices.create(AssistantCarriere.class, modele);
            long debut = System.nanoTime();
            lent.conseiller(QUESTION);
            long duree = (System.nanoTime() - debut) / 1_000_000;
            Console.ligne("le modele met", duree + " ms", 32);
            Console.ligne("AiServices a-t-il coupe", "non", 32);
            String coupe;
            try {
                CompletableFuture.supplyAsync(() -> lent.conseiller(QUESTION))
                        .get(100, TimeUnit.MILLISECONDS);
                coupe = "aucune coupure";
            } catch (Exception erreur) {
                coupe = erreur.getClass().getSimpleName();
            }
            Console.ligne("avec un delai de 100 ms autour", coupe, 34);
            Console.ligne("le modele a-t-il quand meme repondu",
                    modele.appels() >= 2 ? "oui" : "non", 38);
            System.out.println();
            Console.texte("`AiServices` n'a pas de delai d'attente. Il "
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
                    + "du fournisseur — `.timeout(...)` sur le builder "
                    + "d'`OpenAiChatModel`, par exemple — pas ici. Couper "
                    + "plus tot economise un thread, jamais une facture.");

            Console.titre(5, "TESTER SANS FOURNISSEUR");
            Console.ligne("cles d'API dans ce projet", "aucune", 38);
            Console.ligne("module OpenAI dans le classpath",
                    presente("dev.langchain4j.model.openai.OpenAiChatModel")
                            ? "present" : "absent", 38);
            Console.ligne("module Ollama dans le classpath",
                    presente("dev.langchain4j.model.ollama.OllamaChatModel")
                            ? "present" : "absent", 38);
            Console.ligne("le modele de tout ce cours",
                    modele.getClass().getSimpleName(), 38);
            System.out.println();
            Console.texte("C'est la recommandation du chapitre 6, poussee "
                    + "jusqu'au bout : « comme `ChatModel` est une simple "
                    + "interface, vous en fournissez une implementation "
                    + "bouchonnee ». Ce projet en a fait sa base — les tests "
                    + "sont instantanes, gratuits et reproductibles, et ils "
                    + "verifient ce que LangChain4j CONSTRUIT : le prompt, le "
                    + "schema, le contexte injecte, l'aller-retour d'outil, "
                    + "les compteurs.");
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
                    + "— et une petite serie d'appels reels, lancee a la main "
                    + "ou la nuit, pour la qualite. Confondre les deux donne "
                    + "une suite lente, chere et instable.");
            System.out.println();
        }
    }

    /**
     * Le modèle bouchonné tel que le cours l'écrit — en redéfinissant
     * {@code chat}.
     *
     * <p>Il est parfaitement fonctionnel : il répond, les tests passent. Il
     * ne prévient simplement jamais l'écouteur, parce que la méthode
     * redéfinie est celle qui aurait dû le faire.
     */
    private static final class BouchonDuCours implements ChatModel {

        private final ChatModelListener ecouteur;
        private final AtomicInteger appels = new AtomicInteger();

        private BouchonDuCours(ChatModelListener ecouteur) {
            this.ecouteur = ecouteur;
        }

        @Override
        public ChatResponse chat(ChatRequest requete) {
            appels.incrementAndGet();
            return ChatResponse.builder()
                    .aiMessage(AiMessage.from("Reponse figee du bouchon."))
                    .build();
        }

        @Override
        public List<ChatModelListener> listeners() {
            return List.of(ecouteur);
        }

        int appels() {
            return appels.get();
        }
    }

    /**
     * Une politique de résilience, jouée sur un modèle qui échoue deux fois
     * sur trois.
     *
     * <p>Le réessai est écrit à la main, en cinq lignes. Ce n'est pas une
     * économie de dépendance : c'est pour que le comptage soit visible.
     * Resilience4j fait la même chose, avec un délai croissant en plus — et
     * la même facture.
     */
    private static List<String> essai(ModeleFactice modele, String nom,
                                      int reessais, boolean repli) {
        var journal = new JournalDesAppels();
        modele.remettreAZero();
        modele.ecouter(journal);
        var pannes = new AtomicInteger();
        modele.repondre(prompt -> {
            if (pannes.incrementAndGet() % 3 != 0) {
                throw new IllegalStateException("503 chez le fournisseur");
            }
            return "Trois offres proposent du teletravail.";
        });
        var assistant = AiServices.create(AssistantCarriere.class, modele);
        String recu = null;
        for (int tentative = 0; tentative <= reessais && recu == null; tentative++) {
            try {
                recu = assistant.conseiller(QUESTION);
            } catch (RuntimeException panne) {
                if (tentative == reessais) {
                    recu = repli ? "(repli) Consultez les offres du portail."
                            : "l'exception " + panne.getClass().getSimpleName();
                }
            }
        }
        return List.of(nom, String.valueOf(modele.appels()),
                String.valueOf(journal.erreurs()),
                String.valueOf(journal.jetonsEntree() + journal.jetonsSortie()),
                court(recu));
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
        return plat.length() <= 20 ? plat : plat.substring(0, 17) + "...";
    }
}
