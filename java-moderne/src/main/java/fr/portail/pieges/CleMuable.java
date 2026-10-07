package fr.portail.pieges;

import java.util.Objects;

/**
 * Une clé dont le {@code hashCode} dépend d'un champ que l'on peut changer.
 *
 * <p>⚠️ <strong>Pièce à conviction : ne pas réparer.</strong> {@code equals}
 * et {@code hashCode} sont ici parfaitement cohérents entre eux — le contrat
 * est respecté. Le défaut est ailleurs : le champ dont ils dépendent est
 * <strong>muable</strong>.
 *
 * <p>Mise dans un {@code HashMap} puis modifiée, l'entrée devient
 * inatteignable : elle est rangée dans le casier de son ancien code, et on la
 * cherche dans celui du nouveau. Le chapitre 3 le mesure — et montre que
 * remettre le champ à sa valeur d'origine fait <em>réapparaître</em> l'entrée,
 * ce qui est la preuve que rien n'a été perdu, seulement mal rangé.
 */
public final class CleMuable {

    private String valeur;

    public CleMuable(String valeur) {
        this.valeur = valeur;
    }

    public String valeur() {
        return valeur;
    }

    /** Le geste fautif : après un {@code put}, il déplace le casier. */
    public void changer(String nouvelle) {
        this.valeur = nouvelle;
    }

    @Override
    public boolean equals(Object autre) {
        return autre instanceof CleMuable c && Objects.equals(valeur, c.valeur);
    }

    @Override
    public int hashCode() {
        return Objects.hashCode(valeur);
    }

    @Override
    public String toString() {
        return "Cle(" + valeur + ")";
    }
}
