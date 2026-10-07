package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.modele.TranscriptionFactice;
import fr.portail.rag.Corpus;
import java.awt.image.BufferedImage;
import java.io.ByteArrayOutputStream;
import java.util.Base64;
import java.util.List;
import javax.imageio.ImageIO;
import org.springframework.ai.audio.transcription.AudioTranscriptionPrompt;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.vectorstore.SearchRequest;
import org.springframework.ai.vectorstore.VectorStore;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.util.MimeTypeUtils;

/**
 * Chapitre 5 — Audio, image et multimodal.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre5Multimodal
 * </pre>
 *
 * <p>« {@code media()} attache l'image au prompt. » Attachée <em>où</em> ?
 * Ce chapitre pèse ce qui part : l'image ne rejoint pas le texte, elle voyage
 * à côté, et elle est encodée — ce qui change la facture et la latence bien
 * plus que la longueur de votre phrase.
 *
 * <p>Il montre aussi les deux limites que l'abstraction ne peut pas cacher :
 * un modèle qui ne sait pas voir reçoit l'image quand même, et la
 * transcription n'est pas un {@code ChatModel} du tout.
 *
 * <p>⚠️ <strong>Ce chapitre ne transcrit rien et ne lit aucune image.</strong>
 * Il n'y a pas de fournisseur ici. Ce qui est mesuré est la plomberie — les
 * types, les tailles, les octets — et elle est identique avec un vrai
 * fournisseur. La qualité, elle, ne se mesure qu'avec un vrai modèle.
 */
public final class Chapitre5Multimodal {

    private Chapitre5Multimodal() {
    }

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var transcription = banc.bean(TranscriptionFactice.class);
            var base = banc.bean(VectorStore.class);
            var client = ChatClient.builder(modele).build();

            Console.titre(1, "CE QU'UNE IMAGE DEVIENT DANS UN MESSAGE");
            byte[] vignette = png(64, 64);
            modele.oublier();
            client.prompt()
                    .user(u -> u.text("Extrais les competences de ce CV")
                            .media(MimeTypeUtils.IMAGE_PNG,
                                    new ByteArrayResource(vignette)))
                    .call().content();
            var medias = modele.derniersMedias();
            Console.ligne("messages envoyes",
                    String.valueOf(modele.derniersMessages().size()), 30);
            Console.ligne("medias joints", String.valueOf(medias.size()), 30);
            Console.ligne("type declare",
                    String.valueOf(medias.getFirst().getMimeType()), 30);
            Console.ligne("le prompt EN TEXTE",
                    modele.dernierTexte().strip(), 30);
            Console.ligne("l'image y apparait-elle",
                    modele.dernierTexte().contains("PNG")
                            || modele.dernierTexte().contains("image")
                            ? "oui" : "NON", 30);
            System.out.println();
            Console.texte("Un seul message, du texte inchange, et une image a "
                    + "cote. C'est exactement la structure des API "
                    + "multimodales : un message est une LISTE de parties, "
                    + "dont certaines sont du texte et d'autres des images. "
                    + "Spring AI vous epargne ce detail — jusqu'au moment ou "
                    + "il faut comprendre une facture.");

