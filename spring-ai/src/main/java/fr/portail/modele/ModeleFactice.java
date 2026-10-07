package fr.portail.modele;

import io.micrometer.observation.ObservationRegistry;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.function.Function;
import org.springframework.ai.chat.messages.AssistantMessage;
import org.springframework.ai.chat.messages.Message;
import org.springframework.ai.chat.messages.ToolResponseMessage;
import org.springframework.ai.chat.metadata.ChatGenerationMetadata;
import org.springframework.ai.chat.metadata.ChatResponseMetadata;
import org.springframework.ai.chat.metadata.DefaultUsage;
import org.springframework.ai.chat.model.ChatModel;
import org.springframework.ai.chat.model.ChatResponse;
import org.springframework.ai.chat.model.Generation;
import org.springframework.ai.chat.observation.ChatModelObservationContext;
import org.springframework.ai.chat.observation.ChatModelObservationConvention;
import org.springframework.ai.chat.observation.ChatModelObservationDocumentation;
import org.springframework.ai.chat.observation.DefaultChatModelObservationConvention;
import org.springframework.ai.chat.prompt.ChatOptions;
import org.springframework.ai.chat.prompt.Prompt;
import org.springframework.ai.content.Media;
import org.springframework.ai.content.MediaContent;
import org.springframework.ai.model.tool.ToolCallingChatOptions;
import org.springframework.ai.tool.ToolCallback;
import org.springframework.stereotype.Component;

/**
 * Le modèle du portail — écrit à la main, et qui n'appelle personne.
 *
 * <p>C'est la pièce centrale de ce projet, et c'est <strong>un instrument de
 * mesure</strong> autant qu'un modèle. Un vrai fournisseur est une boîte
 * noire : on lui envoie un prompt, il rend du texte, et ce que Spring AI a
 * réellement mis dans ce prompt reste invisible. Ici, chaque appel est
 * <em>retenu</em> — et les six chapitres impriment ce que
 * {@code ChatClient} a fabriqué.
 *
 * <p>Ce que cela rend visible, chapitre par chapitre :
 *
 * <ul>
 *   <li>le message système que {@code defaultSystem()} ajoute ;</li>
 *   <li>les <strong>instructions de format</strong> que {@code entity()}
 *       colle à la fin du prompt — un schéma JSON complet, que personne
 *       n'écrit à la main ;</li>
 *   <li>le <strong>contexte</strong> que le {@code QuestionAnswerAdvisor}
 *       injecte, texte compris ;</li>
 *   <li>l'historique que {@code ChatMemory} rejoue à chaque tour.</li>
 * </ul>
 *
 * <p>⚠️ <strong>Il ne comprend rien.</strong> Ses réponses viennent de règles
 * écrites ici. Ce projet ne mesure donc jamais la <em>qualité</em> d'une
 * réponse — il mesure ce que Spring AI construit, envoie et reconstruit, ce
 * qui est précisément ce qu'un cours sur Spring AI enseigne.
 */
@Component
public class ModeleFactice implements ChatModel {

    /** Tous les prompts reçus, dans l'ordre. */
    private final List<Prompt> recus = new CopyOnWriteArrayList<>();

    /**
     * Les règles de réponse, essayées dans l'ordre.
     *
     * <p>Chacune regarde le prompt entier et rend une réponse, ou
     * {@code null} pour laisser la main à la suivante. Les chapitres en
     * ajoutent quand ils ont besoin d'une réponse précise — c'est ainsi que
     * le chapitre 4 fait « demander » un outil au modèle.
     */
    private final List<Function<String, String>> regles = new CopyOnWriteArrayList<>();

    /**
     * Les règles qui font <strong>demander un outil</strong> plutôt que
     * répondre.
     *
     * <p>Essayées avant les règles de texte. Une règle rend un
     * {@link AssistantMessage.ToolCall} — exactement ce qu'un vrai modèle
     * renvoie quand il décide d'appeler une fonction : un nom et des
     * arguments en JSON, rien d'autre. Ce n'est pas le modèle qui exécute
     * quoi que ce soit.
     */
    private final List<Function<String, AssistantMessage.ToolCall>> demandes =
            new CopyOnWriteArrayList<>();

    public ModeleFactice() {
        reglesParDefaut();
    }

    // ── ce que le modele a vu ────────────────────────────────────────────

    public List<Prompt> recus() {
        return List.copyOf(recus);
    }

    public Prompt dernierPrompt() {
        return recus.isEmpty() ? null : recus.getLast();
    }

    /** Le dernier prompt, mis à plat : c'est ce que les chapitres impriment. */
    public String dernierTexte() {
        var prompt = dernierPrompt();
        if (prompt == null) {
            return "";
        }
        var texte = new StringBuilder();
        for (var message : prompt.getInstructions()) {
            texte.append("[").append(message.getMessageType()).append("] ")
                 .append(message.getText()).append("\n");
        }
        return texte.toString();
    }

