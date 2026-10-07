package fr.portail.runner;

/**
 * Le contrat de sortie du runner.
 *
 * <p>⚠️ CE QUI SORT D'ICI EST UNE DONNEE HOSTILE. {@code sortie} et
 * {@code erreurs} ont ete produits par le code d'un inconnu. On ne les
 * insere jamais dans une page sans echappement, jamais dans une requete,
 * jamais dans une expression evaluee. Voir {@code securite.Sortie}.
 *
 * @param sortie      la sortie standard, deja plafonnee
 * @param erreurs     la sortie d'erreur, deja plafonnee
 * @param codeSortie  0 en cas de succes ; 77 en cas de refus de privilege
 * @param delaiDepasse vrai si le processus a ete tue par le delai dur
 * @param millisecondes le temps mesure, pour l'observabilite
 */
public record Resultat(String sortie, String erreurs, int codeSortie,
                       boolean delaiDepasse, long millisecondes) {

    public boolean reussi() {
        return codeSortie == 0 && !delaiDepasse;
    }

    /** ⚠️ Le seul verdict qui compte pour un test d'evasion. */
    public boolean bloque() {
        return !reussi();
    }
}
