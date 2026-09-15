package fr.portail.modele;

import dev.langchain4j.model.chat.StreamingChatModel;
import dev.langchain4j.model.chat.request.ChatRequest;
import dev.langchain4j.model.chat.response.StreamingChatResponseHandler;
import org.springframework.stereotype.Component;

/**
 * Le même modèle, mais qui répond mot à mot.
 *
 * <p>⚠️ <strong>C'est une interface différente.</strong> {@code ChatModel} et
 * {@link StreamingChatModel} n'ont aucun lien d'héritage : un modèle peut
 * savoir faire l'un, l'autre, ou les deux, et {@code AiServices} demande
 * explicitement un {@code streamingChatModel(...)} pour une méthode qui rend
 * un {@code TokenStream}. Se tromper d'interface ne compile pas — c'est le
 * bon comportement, mais il surprend.
 *
 * <p>Ce modèle délègue le travail au {@link ModeleFactice} qu'on lui donne :
 * même règles, même mémoire des requêtes. Il n'ajoute qu'une chose — le
 * découpage — et une pause volontaire avant le premier morceau, pour que le
 * chapitre 5 puisse mesurer le <em>temps jusqu'au premier jeton</em> plutôt
 * que d'en parler.
 */
@Component
public class ModeleFacticeEnFlux implements StreamingChatModel {

    /** Le temps que « réfléchit » le modèle avant son premier mot. */
    public static final long REFLEXION_MS = 120;

    /** Le temps entre deux mots, une fois la génération lancée. */
    public static final long PAR_MOT_MS = 4;

    private final ModeleFactice modele;

    public ModeleFacticeEnFlux(ModeleFactice modele) {
        this.modele = modele;
    }

    public ModeleFactice modele() {
        return modele;
    }

    /**
     * ⚠️ {@code doChat}, et non {@code chat} — comme pour le modèle complet.
     * {@code chat} est l'enveloppe qui prévient les écouteurs.
     */
    @Override
    public void doChat(ChatRequest requete, StreamingChatResponseHandler main) {
        try {
            var complete = modele.doChat(requete);
            dormir(REFLEXION_MS);
            String texte = complete.aiMessage().text();
            if (texte != null) {
                // >>> depart: diffuser la reponse mot a mot, en gardant l'espace avec le mot qui le precede
                //     main.onPartialResponse(texte);
                // Coupe APRES chaque espace, pour que les morceaux se
                // recollent exactement — on garde l'espace avec le mot qui
                // le precede.
                for (var mot : texte.split("(?<= )")) {
                    main.onPartialResponse(mot);
                    dormir(PAR_MOT_MS);
                }
                // <<<
            }
            main.onCompleteResponse(complete);
        } catch (RuntimeException panne) {
            main.onError(panne);
        }
    }

    private static void dormir(long millisecondes) {
        try {
            Thread.sleep(millisecondes);
        } catch (InterruptedException interrompu) {
            Thread.currentThread().interrupt();
        }
    }
}