    public List<Message> derniersMessages() {
        var prompt = dernierPrompt();
        return prompt == null ? List.of() : List.copyOf(prompt.getInstructions());
    }

    public int appels() {
        return recus.size();
    }

    public void oublier() {
        recus.clear();
    }

    /** Ajoute une règle prioritaire — les chapitres s'en servent. */
    public void repondre(Function<String, String> regle) {
        regles.addFirst(regle);
    }

    /** Fait « décider » au modèle d'appeler un outil. */
    public void demanderOutil(Function<String, AssistantMessage.ToolCall> regle) {
        demandes.addFirst(regle);
    }

    /** Remet les règles d'origine, et vide la mémoire des appels. */
    public void remettreAZero() {
        recus.clear();
        regles.clear();
        demandes.clear();
        reglesParDefaut();
    }

    /**
     * Les outils que {@code ChatClient} a joints au dernier appel.
     *
     * <p>⚠️ <strong>Ils ne sont pas dans le prompt.</strong> Ils voyagent
     * dans les <em>options</em>, sous forme de {@link ToolCallback} — et
     * c'est le fournisseur qui les traduit en payload HTTP. C'est pourquoi
     * {@link #dernierTexte()} ne les montre pas : le chapitre 4 doit les
     * demander ici.
     */
    public List<ToolCallback> derniersOutils() {
        var prompt = dernierPrompt();
        if (prompt == null
                || !(prompt.getOptions() instanceof ToolCallingChatOptions o)) {
            return List.of();
        }
        return List.copyOf(o.getToolCallbacks());
    }

    /**
     * Les médias joints au dernier prompt — images, audio, documents.
     *
     * <p>Même remarque que pour les outils : ils ne sont pas dans le texte.
     * Un {@code UserMessage} porte un texte <em>et</em> une liste de
     * {@link Media}, et c'est le fournisseur qui décide comment les coder
     * dans sa requête HTTP. Le chapitre 5 les compte et les pèse ici.
     */
    public List<Media> derniersMedias() {
        var trouves = new ArrayList<Media>();
        for (var message : derniersMessages()) {
            if (message instanceof MediaContent porteur) {
                trouves.addAll(porteur.getMedia());
            }
        }
        return trouves;
    }

    /**
     * La conversation du dernier prompt, appels d'outils compris.
     *
     * <p>{@link #dernierTexte()} suffit tant que la conversation n'est que du
     * texte. Dès qu'un outil entre en jeu, deux messages n'ont plus de texte
     * du tout : l'{@code ASSISTANT} qui <em>demande</em> l'outil porte sa
     * demande dans {@code getToolCalls()}, et le {@code TOOL} qui répond
     * porte son résultat dans {@code getResponses()}. Les imprimer par
     * {@code getText()} donnerait deux lignes vides — et ferait croire qu'il
     * ne s'est rien passé.
     */
    public String conversation() {
        var prompt = dernierPrompt();
        if (prompt == null) {
            return "";
        }
        var texte = new StringBuilder();
        for (var message : prompt.getInstructions()) {
            texte.append("[").append(message.getMessageType()).append("] ");
            if (message instanceof AssistantMessage assistant
                    && assistant.hasToolCalls()) {
                for (var appel : assistant.getToolCalls()) {
                    texte.append("appelle ").append(appel.name())
                         .append(appel.arguments());
                }
            } else if (message instanceof ToolResponseMessage outil) {
                for (var reponse : outil.getResponses()) {
                    texte.append(reponse.name()).append(" a rendu : ")
                         .append(reponse.responseData());
                }
            } else {
                texte.append(message.getText());
            }
            texte.append("\n");
        }
        return texte.toString();
    }

    // ── l'observabilite ──────────────────────────────────────────────────

    /**
     * Le registre d'observations — muet par défaut.
     *
     * <p>⚠️ <strong>C'est le fournisseur qui instrumente, pas Spring AI.</strong>
     * La métrique {@code gen_ai.client.token.usage} que le chapitre 6 du
     * cours nomme n'apparaît pas toute seule : chaque {@code ChatModel}
     * ouvre lui-même l'observation {@code CHAT_MODEL_OPERATION} autour de
     * son appel, et un {@code ChatModelMeterObservationHandler} la traduit
     * en compteurs. Un modèle écrit à la main n'expose donc RIEN tant qu'il
     * ne fait pas ce travail — et c'est exactement ce que fait
     * {@link #call(Prompt)} ci-dessous.
     */
    private ObservationRegistry observations = ObservationRegistry.NOOP;

    private static final ChatModelObservationConvention CONVENTION =
            new DefaultChatModelObservationConvention();

