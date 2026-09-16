package fr.portail.chapitres;

import dev.langchain4j.data.image.Image;
import dev.langchain4j.data.message.ImageContent;
import dev.langchain4j.data.message.TextContent;
import dev.langchain4j.data.message.UserMessage;
import dev.langchain4j.memory.chat.MessageWindowChatMemory;
import dev.langchain4j.service.AiServices;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.modele.ModeleFacticeEnFlux;
import fr.portail.service.AssistantAvecMemoire;
import fr.portail.service.AssistantCarriere;
import fr.portail.service.AssistantEnFlux;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import javax.imageio.ImageIO;

/**
 * Chapitre 5 — Mémoire, streaming et multimodal.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Memoire
 * </pre>
 *
 * <p>« LangChain4j rejoue l'historique à chaque tour. » Ce chapitre le compte :
 * combien de messages partent au premier tour, au troisième, au huitième — et
 * ce que la fenêtre glissante coupe exactement.
 *
 * <p>Il mesure ensuite le <strong>temps jusqu'au premier jeton</strong>, qui
 * est le seul gain réel du streaming, et ce qu'une image devient dans un
 * message.
 */
public final class Chapitre5Memoire {

    private Chapitre5Memoire() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var enFlux = banc.bean(ModeleFacticeEnFlux.class);

            Console.titre(1, "LA MEMOIRE REJOUE TOUT, A CHAQUE TOUR");
            var conversant = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .chatMemory(MessageWindowChatMemory.withMaxMessages(10))
                    .build();
            modele.oublier();
            var lignes = new ArrayList<List<String>>();
            String[] tours = {
                "Je cherche un poste a Lyon.",
                "Et le salaire ?",
                "Merci, et le teletravail ?",
            };
            for (var tour : tours) {
                conversant.conseiller(tour);
                lignes.add(List.of(court(tour, 30),
                        String.valueOf(modele.derniersMessages().size()),
                        String.valueOf(modele.dernierTexte().length())));
            }
            Console.tableau(List.of("le tour de parole", "messages envoyes",
                    "caracteres"), lignes, List.of(32, 18, 14));
            System.out.println();
            Console.texte("Le troisieme tour envoie six messages pour une "
                    + "question de trois mots — le message systeme, puis "
                    + "chaque question et chaque reponse depuis le debut. "
                    + "C'est ce que fait une `ChatMemory` : elle rejoue TOUT "
                    + "l'historique, parce qu'un modele ne se souvient de "
                    + "rien entre deux requetes.");
            System.out.println();
            Console.texte("La consequence est financiere. Une conversation de "
                    + "vingt tours facture vingt fois le debut de la "
                    + "conversation.");

            Console.titre(2, "CE QUE LA FENETRE COUPE, EXACTEMENT");
            var court = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .chatMemory(MessageWindowChatMemory.withMaxMessages(4))
                    .build();
            var large = AiServices.builder(AssistantCarriere.class)
                    .chatModel(modele)
                    .chatMemory(MessageWindowChatMemory.withMaxMessages(20))
                    .build();
            var comparaison = new ArrayList<List<String>>();
            for (var essai : List.of(new Object[] {"fenetre de 4", court},
                    new Object[] {"fenetre de 20", large})) {
                var assistant = (AssistantCarriere) essai[1];
                modele.oublier();
                int caracteres = 0;
                for (int tour = 1; tour <= 6; tour++) {
                    assistant.conseiller("Question numero " + tour + " ?");
                    caracteres += modele.dernierTexte().length();
                }
                comparaison.add(List.of((String) essai[0],
                        String.valueOf(modele.derniersMessages().size()),
                        String.valueOf(caracteres)));
            }
            Console.tableau(List.of("configuration",
                    "messages au 6e tour", "caracteres cumules"),
                    comparaison, List.of(20, 22, 20));
            System.out.println();
            Console.texte("Six tours identiques, deux factures differentes. "
                    + "`MessageWindowChatMemory` borne la fenetre, et c'est "
                    + "une decision de cout autant que de pertinence : trop "
                    + "courte, l'assistant oublie ce qu'on vient de lui dire ; "
                    + "trop longue, chaque tour traine tout le passe.");
            System.out.println();
            Console.texte("⚠️ Et la fenetre compte des MESSAGES, pas des "
                    + "jetons. Un message de trois mots et un message de "
                    + "trois pages comptent pareil. Pour borner un cout, "
                    + "c'est une approximation — utile, mais une "
                    + "approximation.");

