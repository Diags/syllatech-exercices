package fr.portail.modele;

import dev.langchain4j.agent.tool.ToolExecutionRequest;
import dev.langchain4j.data.message.AiMessage;
import dev.langchain4j.data.message.ChatMessage;
import dev.langchain4j.data.message.ToolExecutionResultMessage;
import dev.langchain4j.model.chat.Capability;
import dev.langchain4j.model.chat.ChatModel;
import dev.langchain4j.model.chat.listener.ChatModelListener;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.ChatResponse;
import dev.langchain4j.model.chat.response.ChatResponseMetadata;
import dev.langchain4j.model.output.FinishReason;
import dev.langchain4j.model.output.TokenUsage;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Function;
import org.springframework.stereotype.Component;

/**
 * Le modèle du portail — écrit à la main, et qui n'appelle personne.
 *
 * <p>C'est la pièce centrale de ce projet, et c'est <strong>un instrument de
 * mesure</strong> autant qu'un modèle. Un vrai fournisseur est une boîte
 * noire : on lui envoie une requête, il rend du texte, et ce que LangChain4j
 * a réellement mis dans cette requête reste invisible. Ici, chaque
 * {@link ChatRequest} est <em>retenue</em> — et les six chapitres impriment
 * ce que le proxy d'{@code AiServices} a fabriqué.
 *
 * <p>Ce que cela rend visible, chapitre par chapitre :
 *
 * <ul>
 *   <li>les deux messages que {@code @SystemMessage} et {@code @UserMessage}
 *       produisent, variables {@code {{…}}} déjà remplacées ;</li>
 *   <li>les <strong>instructions de format</strong> qu'un type de retour
 *       {@code record} ajoute — et le fait qu'elles changent complètement
 *       selon ce que le modèle déclare savoir faire ;</li>
 *   <li>le <strong>contexte</strong> que le {@code ContentRetriever}
 *       injecte, texte compris ;</li>
 *   <li>l'historique que la {@code ChatMemory} rejoue à chaque tour ;</li>
 *   <li>les {@code ToolSpecification} qui voyagent <em>à côté</em> des
 *       messages, jamais dedans.</li>
 * </ul>
 *
 * <p>⚠️ <strong>C'est {@code doChat} qui est redéfini, pas {@code chat}.</strong>
 * Les deux existent sur l'interface, et l'exemple du chapitre 6 du cours
 * redéfinit {@code chat(ChatRequest)}. Or {@code chat} est la méthode
 * <em>enveloppe</em> : c'est elle qui prévient les {@link ChatModelListener}
 * avant et après l'appel. La redéfinir désactive donc toute l'observabilité
 * du chapitre 6, sans erreur et sans message. Le chapitre 6 de ce projet le
 * mesure.
 *
 * <p>⚠️ <strong>Il ne comprend rien.</strong> Ses réponses viennent de règles
 * écrites ici. Ce projet ne mesure donc jamais la <em>qualité</em> d'une
 * réponse — il mesure ce que LangChain4j construit, envoie et reconstruit,
 * ce qui est précisément ce qu'un cours sur LangChain4j enseigne.
 */
@Component
public class ModeleFactice implements ChatModel {

    /** Toutes les requêtes reçues, dans l'ordre. */
    private final List<ChatRequest> recues = new CopyOnWriteArrayList<>();

    /** Les règles de réponse textuelle, essayées dans l'ordre. */
    private final List<Function<String, String>> regles = new CopyOnWriteArrayList<>();

    /**
     * Les règles qui font <strong>demander un outil</strong> plutôt que
     * répondre. Essayées avant les règles de texte.
     */
    private final List<Function<String, ToolExecutionRequest>> demandes =
            new CopyOnWriteArrayList<>();

    private final List<ChatModelListener> ecouteurs = new CopyOnWriteArrayList<>();

    /**
     * Ce que le modèle déclare savoir faire.
     *
     * <p>⚠️ Ce champ n'est pas décoratif : {@code AiServices} lit
     * {@link #supportedCapabilities()} pour décider <em>comment</em> imposer
     * un format de sortie. Vide, il écrit les instructions en toutes lettres
     * dans le prompt ; avec {@link Capability#RESPONSE_FORMAT_JSON_SCHEMA},
     * il pose un schéma JSON dans la requête et laisse le prompt intact. Le
     * chapitre 2 imprime les deux.
     */
    private final Set<Capability> capacites = new LinkedHashSet<>();

    public ModeleFactice() {
        reglesParDefaut();
    }

    // ── ce que le modele a vu ────────────────────────────────────────────

    public List<ChatRequest> recues() {
        return List.copyOf(recues);
    }

    public ChatRequest derniereRequete() {
        return recues.isEmpty() ? null : recues.getLast();
    }