    /** Branche le modèle sur un registre — le chapitre 6 s'en sert. */
    public void observer(ObservationRegistry registre) {
        this.observations = registre == null ? ObservationRegistry.NOOP : registre;
    }

    // ── le contrat ChatModel ─────────────────────────────────────────────

    @Override
    public ChatResponse call(Prompt prompt) {
        var contexte = ChatModelObservationContext.builder()
                .prompt(prompt)
                .provider("factice")
                .build();
        return ChatModelObservationDocumentation.CHAT_MODEL_OPERATION
                .observation(null, CONVENTION, () -> contexte, observations)
                .observe(() -> {
                    var reponse = repondre(prompt);
                    contexte.setResponse(reponse);
                    return reponse;
                });
    }

    /** La réponse elle-même — sans l'observation qui l'entoure. */
    private ChatResponse repondre(Prompt prompt) {
        recus.add(prompt);
        String entier = aPlat(prompt);

        // ── le modele demande-t-il un outil ? ────────────────────────────
        // C'est tout ce qu'un modele fait : il REND une demande. L'appel,
        // c'est Spring AI qui l'execute — le chapitre 4 le montre en
        // comptant les appels de chaque cote.
        for (var demande : demandes) {
            var appel = demande.apply(entier);
            if (appel != null) {
                var message = AssistantMessage.builder()
                        .content("")
                        .toolCalls(List.of(appel))
                        .build();
                var pourquoi = ChatGenerationMetadata.builder()
                        .finishReason("tool_calls")
                        .build();
                return new ChatResponse(
                        List.of(new Generation(message, pourquoi)),
                        ChatResponseMetadata.builder().model("factice-1")
                                .usage(new DefaultUsage(mots(entier), 0))
                                .build());
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
        var usage = new DefaultUsage(mots(entier), mots(reponse));
        var metadonnees = ChatResponseMetadata.builder()
                .model("factice-1")
                .usage(usage)
                .build();
        return new ChatResponse(List.of(new Generation(
                new AssistantMessage(reponse))), metadonnees);
    }

    /**
     * La même réponse, mais découpée — comme un vrai fournisseur la rend.
     *
     * <p>⚠️ Sans cette méthode, {@code .stream()} lève
     * {@code UnsupportedOperationException: streaming is not supported} :
     * l'implémentation par défaut de {@code ChatModel} ne se rabat PAS sur
     * {@code call()}. Un modèle écrit à la main doit donc décider s'il sait
     * diffuser, et le dire.
     *
     * <p>Le découpage est fait mot à mot, avec une pause d'une milliseconde :
     * assez pour que le chapitre 1 compte de vrais morceaux, assez peu pour
     * qu'il ne fasse pas attendre.
     */
    @Override
    public reactor.core.publisher.Flux<ChatResponse> stream(Prompt prompt) {
        var complete = call(prompt);
        String texte = complete.getResult().getOutput().getText();
        var morceaux = new ArrayList<ChatResponse>();
        // >>> depart: decouper le texte mot a mot, un ChatResponse par morceau
        //     morceaux.add(new ChatResponse(List.of(new Generation(
        //             new AssistantMessage(texte)))));
        // Coupe APRES chaque espace, pour que les morceaux se recollent
        // exactement. `(?<= )` et non `\\s` : on veut l'espace lui-meme, et
        // le garder avec le mot qui le precede.
        for (var mot : texte.split("(?<= )")) {
            morceaux.add(new ChatResponse(List.of(new Generation(
                    new AssistantMessage(mot)))));
        }
        // <<<
        // Le dernier morceau porte les metadonnees et RIEN d'autre —
        // l'usage de jetons n'est connu qu'a la fin, chez un vrai
        // fournisseur comme ici.
        //
        // ⚠️ Il a d'abord porte la reponse complete, et l'appelant qui
        // recollait les morceaux obtenait le texte EN DOUBLE. Un morceau de
        // fin sert a clore le flux, pas a le repeter.
        morceaux.add(new ChatResponse(
                List.of(new Generation(new AssistantMessage(""))),
                complete.getMetadata()));
        return reactor.core.publisher.Flux.fromIterable(morceaux)
                .delayElements(java.time.Duration.ofMillis(1));
    }

    /**
     * Le prompt entier, tel que le modèle le « lit ».
     *
     * <p>⚠️ Les résultats d'outils en font partie. Un vrai modèle les voit
     * dans son contexte — c'est même toute l'idée du second aller-retour :
     * il répond <em>à partir</em> de ce que l'outil a rendu. Les règles de
     * ce modèle doivent donc les voir aussi, sans quoi elles redemanderaient
     * le même outil à l'infini.
     */
    public static String aPlat(Prompt prompt) {
        var texte = new StringBuilder();
        for (var message : prompt.getInstructions()) {
            if (message instanceof ToolResponseMessage outil) {
                for (var reponse : outil.getResponses()) {
                    texte.append(reponse.name()).append(" = ")
                         .append(reponse.responseData()).append("\n");
                }
            } else {
                texte.append(message.getText()).append("\n");
            }
        }
        return texte.toString();
    }

    private static int mots(String texte) {
        return texte == null || texte.isBlank() ? 0 : texte.split("\\s+").length;
    }

    // ── les reponses par defaut ──────────────────────────────────────────

    private void reglesParDefaut() {
        // ⚠️ L'ORDRE COMPTE. La regle du format structure passe en premier :
        // quand `entity()` a colle ses instructions au prompt, il FAUT rendre
        // du JSON, sinon la conversion echoue — et c'est ce que le chapitre 2
        // mesure en la retirant.
        regles.add(ModeleFactice::sortieStructuree);
        regles.add(ModeleFactice::depuisLeContexte);
        regles.add(ModeleFactice::conseils);
    }

    /** Si le prompt réclame du JSON, en rendre. */
    private static String sortieStructuree(String prompt) {
        if (!prompt.contains("RFC8259") && !prompt.contains("JSON")) {
            return null;
        }
        if (prompt.contains("pointsForts")) {
            return """
                   {"pointsForts":"sept ans de Java et deux migrations menees",
                    "competences":["Java","Spring","PostgreSQL"],
                    "score":78}""";
        }
        if (prompt.contains("pertinent")) {
            return "{\"pertinent\":true,\"raison\":\"la reponse cite le document\"}";
        }
        return "{}";
    }

    /**
     * Répond à partir du contexte injecté par le RAG, s'il y en a un.
     *
     * <p>Grossier et volontairement : on cherche les phrases du contexte qui
     * partagent des mots avec la question. Aucune compréhension, aucune
     * génération — mais une réponse qui <strong>dépend du contexte</strong>,
     * ce qui suffit à montrer ce que le RAG change.
     */
    private static String depuisLeContexte(String prompt) {
        int debut = prompt.indexOf("Context information is below");
        if (debut < 0) {
            return null;
        }
        String contexte = prompt.substring(debut);
        for (var ligne : contexte.split("\n")) {
            if (ligne.contains("OFF-") || ligne.contains("salaire")
                    || ligne.contains("teletravail")) {
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

    /**
     * Les options du modèle — et le détail qui décide si les outils partent.
     *
     * <p>⚠️ <strong>Le type compte.</strong> Rendre un simple
     * {@code ChatOptions} suffisait tant qu'il n'y avait pas d'outils. Mais
     * {@code ChatClient} construit les options de chaque requête <em>à partir
     * de celles-ci</em> : si elles ne savent pas porter de
     * {@code ToolCallback}, les outils passés à {@code .tools(...)} sont
     * silencieusement perdus. Le chapitre 4 mesurait alors « 0 outil joint »
     * et « 0 appel à l'outil », sans la moindre erreur.
     *
     * <p>C'est pourquoi les options de tous les vrais fournisseurs
     * ({@code OpenAiChatOptions}, {@code AnthropicChatOptions}…)
     * implémentent {@link ToolCallingChatOptions}. Un {@code ChatModel}
     * écrit à la main doit faire pareil, ou il n'aura jamais d'outils.
     *
     * <p>⚠️ <strong>Et le nom de la méthode compte aussi.</strong>
     * {@code ChatModel} en déclare deux : {@code getDefaultOptions()}, celle
     * de Spring AI 1.x que toute la documentation nomme, et
     * {@code getOptions()}. C'est <em>getOptions()</em> que
     * {@code ChatClient} appelle pour fabriquer les options de chaque
     * requête ; {@code getDefaultOptions()} ne fait plus que déléguer à
     * celle-ci. Redéfinir la mauvaise compile, s'exécute, et perd les outils
     * sans un mot — c'est exactement ce que mesurait le chapitre 4 avant
     * cette correction.
     */
    @Override
    public ChatOptions getOptions() {
        // >>> depart: rendre des options qui savent porter des ToolCallback — sinon `.tools()` est perdu en silence
        //     return ChatOptions.builder().model("factice-1").temperature(0.0).build();
        return ToolCallingChatOptions.builder()
                .model("factice-1")
                .temperature(0.0)
                .build();
        // <<<
    }

    /** Ce que le modèle a retenu de son dernier appel, pour les tableaux. */
    public Map<String, Object> resume() {
        var prompt = dernierPrompt();
        if (prompt == null) {
            return Map.of("appels", appels());
        }
        var types = new ArrayList<String>();
        for (var message : prompt.getInstructions()) {
            types.add(message.getMessageType().getValue());
        }
        return Map.of("appels", appels(), "messages", types,
                "caracteres", aPlat(prompt).length());
    }
}