            Console.titre(3, "`@MemoryId` : DEUX CONVERSATIONS, ZERO MELANGE");
            String sansFournisseur;
            try {
                AiServices.create(AssistantAvecMemoire.class, modele);
                sansFournisseur = "construit sans erreur";
            } catch (RuntimeException refus) {
                sansFournisseur = refus.getClass().getSimpleName() + " au BUILD";
            }
            Console.ligne("sans `chatMemoryProvider`", sansFournisseur, 32);
            var parUtilisateur = AiServices.builder(AssistantAvecMemoire.class)
                    .chatModel(modele)
                    .chatMemoryProvider(id ->
                            MessageWindowChatMemory.withMaxMessages(10))
                    .build();
            parUtilisateur.discuter("awa", "Je cherche un poste a Lyon.");
            parUtilisateur.discuter("karim", "Je cherche un poste a Nantes.");
            modele.oublier();
            parUtilisateur.discuter("awa", "Et le salaire ?");
            String vuParAwa = modele.dernierTexte();
            modele.oublier();
            parUtilisateur.discuter("karim", "Et le salaire ?");
            String vuParKarim = modele.dernierTexte();
            Console.ligne("le prompt d'awa parle de Lyon",
                    vuParAwa.contains("Lyon") ? "oui" : "NON", 34);
            Console.ligne("le prompt d'awa parle de Nantes",
                    vuParAwa.contains("Nantes") ? "OUI (fuite !)" : "non", 34);
            Console.ligne("le prompt de karim parle de Nantes",
                    vuParKarim.contains("Nantes") ? "oui" : "NON", 36);
            Console.ligne("le prompt de karim parle de Lyon",
                    vuParKarim.contains("Lyon") ? "OUI (fuite !)" : "non", 36);
            System.out.println();
            Console.texte("Deux conversations menees en alternance sur le MEME "
                    + "assistant, et aucune ne voit l'autre. C'est tout ce que "
                    + "fait `@MemoryId` — mais sans lui, une application web "
                    + "multi-utilisateurs melange les historiques, et c'est "
                    + "une fuite de donnees personnelles, pas un bug "
                    + "d'affichage.");
            System.out.println();
            Console.texte("⚠️ Et remarquez la premiere ligne : un seul "
                    + "parametre `@MemoryId` rend le `chatMemoryProvider` "
                    + "OBLIGATOIRE, et l'absence est refusee a la "
                    + "CONSTRUCTION du proxy — pas au premier appel. L'echec "
                    + "est immediat et lisible : c'est le bon comportement.");
            System.out.println();
            Console.texte("⚠️ Ce que LangChain4j ne fait pas : effacer. La "
                    + "memoire par defaut vit en memoire vive, sans "
                    + "expiration et sans limite de nombre. Mille "
                    + "utilisateurs, mille historiques qui ne partent "
                    + "jamais — c'est une fuite de memoire, et c'est a vous "
                    + "de fournir un `ChatMemoryStore` qui oublie.");

            Console.titre(4, "LE STREAMING : CE QU'IL CHANGE VRAIMENT");
            var flux = AiServices.builder(AssistantEnFlux.class)
                    .streamingChatModel(enFlux)
                    .build();
            modele.oublier();
            var morceaux = new ArrayList<String>();
            var attente = new CountDownLatch(1);
            long depart = System.nanoTime();
            var premierJeton = new java.util.concurrent.atomic.AtomicLong();
            flux.conseiller("Donne 3 conseils pour un entretien")
                    .onPartialResponse(morceau -> {
                        if (morceaux.isEmpty()) {
                            premierJeton.set(System.nanoTime() - depart);
                        }
                        morceaux.add(morceau);
                    })
                    .onCompleteResponse(complete -> attente.countDown())
                    .onError(erreur -> attente.countDown())
                    .start();
            boolean fini = attendre(attente);
            long total = System.nanoTime() - depart;
            modele.oublier();
            String dUnSeulCoup = AiServices.create(AssistantCarriere.class,
                    modele).conseiller("Donne 3 conseils pour un entretien");
            Console.ligne("le flux s'est-il termine", fini ? "oui" : "NON", 32);
            Console.ligne("morceaux recus",
                    String.valueOf(morceaux.size()), 32);
            Console.ligne("premier morceau",
                    "« " + (morceaux.isEmpty() ? "" : morceaux.getFirst())
                    + " »", 32);
            Console.ligne("temps jusqu'au premier jeton",
                    premierJeton.get() / 1_000_000 + " ms", 32);
            Console.ligne("temps jusqu'a la reponse complete",
                    total / 1_000_000 + " ms", 36);
            Console.ligne("texte recolle = texte d'un coup",
                    String.join("", morceaux).equals(dUnSeulCoup)
                            ? "oui" : "NON", 36);
            System.out.println();
            Console.texte("Voila le seul gain du streaming, et il est reel : "
                    + "l'utilisateur voit quelque chose apparaitre bien avant "
                    + "la fin. Le rapport entre les deux durees est ce qui "
                    + "compte pour lui.");
            System.out.println();
            Console.texte("⚠️ Ce que le flux ne change PAS : le cout, la "
                    + "latence totale, et le fait que la reponse complete "
                    + "n'existe qu'a la fin. `.start()` ameliore le RESSENTI, "
                    + "pas la mesure. Et il complique tout le reste — une "
                    + "erreur arrive dans `onError`, pas dans un `catch`, et "
                    + "un flux qu'on oublie de demarrer ne dit rien.");