            Console.titre(2, "CE QUE L'IMAGE PESE VRAIMENT");
            byte[] scan = png(1240, 1754);
            var lignes = List.of(
                    List.of("vignette 64 x 64", octets(vignette.length),
                            octets(base64(vignette))),
                    List.of("page A4 scannee 150 ppp", octets(scan.length),
                            octets(base64(scan))));
            Console.tableau(List.of("ce qu'on joint", "octets",
                    "une fois encode en base64"), lignes,
                    List.of(26, 14, 26));
            Console.ligne("le prompt texte, lui", modele.dernierTexte()
                    .strip().length() + " caracteres", 30);
            System.out.println();
            Console.texte("Le base64 ajoute un tiers : trois octets deviennent "
                    + "quatre caracteres. Une page scannee part donc plus "
                    + "lourde qu'elle n'est sur le disque, et ce poids passe "
                    + "sur le reseau a CHAQUE appel — une conversation de dix "
                    + "tours qui garde l'image dans son historique l'envoie "
                    + "dix fois.");
            System.out.println();
            Console.texte("Les deux images de ce tableau sont fabriquees ici, "
                    + "avec le grain d'un vrai scan : sans ce bruit, un aplat "
                    + "blanc se compresserait en quelques kilo-octets et la "
                    + "mesure serait flatteuse. Le chiffre exact depend du "
                    + "document ; l'ordre de grandeur, lui, est le bon.");
            System.out.println();
            Console.texte("⚠️ La facturation, elle, ne se compte pas en "
                    + "octets : les fournisseurs decoupent l'image en tuiles "
                    + "et facturent des jetons par tuile, selon la resolution "
                    + "demandee. C'est une grille par fournisseur, a lire chez "
                    + "lui — la seule chose que l'on peut dire ici sans "
                    + "mentir, c'est qu'une image coute beaucoup plus qu'une "
                    + "phrase, et qu'on redimensionne AVANT d'envoyer.");

            Console.titre(3, "UN MODELE QUI NE SAIT PAS VOIR");
            modele.oublier();
            String sansImage = client.prompt()
                    .user("Extrais les competences de ce CV").call().content();
            modele.oublier();
            String avecImage = client.prompt()
                    .user(u -> u.text("Extrais les competences de ce CV")
                            .media(MimeTypeUtils.IMAGE_PNG,
                                    new ByteArrayResource(scan)))
                    .call().content();
            Console.ligne("sans image", court(sansImage), 22);
            Console.ligne("avec image", court(avecImage), 22);
            Console.ligne("image recue par le modele",
                    String.valueOf(modele.derniersMedias().size()), 30);
            Console.ligne("reponses identiques",
                    sansImage.equals(avecImage) ? "oui" : "non", 30);
            System.out.println();
            Console.texte("Le modele de ce projet ne regarde que le texte. Il "
                    + "a recu l'image, ne l'a pas lue, et a repondu comme si "
                    + "elle n'existait pas — sans la moindre erreur.");
            System.out.println();
            Console.texte("⚠️ C'est le piege du multimodal, et il ne vient pas "
                    + "de ce projet. `ChatClient` compile avec n'importe quel "
                    + "`ChatModel` ; savoir lire une image est une propriete "
                    + "du MODELE, pas du code. Chez un vrai fournisseur, "
                    + "envoyer une image a un modele texte rend une erreur "
                    + "HTTP 400 — a l'execution, en production, et jamais a la "
                    + "compilation.");
            System.out.println();
            Console.texte("La regle pratique : le nom du modele est une "
                    + "dependance aussi serieuse qu'une version de "
                    + "bibliotheque. On l'ecrit dans la configuration, on le "
                    + "teste, et on ne le change pas sans relire ce qu'on lui "
                    + "envoie.");

