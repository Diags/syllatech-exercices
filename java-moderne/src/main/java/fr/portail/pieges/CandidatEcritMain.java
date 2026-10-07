package fr.portail.pieges;

/**
 * Le même candidat, écrit à la main — et avec l'oubli le plus fréquent.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> {@code equals}
 * est redéfini, {@code hashCode} ne l'est pas. Le compilateur ne dit rien —
 * c'est du Java parfaitement légal — et le résultat est un objet qui est
 * égal à lui-même mais introuvable dans un {@code HashSet}.
 *
 * <p>Comparez avec {@link fr.portail.domaine.Candidat}, qui est un
 * {@code record} : le compilateur y écrit les deux, toujours ensemble,
 * toujours à partir des mêmes composants. C'est tout l'argument du chapitre 2.
 */
public final class CandidatEcritMain {

    private final String nom;
    private final String courriel;
    private final int anneesExperience;

    public CandidatEcritMain(String nom, String courriel, int anneesExperience) {
        this.nom = nom;
        this.courriel = courriel;
        this.anneesExperience = anneesExperience;
    }

    public String nom() {
        return nom;
    }

    public String courriel() {
        return courriel;
    }

    public int anneesExperience() {
        return anneesExperience;
    }

    @Override
    public boolean equals(Object autre) {
        return autre instanceof CandidatEcritMain c
                && nom.equals(c.nom)
                && courriel.equals(c.courriel)
                && anneesExperience == c.anneesExperience;
    }

    // Ici manque hashCode(). C'est le defaut, et il est volontaire.

    // Et toString() manque aussi : l'objet s'affichera sous la forme
    // fr.portail.pieges.CandidatEcritMain@1b6d3586 — le nom de la classe et
    // un nombre qui ne veut rien dire. Dans un journal d'erreurs, c'est la
    // difference entre comprendre et relancer le programme.
}
