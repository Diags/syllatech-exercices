package fr.portail.chapitres;

import dev.langchain4j.model.chat.Capability;
import dev.langchain4j.service.AiServices;
import fr.portail.commun.Banc;
import fr.portail.commun.Console;
import fr.portail.modele.ModeleFactice;
import fr.portail.service.AnalyseurCV;
import fr.portail.service.AssistantCarriere;
import java.util.List;

/**
 * Chapitre 2 — AiServices : les interfaces IA déclaratives.
 *
 * <pre>
 * mvn -q compile exec:java -Dexec.mainClass=fr.portail.chapitres.Chapitre2AiServices
 * </pre>
 *
 * <p>« Déclarez un {@code record} comme type de retour, et LangChain4j impose
 * au modèle un schéma JSON correspondant. » Impose <em>comment</em> ? Ce
 * chapitre imprime les <strong>deux</strong> façons — car il y en a deux, et
 * elles ne se ressemblent pas du tout.
 *
 * <p>Il mesure aussi ce qui arrive quand le modèle n'obéit pas, et ce que
 * les accolades doubles font d'un CV qui en contient.
 */
public final class Chapitre2AiServices {

    private Chapitre2AiServices() {
    }

    private static final String CV = """
            Sept ans en Java, dont trois sur Spring Boot. A mene deux
            migrations de monolithe vers des services. Parle couramment
            anglais. Cherche un poste a Lyon.""";