            Console.titre(4, "LA TRANSCRIPTION N'EST PAS UN `ChatModel`");
            modele.oublier();
            var reponse = transcription.call(new AudioTranscriptionPrompt(
                    new ByteArrayResource("des octets d'audio".getBytes())));
            Console.ligne("le modele de transcription",
                    transcription.getClass().getSimpleName(), 32);
            // ⚠️ `transcription instanceof ChatModel` NE COMPILE PAS, et la
            // raison vaut la lecture : les deux interfaces etendent
            // `Model<REQ, RES>` avec des types differents, et une classe Java
            // ne peut pas implementer deux fois la meme interface generique.
            // Le compilateur PROUVE donc l'exclusion — il faut passer par
            // Object pour seulement poser la question a l'execution.
            Object vuCommeObjet = transcription;
            Console.ligne("est-il un ChatModel ?",
                    vuCommeObjet instanceof ChatModel ? "oui" : "NON", 32);
            Console.ligne("ce qu'il prend",
                    AudioTranscriptionPrompt.class.getSimpleName(), 32);
            Console.ligne("ce qu'il rend",
                    reponse.getClass().getSimpleName(), 32);
            Console.ligne("appels au modele de chat pendant",
                    String.valueOf(modele.appels()), 34);
            System.out.println();
            Console.sousTitre("La transcription obtenue :");
            Console.bloc(reponse.getResult().getOutput(), 6);
            System.out.println();
            Console.texte("Deux interfaces, deux hierarchies, et le "
                    + "compilateur le PROUVE : ecrire "
                    + "`transcription instanceof ChatModel` ne compile meme "
                    + "pas. Les deux etendent `Model<REQ, RES>` avec des "
                    + "types differents, et une classe ne peut pas "
                    + "implementer deux fois la meme interface generique. Il "
                    + "a fallu passer par `Object` pour poser la question a "
                    + "l'execution.");
            System.out.println();
            Console.texte("`ChatClient.builder(transcription)` ne compile pas "
                    + "davantage, et c'est volontaire. Une transcription "
                    + "n'est pas une conversation — elle n'a ni message "
                    + "systeme, ni historique, ni outils.");
            System.out.println();
            Console.texte("C'est pourquoi le cours parle d'un « modele "
                    + "dedie ». En pratique, cela veut dire une seconde "
                    + "dependance, une seconde cle, une seconde ligne de "
                    + "facture, et un second point de panne.");

            Console.titre(5, "ENCHAINER : TRANSCRIRE, PUIS CHERCHER");
            String transcrit = reponse.getResult().getOutput();
            var trouves = base.similaritySearch(SearchRequest.builder()
                    .query(transcrit).topK(1).build());
            Console.ligne("longueur de la transcription",
                    transcrit.length() + " caracteres", 32);
            Console.ligne("documents indexes",
                    String.valueOf(Corpus.OFFRES.size()), 32);
            Console.ligne("offre la plus proche", trouves.isEmpty() ? "aucune"
                    : String.valueOf(trouves.getFirst().getMetadata()
                            .get("reference")), 32);
            System.out.println();
            Console.texte("Voila l'enchainement que le cours annonce : la voix "
                    + "devient du texte, le texte devient un vecteur, le "
                    + "vecteur trouve une offre. Aucune de ces trois etapes ne "
                    + "connait la precedente — ce sont trois modeles, relies "
                    + "par du texte.");
            System.out.println();
            Console.texte("⚠️ Et les erreurs s'additionnent au lieu de se "
                    + "compenser. Un mot mal transcrit devient un mot mal "
                    + "cherche, puis un document mal remonte, puis une reponse "
                    + "fausse — et plus rien, en bout de chaine, ne rappelle "
                    + "que tout est parti d'un enregistrement bruite.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("La metrique `gen_ai.client.token.usage` dans un "
                    + "vrai registre Micrometer, un modele qui en juge un "
                    + "autre, et ce que coute une politique de reessai.");
            System.out.println();
        }
    }

    /**
     * Une image PNG fabriquée à la volée — pas de fichier dans le dépôt.
     *
     * <p>Le contenu n'a aucune importance : ce qui est mesuré est le poids
     * d'un PNG de cette taille, et le fait qu'il voyage encodé. Un aplat gris
     * avec quelques bandes noires compresse comme un scan de texte, ce qui
     * rend la mesure honnête plutôt que flatteuse.
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
        // ⚠️ Le grain d'un vrai scan. Sans lui, un aplat blanc avec des
        // barres noires se compresse en quelques kilo-octets, et la mesure
        // de la section 2 serait flatteuse au point d'etre fausse : un
        // document numerise porte du bruit de capteur, et c'est CE bruit qui
        // pese. La graine est fixe pour que la mesure soit reproductible.
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

    private static int base64(byte[] donnees) {
        return Base64.getEncoder().encodeToString(donnees).length();
    }

    private static String octets(int nombre) {
        return nombre < 10_000 ? nombre + " o"
                : "%,d ko".formatted(nombre / 1024);
    }

    private static String court(String texte) {
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 44 ? plat : plat.substring(0, 41) + "...";
    }
}