            Console.titre(5, "LE MULTIMODAL : L'IMAGE VOYAGE A COTE DU TEXTE");
            byte[] scan = png(600, 850);
            String encodee = Base64.getEncoder().encodeToString(scan);
            var message = UserMessage.from(
                    TextContent.from("Extrais les competences de ce CV"),
                    ImageContent.from(Image.builder()
                            .base64Data(encodee)
                            .mimeType("image/png")
                            .build()));
            modele.oublier();
            modele.chat(List.of(message));
            var recu = (UserMessage) modele.derniersMessages().getFirst();
            Console.ligne("parties du message",
                    String.valueOf(recu.contents().size()), 30);
            Console.ligne("types des parties",
                    recu.contents().stream().map(c -> String.valueOf(c.type()))
                            .toList().toString(), 30);
            Console.ligne("le texte du message",
                    ModeleFactice.contenu(recu), 30);
            Console.ligne("l'image pese", octets(scan.length), 30);
            Console.ligne("une fois encodee en base64",
                    octets(encodee.length()), 34);
            System.out.println();
            Console.texte("Un message utilisateur n'est pas une chaine : c'est "
                    + "une LISTE de contenus. Le texte et l'image voyagent "
                    + "cote a cote, et le base64 ajoute un tiers — trois "
                    + "octets deviennent quatre caracteres. Ce poids passe sur "
                    + "le reseau a CHAQUE appel, et une conversation qui garde "
                    + "l'image dans son historique l'envoie a chaque tour.");
            System.out.println();
            Console.texte("⚠️ Savoir voir est une propriete du MODELE, pas du "
                    + "code. Celui de ce projet a recu l'image et ne l'a pas "
                    + "lue — sans la moindre erreur. Chez un vrai "
                    + "fournisseur, envoyer une image a un modele texte rend "
                    + "une erreur HTTP 400, a l'execution et jamais a la "
                    + "compilation. Le nom du modele est une dependance aussi "
                    + "serieuse qu'une version de bibliotheque.");
            System.out.println();
            Console.texte("⚠️ Et la facturation ne se compte pas en octets : "
                    + "les fournisseurs decoupent l'image en tuiles et "
                    + "facturent des jetons par tuile. C'est une grille par "
                    + "fournisseur, a lire chez lui — la seule chose que l'on "
                    + "peut dire ici sans mentir, c'est qu'on redimensionne "
                    + "AVANT d'envoyer.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le `ChatModelListener` — et pourquoi l'exemple du "
                    + "cours, qui redefinit `chat`, le rend muet.");
            System.out.println();
        }
    }

    private static boolean attendre(CountDownLatch attente) {
        try {
            return attente.await(30, TimeUnit.SECONDS);
        } catch (InterruptedException interrompu) {
            Thread.currentThread().interrupt();
            return false;
        }
    }

    /**
     * Une image PNG fabriquée à la volée — pas de fichier dans le dépôt.
     *
     * <p>Le grain est celui d'un vrai scan : sans lui, un aplat blanc se
     * compresserait en quelques kilo-octets et la mesure serait flatteuse au
     * point d'être fausse. La graine est fixe pour que le chiffre soit
     * reproductible.
     */
    private static byte[] png(int largeur, int hauteur) {
        var image = new BufferedImage(largeur, hauteur,
                BufferedImage.TYPE_INT_RGB);
        var dessin = image.createGraphics();
        dessin.setColor(java.awt.Color.WHITE);
        dessin.fillRect(0, 0, largeur, hauteur);
        dessin.setColor(java.awt.Color.DARK_GRAY);
        for (int y = hauteur / 10; y < hauteur; y += Math.max(4, hauteur / 40)) {
            dessin.fillRect(largeur / 12, y,
                    (int) (largeur * 0.7 * ((y % 7) + 3) / 10), 2);
        }
        dessin.dispose();
        var grain = new java.util.Random(31);
        for (int y = 0; y < hauteur; y++) {
            for (int x = 0; x < largeur; x++) {
                int variation = grain.nextInt(40);
                int couleur = image.getRGB(x, y);
                int r = Math.max(0, ((couleur >> 16) & 0xFF) - variation);
                int v = Math.max(0, ((couleur >> 8) & 0xFF) - variation);
                int b = Math.max(0, (couleur & 0xFF) - variation);
                image.setRGB(x, y, (r << 16) | (v << 8) | b);
            }
        }
        var tampon = new ByteArrayOutputStream();
        try {
            ImageIO.write(image, "png", tampon);
        } catch (java.io.IOException impossible) {
            throw new IllegalStateException("PNG non ecrit", impossible);
        }
        return tampon.toByteArray();
    }

    private static String octets(int nombre) {
        return nombre < 10_000 ? nombre + " o" : "%,d ko".formatted(nombre / 1024);
    }

    private static String court(String texte, int largeur) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= largeur ? plat
                : plat.substring(0, largeur - 3) + "...";
    }
}