    public List<ChatMessage> derniersMessages() {
        var requete = derniereRequete();
        return requete == null ? List.of() : List.copyOf(requete.messages());
    }

    /** La dernière requête, mise à plat : c'est ce que les chapitres impriment. */
    public String dernierTexte() {
        var requete = derniereRequete();
        if (requete == null) {
            return "";
        }
        var texte = new StringBuilder();
        for (var message : requete.messages()) {
            texte.append("[").append(message.type()).append("] ")
                 .append(contenu(message)).append("\n");
        }
        return texte.toString();
    }

    /**
     * Le texte d'un message, quel que soit son type.
     *
     * <p>⚠️ {@code ChatMessage} n'a pas de méthode {@code text()} commune :
     * chaque type a la sienne, et deux d'entre eux n'ont pas de texte du
     * tout. Un {@code AI} qui <em>demande</em> un outil porte sa demande dans
     * {@code toolExecutionRequests()}, et le {@code TOOL} qui répond porte
     * son résultat ailleurs encore. Les imprimer naïvement donnerait deux
     * lignes vides — et ferait croire qu'il ne s'est rien passé.
     */
    public static String contenu(ChatMessage message) {
        return switch (message) {
            case dev.langchain4j.data.message.SystemMessage systeme -> systeme.text();
            // ⚠️ `singleText()` LEVE une exception des qu'un message porte
            // autre chose que du texte — une image, par exemple. Le chapitre
            // 5 en envoie une, et c'est ainsi qu'on apprend qu'un message
            // utilisateur est une LISTE de contenus, pas une chaine.
            case dev.langchain4j.data.message.UserMessage utilisateur -> {
                var parties = new StringBuilder();
                for (var partie : utilisateur.contents()) {
                    parties.append(switch (partie) {
                        case dev.langchain4j.data.message.TextContent texte ->
                                texte.text();
                        case dev.langchain4j.data.message.ImageContent image ->
                                "(image " + image.image().mimeType() + ")";
                        default -> "(" + partie.type() + ")";
                    });
                }
                yield parties.toString();
            }
            case AiMessage ia when ia.hasToolExecutionRequests() -> {
                var demande = new StringBuilder();
                for (var appel : ia.toolExecutionRequests()) {
                    demande.append("appelle ").append(appel.name())
                           .append(appel.arguments());
                }
                yield demande.toString();
            }
            case AiMessage ia -> String.valueOf(ia.text());
            case ToolExecutionResultMessage outil ->
                    outil.toolName() + " a rendu : " + outil.text();
            default -> String.valueOf(message);
        };
    }

    public int appels() {
        return recues.size();
    }

    public void oublier() {
        recues.clear();
    }

    /** Ajoute une règle prioritaire — les chapitres s'en servent. */
    public void repondre(Function<String, String> regle) {
        regles.addFirst(regle);
    }

    /** Fait « décider » au modèle d'appeler un outil. */
    public void demanderOutil(Function<String, ToolExecutionRequest> regle) {
        demandes.addFirst(regle);
    }

    /** Branche un écouteur — le chapitre 6 s'en sert. */
    public void ecouter(ChatModelListener ecouteur) {
        ecouteurs.add(ecouteur);
    }

    /** Déclare une capacité, ce qui change la façon d'imposer un format. */
    public ModeleFactice sachant(Capability capacite) {
        capacites.add(capacite);
        return this;
    }

    /** Remet les règles d'origine, et vide toute la mémoire. */
    public void remettreAZero() {
        recues.clear();
        regles.clear();
        demandes.clear();
        ecouteurs.clear();
        capacites.clear();
        reglesParDefaut();
    }

    // ── le contrat ChatModel ─────────────────────────────────────────────

    /**
     * ⚠️ {@code doChat}, et non {@code chat} — voir la note de classe.
     */
    @Override
    public ChatResponse doChat(ChatRequest requete) {
        recues.add(requete);
        String entier = aPlat(requete);

        // Le modele ne fait que DEMANDER un outil. L'execution appartient a
        // LangChain4j, et le chapitre 4 le montre en comptant les deux cotes.
        for (var demande : demandes) {
            var appel = demande.apply(entier);
            if (appel != null) {
                return ChatResponse.builder()
                        .aiMessage(AiMessage.from(List.of(appel)))
                        .metadata(ChatResponseMetadata.builder()
                                .modelName("factice-1")
                                .finishReason(FinishReason.TOOL_EXECUTION)
                                .tokenUsage(new TokenUsage(mots(entier), 0))
                                .build())
                        .build();
            }
        }

        String reponse = null;
        for (var regle : regles) {
            reponse = regle.apply(entier);
            if (reponse != null) {
                break;
            }
        }
        if (reponse == null) {
            reponse = "Je n'ai pas d'information la-dessus.";
        }
        // Un vrai modele compte ses jetons ; celui-ci compte ses mots, ce
        // qui suffit au chapitre 6 pour mesurer une metrique qui MONTE avec
        // la taille du prompt — le point qui compte.
        return ChatResponse.builder()
                .aiMessage(AiMessage.from(reponse))
                .metadata(ChatResponseMetadata.builder()
                        .modelName("factice-1")
                        .finishReason(FinishReason.STOP)
                        .tokenUsage(new TokenUsage(mots(entier), mots(reponse)))
                        .build())
                .build();
    }

