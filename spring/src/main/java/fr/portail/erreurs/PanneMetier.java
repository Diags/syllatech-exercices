package fr.portail.erreurs;

/**
 * Une exception <strong>vérifiée</strong> — celle que Spring ne considère pas
 * comme une raison d'annuler.
 *
 * <p>Elle n'hérite pas de {@link RuntimeException}, et c'est tout le sujet du
 * chapitre 4 : par défaut, {@code @Transactional} ne fait un rollback que sur
 * une exception non vérifiée. Celle-ci laisse donc la transaction se valider,
 * sauf à écrire {@code @Transactional(rollbackFor = PanneMetier.class)}.
 */
public class PanneMetier extends Exception {

    private static final long serialVersionUID = 1L;

    public PanneMetier(String message) {
        super(message);
    }
}
