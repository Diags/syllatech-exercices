package fr.portail.application;

/**
 * Ce que l'application retient d'une soumission.
 *
 * @param candidature  l'identifiant de la candidature
 * @param reussis      le nombre d'assertions satisfaites
 * @param attendus     le nombre d'assertions du test
 * @param delaiDepasse la solution a-t-elle boucle ?
 * @param bloquee      le bac a sable a-t-il refuse un privilege ?
 */
public record Note(long candidature, int reussis, int attendus,
                   boolean delaiDepasse, boolean bloquee) {

    /** Une soumission ecartee n'est pas notee : elle sort du bareme. */
    public boolean ecartee() {
        return delaiDepasse || bloquee;
    }

    public boolean admise() {
        return !delaiDepasse && !bloquee && reussis == attendus;
    }

    public String mention() {
        if (bloquee) {
            return "ecartee — tentative d'acces refusee";
        }
        if (delaiDepasse) {
            return "ecartee — delai depasse";
        }
        return reussis + "/" + attendus;
    }
}
