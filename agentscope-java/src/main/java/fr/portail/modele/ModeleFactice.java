package fr.portail.modele;

import io.agentscope.core.message.ContentBlock;
import io.agentscope.core.message.Msg;
import io.agentscope.core.message.TextBlock;
import io.agentscope.core.message.ToolResultBlock;
import io.agentscope.core.message.ToolUseBlock;
import io.agentscope.core.model.ChatModelBase;
import io.agentscope.core.model.ChatResponse;
import io.agentscope.core.model.ChatUsage;
import io.agentscope.core.model.GenerateOptions;
import io.agentscope.core.model.ToolSchema;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.Predicate;
import reactor.core.publisher.Flux;

/**
 * Un {@link io.agentscope.core.model.Model} ecrit ici, et c'est ce qui rend
 * ce projet mesurable.
 *
 * <p>POURQUOI PAS UN VRAI FOURNISSEUR
 * <p>Parce qu'un cours ne peut pas exiger une cle d'API, et surtout parce
 * qu'on ne mesure rien avec un modele non deterministe. Ce qu'AgentScope
 * apporte — la BOUCLE ReAct, le catalogue d'outils, le moteur de
 * permissions, le flux d'evenements — se demontre bien mieux avec un modele
 * dont on connait d'avance chaque decision. Le framework, lui, est le vrai.
 *
 * <p>⚠️ CE MODELE NE RAISONNE PAS. Il suit un SCENARIO : une liste de tours,
 * chacun disant « emets tel appel d'outil » ou « reponds ce texte ». Ce qui
 * est mesure ensuite — combien de fois le modele a ete appele, quels outils
 * ont ete demandes, quels evenements sont sortis — est produit par
 * AgentScope, pas par ce fichier.
 *
 * <p>Le modele compte ses propres appels : c'est l'instrument du chapitre 1,
 * qui oppose « un appel au modele » a « un agent ».
 */
public final class ModeleFactice extends ChatModelBase {

    private static final com.fasterxml.jackson.databind.ObjectMapper JSON =
            new com.fasterxml.jackson.databind.ObjectMapper();

    /** Un tour du scenario : ce que le modele repond a l'appel numero N. */
    public sealed interface Tour {

        /** Le modele demande l'execution d'un outil. */
        record AppelDOutil(String outil, Map<String, Object> arguments)
                implements Tour {
        }

        /** Le modele repond, et la boucle s'arrete. */
        record Reponse(String texte) implements Tour {
        }

        /**
         * Le modele repond en fonction de ce qu'il a VU dans l'historique.
         *
         * <p>C'est ce qui permet au chapitre 1 de montrer qu'un agent voit
         * le resultat de l'outil, la ou un appel isole ne voit rien.
         */
        record ReponseSelonLHistorique(
                java.util.function.Function<List<Msg>, String> texte)
                implements Tour {
        }
    }

    private final String nom;
    private final List<Tour> scenario;
    private final AtomicInteger appels = new AtomicInteger();
    private final List<List<ToolSchema>> outilsVus = new ArrayList<>();
    private final List<Integer> messagesVus = new ArrayList<>();

    public ModeleFactice(String nom, List<Tour> scenario) {
        this.nom = nom;
        this.scenario = List.copyOf(scenario);
    }

    /** Un modele d'une seule reponse : le « simple appel » du chapitre 1. */
    public static ModeleFactice quiRepond(String nom, String texte) {
        return new ModeleFactice(nom, List.of(new Tour.Reponse(texte)));
    }