    @Override
    public List<ChatModelListener> listeners() {
        return List.copyOf(ecouteurs);
    }

    @Override
    public Set<Capability> supportedCapabilities() {
        return Set.copyOf(capacites);
    }

    /**
     * La requête entière, telle que le modèle la « lit ».
     *
     * <p>⚠️ <strong>Les messages ne sont pas toute la requête.</strong> Un
     * {@code ResponseFormat} et des {@code ToolSpecification} voyagent à
     * côté, et un vrai modèle les reçoit aussi — c'est même ainsi qu'il
     * « obéit » à un format imposé. Les règles de ce modèle doivent donc les
     * voir, sans quoi le chapitre 2 mesurerait un refus de répondre là où un
     * vrai fournisseur rendrait du JSON.
     *
     * <p>{@link #dernierTexte()}, lui, ne montre que les messages : c'est ce
     * que les chapitres impriment quand ils parlent du « prompt ».
     */
    public static String aPlat(ChatRequest requete) {
        var texte = new StringBuilder();
        for (var message : requete.messages()) {
            texte.append(contenu(message)).append("\n");
        }
        if (requete.responseFormat() != null) {
            texte.append("[format impose] ")
                 .append(requete.responseFormat()).append("\n");
        }
        if (requete.toolSpecifications() != null
                && !requete.toolSpecifications().isEmpty()) {
            texte.append("[outils proposes] ")
                 .append(requete.toolSpecifications()).append("\n");
        }
        return texte.toString();
    }

    private static int mots(String texte) {
        return texte == null || texte.isBlank() ? 0 : texte.split("\\s+").length;
    }

    // ── les reponses par defaut ──────────────────────────────────────────

    private void reglesParDefaut() {
        // ⚠️ L'ORDRE COMPTE. La regle du format structure passe en premier :
        // quand un type de retour a impose du JSON, il FAUT en rendre, sinon
        // la conversion echoue — et c'est ce que le chapitre 2 mesure en la
        // retirant.
        regles.add(ModeleFactice::sortieStructuree);
        regles.add(ModeleFactice::depuisLeContexte);
        regles.add(ModeleFactice::conseils);
    }

    /** Si la requête réclame du JSON, en rendre. */
    private static String sortieStructuree(String prompt) {
        boolean reclame = prompt.contains("JSON") || prompt.contains("json");
        if (!reclame) {
            return null;
        }
        if (prompt.contains("competences")) {
            return """
                   {"competences":["Java","Spring","PostgreSQL"],
                    "score":78,
                    "resume":"sept ans de Java et deux migrations menees"}""";
        }
        if (prompt.contains("pertinent")) {
            return "{\"pertinent\":true,\"raison\":\"la reponse cite le document\"}";
        }
        return "{}";
    }

    /**
     * Répond à partir du contexte injecté par le RAG, s'il y en a un.
     *
     * <p>Grossier et volontairement : on cherche la première ligne du
     * contexte qui partage des mots avec la question. Aucune compréhension,
     * aucune génération — mais une réponse qui <strong>dépend du
     * contexte</strong>, ce qui suffit à montrer ce que le RAG change.
     */
    private static String depuisLeContexte(String prompt) {
        int debut = prompt.indexOf("Answer using the following information");
        if (debut < 0) {
            return null;
        }
        for (var ligne : prompt.substring(debut).split("\n")) {
            if (ligne.contains("OFF-") || ligne.contains("teletravail")) {
                return "D'apres les documents fournis : " + ligne.strip();
            }
        }
        return null;
    }

    private static String conseils(String prompt) {
        if (!prompt.toLowerCase(java.util.Locale.ROOT).contains("conseil")) {
            return null;
        }
        return """
               1. Montrez un projet que vous avez mene de bout en bout.
               2. Preparez trois questions sur l'equipe et ses pratiques.
               3. Chiffrez ce que vous avez ameliore, pas ce que vous avez fait.""";
    }

    /** Ce que le modèle a retenu de son dernier appel, pour les tableaux. */
    public List<String> typesDesMessages() {
        var types = new ArrayList<String>();
        for (var message : derniersMessages()) {
            types.add(String.valueOf(message.type()));
        }
        return types;
    }
}
