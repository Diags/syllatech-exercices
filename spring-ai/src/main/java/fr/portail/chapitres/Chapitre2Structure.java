package fr.portail.chapitres;

import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import java.util.List;
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.chat.client.advisor.MessageChatMemoryAdvisor;
import org.springframework.ai.chat.memory.MessageWindowChatMemory;

/**
 * Chapitre 2 — Prompts avancés et sorties structurées.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2Structure
 * </pre>
 *
 * <p>« Spring AI convertit automatiquement la réponse en record grâce à
 * {@code entity()}. » Automatiquement, oui — mais comment ? Ce chapitre
 * imprime ce que {@code entity()} <strong>ajoute au prompt</strong> : un
 * schéma JSON complet, écrit par Spring AI et collé à la fin de votre
 * message. Le modèle ne devine rien ; on lui dicte la forme.
 *
 * <p>Et il mesure ce qui arrive quand le modèle n'obéit pas — car rien ne
 * l'y oblige.
 */
public final class Chapitre2Structure {

    private Chapitre2Structure() {
    }

    /** Ce que l'on veut obtenir du modèle : un objet, pas du texte. */
    public record AnalyseCV(String pointsForts, List<String> competences,
                            int score) {
    }

    private static final String CV = """
            Sept ans en Java, dont trois sur Spring Boot. A mene deux
            migrations de monolithe vers des services. Parle couramment
            anglais. Cherche un poste a Lyon.""";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);
            var client = ChatClient.builder(modele).build();

            Console.titre(1, "CE QUE `entity()` AJOUTE A VOTRE PROMPT");
            modele.oublier();
            var analyse = client.prompt()
                    .user(u -> u.text("Analyse ce CV : {cv}").param("cv", CV))
                    .call()
                    .entity(AnalyseCV.class);
            String envoye = modele.dernierTexte();
            Console.ligne("votre message", "Analyse ce CV : {cv}", 26);
            Console.ligne("ce qui est parti",
                    envoye.length() + " caracteres", 26);
            System.out.println();
            Console.sousTitre("Le prompt complet, tel que le modele l'a recu :");
            Console.bloc(envoye, 6);
            System.out.println();
            Console.texte("Tout ce qui suit votre phrase a ete ecrit par "
                    + "Spring AI. C'est un schema JSON, avec les noms exacts "
                    + "des composants du record et leurs types — et "
                    + "l'instruction de ne rendre QUE cela, sans balise de "
                    + "code ni explication.");
            System.out.println();
            Console.texte("« Automatiquement » veut donc dire : le prompt est "
                    + "ecrit pour vous, et la reponse est relue pour vous. Le "
                    + "modele, lui, n'a aucune garantie a offrir.");

            Console.titre(2, "L'OBJET OBTENU");
            Console.ligne("type rendu", analyse.getClass().getSimpleName(), 22);
            Console.ligne("pointsForts", analyse.pointsForts(), 22);
            Console.ligne("competences", String.valueOf(analyse.competences()), 22);
            Console.ligne("score", String.valueOf(analyse.score()), 22);
            System.out.println();
            Console.texte("Un `record` Java, avec un `int` qui est vraiment un "
                    + "`int`. Le code appelant peut le trier, le comparer, le "
                    + "stocker — ce qu'on ne fait pas avec un paragraphe.");

            Console.titre(3, "ET SI LE MODELE N'OBEIT PAS ?");
            var desobeissant = new ModeleFactice();
            desobeissant.repondre(texte -> "Bien sur ! Voici l'analyse : ce "
                    + "candidat a un bon profil Java.");
            var clientBis = ChatClient.builder(desobeissant).build();
            String verdict;
            try {
                clientBis.prompt().user("Analyse ce CV : " + CV)
                        .call().entity(AnalyseCV.class);
                verdict = "converti sans erreur";
            } catch (RuntimeException erreur) {
                verdict = erreur.getClass().getSimpleName() + " — "
                          + court(erreur.getMessage());
            }
            Console.ligne("le modele repond du texte libre", verdict, 38);
            System.out.println();
            Console.texte("La conversion echoue, et elle echoue BRUYAMMENT — "
                    + "c'est le bon comportement. Ce qui compte est de savoir "
                    + "que le cas existe : un modele qui ajoute une phrase de "
                    + "politesse avant son JSON casse votre application, et "
                    + "aucun type Java ne vous en protege.");
            System.out.println();
            Console.texte("En production, cela se traite comme un appel reseau "
                    + "qui echoue : un reessai, et une valeur de repli. Le "
                    + "chapitre 6 y revient.");

            Console.titre(4, "LE TEMPLATE EST UN PIEGE A ACCOLADES");
            modele.oublier();
            String cvAvecAccolades = "Maitrise les templates : ecrit des "
                    + "expressions comme {utilisateur} dans ses vues.";
            String avecParam;
            try {
                client.prompt()
                        .user(u -> u.text("Analyse ce CV : {cv}")
                                .param("cv", cvAvecAccolades))
                        .call().content();
                avecParam = "passe — la substitution n'est faite qu'une fois";
            } catch (RuntimeException erreur) {
                avecParam = "ECHEC : " + erreur.getClass().getSimpleName();
            }
            Console.ligne("un CV qui contient `{utilisateur}`", avecParam, 40);
            String concatene;
            try {
                client.prompt()
                        .user(u -> u.text("Analyse ce CV : " + cvAvecAccolades))
                        .call().content();
                concatene = "passe";
            } catch (RuntimeException erreur) {
                concatene = "ECHEC : " + erreur.getClass().getSimpleName();
            }
            Console.ligne("le meme CV, concatene dans le texte", concatene, 40);
            String melange;
            try {
                client.prompt()
                        .user(u -> u.text("Analyse ce CV : " + cvAvecAccolades
                                        + " pour le poste {poste}")
                                .param("poste", "developpeur"))
                        .call().content();
                melange = "passe";
            } catch (RuntimeException erreur) {
                melange = "ECHEC : " + erreur.getClass().getSimpleName();
            }
            Console.ligne("concatene ET un vrai parametre a cote", melange, 40);
            System.out.println();
            Console.texte("Les deux premieres lignes passent, et la troisieme "
                    + "echoue. La difference : des qu'UN parametre existe, "
                    + "Spring AI rend le texte comme un template — et bute "
                    + "sur `{utilisateur}`, qui vient des donnees et pour "
                    + "lequel personne n'a fourni de valeur.");
            System.out.println();
            Console.texte("C'est exactement la comparaison du cours avec un "
                    + "`PreparedStatement`. Ce qui entre par `param()` est "
                    + "une VALEUR, jamais du texte de template ; ce qu'on "
                    + "concatene devient du template, et un CV contenant une "
                    + "accolade fait tomber la requete. La regle pratique : "
                    + "tout ce qui vient de l'exterieur passe par "
                    + "`param()`.");

            Console.titre(5, "LA MEMOIRE DE CONVERSATION");
            var memoire = MessageWindowChatMemory.builder().maxMessages(10).build();
            var conversant = ChatClient.builder(modele)
                    .defaultAdvisors(MessageChatMemoryAdvisor.builder(memoire).build())
                    .build();
            modele.oublier();
            var lignes = new java.util.ArrayList<List<String>>();
            String[] tours = {
                "Je cherche un poste a Lyon.",
                "Et le salaire ?",
                "Merci, et le teletravail ?",
            };
            for (var tour : tours) {
                conversant.prompt().user(tour)
                        .advisors(a -> a.param(
                                org.springframework.ai.chat.memory.ChatMemory
                                        .CONVERSATION_ID, "awa"))
                        .call().content();
                lignes.add(List.of(court(tour),
                        String.valueOf(modele.derniersMessages().size()),
                        String.valueOf(modele.dernierTexte().length())));
            }
            Console.tableau(List.of("le tour de parole", "messages envoyes",
                    "caracteres"), lignes, List.of(34, 18, 14));
            System.out.println();
            Console.texte("Le troisieme tour envoie cinq messages pour une "
                    + "question de trois mots. C'est ce que `ChatMemory` "
                    + "fait : il rejoue TOUT l'historique a chaque appel, "
                    + "parce qu'un modele ne se souvient de rien entre deux "
                    + "requetes.");
            System.out.println();
            Console.texte("La consequence est financiere. Une conversation de "
                    + "vingt tours facture vingt fois le debut de la "
                    + "conversation. `MessageWindowChatMemory` borne la "
                    + "fenetre — ici dix messages — et c'est une decision de "
                    + "cout autant que de pertinence.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le RAG : ce qu'une recherche par similarite "
                    + "trouve, ce que l'advisor colle dans le prompt, et ce "
                    + "que le modele repond avec et sans.");
            System.out.println();
        }
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 32 ? plat : plat.substring(0, 29) + "...";
    }
}