    @Override
    protected Flux<ChatResponse> doStream(List<Msg> messages,
                                          List<ToolSchema> outils,
                                          GenerateOptions options) {
        int rang = appels.getAndIncrement();
        synchronized (this) {
            outilsVus.add(outils == null ? List.of() : List.copyOf(outils));
            messagesVus.add(messages == null ? 0 : messages.size());
        }
        Tour tour = rang < scenario.size()
                ? scenario.get(rang)
                : new Tour.Reponse("(le scenario est epuise)");

        List<ContentBlock> contenu = switch (tour) {
            // >>> depart: emettre un appel d'outil EXPLOITABLE — l'accumulateur d'AgentScope recolle les arguments depuis le JSON de `content`, pas depuis la Map d'`input`
            //     case Tour.AppelDOutil appel -> List.of(ToolUseBlock.builder()
            //             .name(appel.outil())
            //             .input(appel.arguments())
            //             .build());
            case Tour.AppelDOutil appel -> List.of(ToolUseBlock.builder()
                    .id("appel-" + (rang + 1))
                    .name(appel.outil())
                    .input(appel.arguments())
                    // ⚠️ `content` PORTE LES ARGUMENTS EN JSON, et ce
                    // n'est pas une redondance : un vrai fournisseur envoie
                    // les arguments d'outil en fragments de TEXTE, que
                    // l'accumulateur d'AgentScope recolle puis analyse. Sans
                    // cette chaine, la validation de schema refuse l'appel —
                    // « required property not found » — alors meme que la
                    // Map est remplie.
                    .content(enJson(appel.arguments()))
                    .build());
            // <<<
            case Tour.Reponse reponse ->
                    List.of(TextBlock.builder().text(reponse.texte()).build());
            case Tour.ReponseSelonLHistorique selon -> List.of(
                    TextBlock.builder()
                            .text(selon.texte().apply(
                                    messages == null ? List.of() : messages))
                            .build());
        };

        // ⚠️ Un vrai fournisseur emet des fragments ; celui-ci emet une seule
        // reponse complete. Le chapitre 2 le dit, et mesure la difference.
        return Flux.just(ChatResponse.builder()
                .id("reponse-" + (rang + 1))
                .content(contenu)
                .usage(new ChatUsage(80 + 20 * rang, 30, 0.0))
                .finishReason(tour instanceof Tour.AppelDOutil
                        ? "tool_calls" : "stop")
                .build());
    }

    /** Les arguments, tels qu'un fournisseur les enverrait : du JSON. */
    private static String enJson(Map<String, Object> arguments) {
        try {
            return JSON.writeValueAsString(arguments);
        } catch (com.fasterxml.jackson.core.JsonProcessingException erreur) {
            throw new IllegalStateException("arguments non serialisables", erreur);
        }
    }

    @Override
    public String getModelName() {
        return nom;
    }

    // -- l'instrument ------------------------------------------------------

    /** Combien de fois le modele a ete appele. */
    public int appels() {
        return appels.get();
    }

    /** Les schemas d'outils presentes au modele, appel par appel. */
    public synchronized List<List<ToolSchema>> outilsVus() {
        return List.copyOf(outilsVus);
    }

    /** Le nombre de messages d'historique recus, appel par appel. */
    public synchronized List<Integer> messagesVus() {
        return List.copyOf(messagesVus);
    }

    public synchronized void reinitialiser() {
        appels.set(0);
        outilsVus.clear();
        messagesVus.clear();
    }

    /**
     * Un predicat lisible pour les scenarios : « l'historique contient-il un
     * resultat d'outil ? »
     */
    public static Predicate<List<Msg>> aVuUnResultatDOutil() {
        return messages -> messages.stream()
                .anyMatch(msg -> msg.hasContentBlocks(ToolResultBlock.class));
    }

    /**
     * Le texte de tous les resultats d'outils vus dans l'historique.
     *
     * <p>⚠️ Le resultat d'un outil traverse la boucle SERIALISE : une methode
     * qui rend une {@code String} arrive ici entre guillemets, avec ses
     * retours a la ligne echappes. C'est logique — le contenu d'un bloc doit
     * pouvoir porter un objet aussi bien qu'un texte — mais cela surprend la
     * premiere fois, et cela se voit dans la reponse si on ne le decode pas.
     */
    public static String resultatsDOutils(List<Msg> messages) {
        List<String> morceaux = new ArrayList<>();
        for (Msg message : messages) {
            for (ToolResultBlock bloc
                    : message.getContentBlocks(ToolResultBlock.class)) {
                for (ContentBlock sortie : bloc.getOutput()) {
                    if (sortie instanceof TextBlock texteBloc) {
                        morceaux.add(decoder(texteBloc.getText()));
                    }
                }
            }
        }
        return String.join("\n", morceaux);
    }

    /** Rend sa forme lisible a une chaine JSON ; laisse le reste intact. */
    static String decoder(String texte) {
        if (texte == null || texte.length() < 2
                || texte.charAt(0) != '"' || !texte.endsWith("\"")) {
            return texte;
        }
        try {
            return JSON.readValue(texte, String.class);
        } catch (com.fasterxml.jackson.core.JsonProcessingException ignore) {
            return texte;
        }
    }
}