    public static void main(String[] args) {
        Console.utf8();

        try (var banc = Banc.demarrer()) {
            var modele = banc.bean(ModeleFactice.class);

            Console.titre(1, "CE QU'UN TYPE DE RETOUR AJOUTE AU PROMPT");
            var analyseur = AiServices.create(AnalyseurCV.class, modele);
            modele.oublier();
            var analyse = analyseur.analyser("developpeuse Java senior", CV);
            String sansCapacite = modele.dernierTexte();
            Console.sousTitre("Le prompt complet, tel que le modele l'a recu :");
            Console.bloc(sansCapacite, 6);
            System.out.println();
            Console.texte("Tout ce qui suit votre CV a ete ecrit par "
                    + "LangChain4j. C'est un schema JSON, avec les noms exacts "
                    + "des composants du record et leurs types — et "
                    + "l'instruction de ne rendre QUE cela.");
            System.out.println();
            Console.texte("« Automatiquement » veut donc dire : le prompt est "
                    + "ecrit pour vous, et la reponse est relue pour vous. Le "
                    + "modele, lui, n'a aucune garantie a offrir.");

            Console.titre(2, "LA MEME DEMANDE, UN AUTRE MODELE : TOUT CHANGE");
            var capable = new ModeleFactice()
                    .sachant(Capability.RESPONSE_FORMAT_JSON_SCHEMA);
            var analyseurBis = AiServices.create(AnalyseurCV.class, capable);
            analyseurBis.analyser("developpeuse Java senior", CV);
            String avecCapacite = capable.dernierTexte();
            Console.sousTitre("Le prompt, cette fois :");
            Console.bloc(avecCapacite, 6);
            System.out.println();
            var format = capable.derniereRequete().responseFormat();
            Console.ligne("un format de reponse est-il pose ?",
                    format == null ? "NON" : String.valueOf(format.type()), 38);
            if (format != null && format.jsonSchema() != null) {
                Console.sousTitre("Le schema, cette fois hors du prompt :");
                Console.bloc(String.valueOf(format.jsonSchema()), 6);
            }
            System.out.println();
            Console.tableau(List.of("ce que le modele declare",
                    "prompt envoye", "schema"), List.of(
                    List.of("rien", sansCapacite.length() + " caracteres",
                            "dans le texte"),
                    List.of("RESPONSE_FORMAT_JSON_SCHEMA",
                            avecCapacite.length() + " caracteres",
                            format == null ? "dans le texte"
                                    : "dans la requete")),
                    List.of(30, 18, 16));
            System.out.println();
            Console.texte("Le meme code Java, la meme interface, le meme "
                    + "record — et deux prompts differents. LangChain4j lit "
                    + "`supportedCapabilities()` sur le modele : s'il sait "
                    + "recevoir un schema JSON, le schema voyage DANS LA "
                    + "REQUETE, a cote des messages, et le prompt reste "
                    + "propre. Sinon, les instructions sont ecrites en toutes "
                    + "lettres a la fin du message utilisateur.");
            System.out.println();
            Console.texte("⚠️ Cela se paie et se debogue differemment. Dans le "
                    + "premier cas, vous facturez le schema a chaque appel et "
                    + "le modele peut l'ignorer ; dans le second, c'est le "
                    + "fournisseur qui garantit la forme, et le prompt reste "
                    + "lisible. Changer de modele change donc le prompt sans "
                    + "que vous ayez touche a une ligne.");

            Console.titre(3, "L'OBJET OBTENU");
            Console.ligne("type rendu", analyse.getClass().getSimpleName(), 22);
            Console.ligne("competences",
                    String.valueOf(analyse.competences()), 22);
            Console.ligne("score", String.valueOf(analyse.score()), 22);
            Console.ligne("resume", analyse.resume(), 22);
            System.out.println();
            Console.texte("Un `record` Java, avec un `int` qui est vraiment un "
                    + "`int`. Le code appelant peut le trier, le comparer, le "
                    + "stocker — ce qu'on ne fait pas avec un paragraphe.");

            Console.titre(4, "ET SI LE MODELE N'OBEIT PAS ?");
            var desobeissant = new ModeleFactice();
            desobeissant.repondre(texte -> "Bien sur ! Voici l'analyse : ce "
                    + "candidat a un bon profil Java.");
            var fragile = AiServices.create(AnalyseurCV.class, desobeissant);
            String verdict;
            try {
                fragile.analyser("developpeuse Java", CV);
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

            Console.titre(5, "LES ACCOLADES DOUBLES SONT UN PIEGE A DONNEES");
            var assistant = AiServices.create(AssistantCarriere.class, modele);
            modele.oublier();
            assistant.conseilCible("developpeur Java", "Lyon");
            Console.sousTitre("Un template rempli par `@V` :");
            Console.bloc(modele.dernierTexte(), 6);
            String avecAccolades;
            try {
                modele.oublier();
                assistant.conseilCible(
                        "developpeur qui ecrit des vues {{utilisateur}}",
                        "Lyon");
                avecAccolades = "passe — la substitution n'est faite qu'une fois";
            } catch (RuntimeException erreur) {
                avecAccolades = "ECHEC : " + erreur.getClass().getSimpleName();
            }
            Console.ligne("une valeur contenant `{{utilisateur}}`",
                    avecAccolades, 42);
            Console.ligne("les accolades sont-elles parties telles quelles",
                    modele.dernierTexte().contains("{{utilisateur}}")
                            ? "oui" : "NON", 50);
            System.out.println();
            Console.texte("C'est la comparaison du cours avec un "
                    + "`PreparedStatement`, et elle tient : ce qui entre par "
                    + "`@V` est une VALEUR, relue une seule fois. Les "
                    + "accolades venues des donnees restent des accolades.");
            System.out.println();
            Console.texte("⚠️ Deux differences avec Spring AI, a ne pas "
                    + "melanger : les accolades sont DOUBLES ici "
                    + "(`{{poste}}`), et la valeur d'un `@V` n'est jamais "
                    + "relue comme un template. Concatener reste, en "
                    + "revanche, la mauvaise idee habituelle — tout ce qui "
                    + "vient de l'exterieur passe par `@V`.");

            Console.titre(6, "CE QUE LE CHAPITRE SUIVANT MESURE");
            Console.texte("Le RAG : ce que `DocumentSplitters.recursive(300, "
                    + "30)` fabrique vraiment, ce que le retriever remonte, "
                    + "et le texte exact qu'il colle dans votre message.");
            System.out.println();
        }
    }

    private static String court(String texte) {
        if (texte == null) {
            return "(sans message)";
        }
        String plat = texte.replaceAll("\\s+", " ").strip();
        return plat.length() <= 46 ? plat : plat.substring(0, 43) + "...";
    }
}
