package fr.portail.modele;

import java.util.concurrent.atomic.AtomicInteger;
import org.springframework.ai.audio.transcription.AudioTranscription;
import org.springframework.ai.audio.transcription.AudioTranscriptionPrompt;
import org.springframework.ai.audio.transcription.AudioTranscriptionResponse;
import org.springframework.ai.audio.transcription.TranscriptionModel;
import org.springframework.stereotype.Component;

/**
 * Le modèle de transcription du portail — et la démonstration qu'il est
 * <strong>un autre modèle</strong>.
 *
 * <p>Le chapitre 5 du cours dit « la transcription a son modèle dédié ». Ce
 * n'est pas une remarque d'organisation, c'est une contrainte de typage :
 *
 * <ul>
 *   <li>il n'implémente <strong>pas</strong> {@code ChatModel} ;</li>
 *   <li>il ne prend pas un {@code Prompt} mais un
 *       {@link AudioTranscriptionPrompt}, qui porte une {@code Resource} ;</li>
 *   <li>il ne rend pas un {@code ChatResponse} mais un
 *       {@link AudioTranscriptionResponse} ;</li>
 *   <li>et surtout, {@code ChatClient.builder(...)} ne l'accepte pas — le
 *       code ne compile pas. Le chapitre le dit, et vous pouvez le
 *       vérifier : décommentez la ligne indiquée.</li>
 * </ul>
 *
 * <p>⚠️ Ce qu'il ne fait pas : écouter. Il rend un texte fixe. Ce qui est
 * mesuré au chapitre 5 est donc la <em>plomberie</em> — quel type entre,
 * quel type sort, et ce qu'on peut enchaîner derrière — jamais la qualité
 * d'une transcription. Pour cela, ce dépôt a un autre outil, qui fait
 * vraiment tourner un modèle : {@code outils/transcrire.py}.
 */
@Component
public class TranscriptionFactice implements TranscriptionModel {

    /** Ce qu'un entretien du portail donnerait, une fois transcrit. */
    public static final String ENTRETIEN = """
            Bonjour, merci de me recevoir. J'ai sept ans d'experience en \
            Java, principalement sur Spring Boot. Sur mon dernier poste \
            j'ai mene la migration d'un monolithe vers des services. Je \
            cherche un poste a Lyon, avec du teletravail deux jours par \
            semaine.""";

    private final AtomicInteger appels = new AtomicInteger();

    public int appels() {
        return appels.get();
    }

    @Override
    public AudioTranscriptionResponse call(AudioTranscriptionPrompt prompt) {
        appels.incrementAndGet();
        return new AudioTranscriptionResponse(new AudioTranscription(ENTRETIEN));
    }
}
