package fr.portail;

import static org.assertj.core.api.Assertions.assertThat;

import fr.portail.front.Composant;
import fr.portail.front.Magasin;
import fr.portail.front.Reconciliation;
import fr.portail.front.Reconciliation.Element;
import fr.portail.front.Reconciliation.Operation;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;

/**
 * Les mecanismes du front, mesures en Java.
 *
 * <p>⚠️ CE QUE CES TESTS NE SONT PAS. Ils ne testent pas React : aucun
 * navigateur, aucun Node. Ils fixent les ALGORITHMES que React applique — la
 * reconciliation d'une liste, la semantique des dependances d'un effet,
 * l'immuabilite d'un reducteur — et c'est ce qu'un cours peut demontrer hors
 * ligne.
 */
class FrontTest {

    private static final List<Element> LISTE = List.of(
            new Element("OFF-101", "Developpeur Java Spring"),
            new Element("OFF-102", "Ingenieur plateforme Kubernetes"),
            new Element("OFF-103", "Developpeur Java / Kafka"),
            new Element("OFF-104", "SRE astreinte"),
            new Element("OFF-105", "Developpeur front React"),
            new Element("OFF-106", "Architecte cloud"));

    private static List<Element> avecUnNouveauEnTete() {
        List<Element> apres = new ArrayList<>();
        apres.add(new Element("OFF-107", "Lead developpeur Java"));
        apres.addAll(LISTE);
        return apres;
    }

    // -- la reconciliation -------------------------------------------------

    @Test
    @DisplayName("⚠️ LA MESURE : une insertion en tete coute 7 operations sans `key`, 1 avec")
    void laCleEviteSixReecritures() {
        List<Element> apres = avecUnNouveauEnTete();

        Reconciliation.Rendu sansCle = Reconciliation.parPosition(LISTE, apres);
        Reconciliation.Rendu avecCle = Reconciliation.parCle(LISTE, apres);

        assertThat(sansCle.total()).isEqualTo(7);
        assertThat(sansCle.compte(Operation.METTRE_A_JOUR))
                .as("chaque ligne est reecrite, alors qu'aucune n'a change")
                .isEqualTo(6);

        assertThat(avecCle.total())
                .as("une creation, et rien d'autre")
                .isEqualTo(1);
        assertThat(avecCle.compte(Operation.CREER)).isEqualTo(1);
        assertThat(avecCle.compte(Operation.METTRE_A_JOUR)).isZero();
        assertThat(avecCle.compte(Operation.DEPLACER))
                .as("l'ordre relatif n'a pas change : rien ne bouge")
                .isZero();
    }

    @Test
    @DisplayName("un element retire n'entraine qu'une suppression")
    void unRetraitCouteUneSuppression() {
        List<Element> apres = new ArrayList<>(LISTE);
        apres.removeFirst();

        assertThat(Reconciliation.parCle(LISTE, apres).total()).isEqualTo(1);
        assertThat(Reconciliation.parCle(LISTE, apres)
                .compte(Operation.SUPPRIMER)).isEqualTo(1);
    }

    @Test
    @DisplayName("un element VRAIMENT modifie coute bien une mise a jour")
    void uneModificationRealleEstVue() {
        List<Element> apres = new ArrayList<>(LISTE);
        apres.set(2, new Element("OFF-103", "Developpeur Java / Kafka (senior)"));

        Reconciliation.Rendu rendu = Reconciliation.parCle(LISTE, apres);
        assertThat(rendu.compte(Operation.METTRE_A_JOUR)).isEqualTo(1);
        assertThat(rendu.total()).isEqualTo(1);
    }

    @Test
    @DisplayName("⚠️ sans `key`, l'etat d'un composant migre vers une AUTRE offre")
    void lEtatMigreSansCle() {
        List<Element> apres = avecUnNouveauEnTete();

        assertThat(Reconciliation.quiHeriteDeLEtat(apres, 0, false, "OFF-101"))
                .as("la coche saute sur l'offre qui a pris la place")
                .isEqualTo("OFF-107");
        assertThat(Reconciliation.quiHeriteDeLEtat(apres, 0, true, "OFF-101"))
                .as("avec une key, l'etat suit son element")
                .isEqualTo("OFF-101");
    }

    @Test
    @DisplayName("un deplacement reel est detecte, lui")
    void unDeplacementEstVu() {
        // On remonte la derniere offre en tete : son ancien rang est le plus
        // grand, donc tous les autres « reculent » et doivent bouger.
        List<Element> apres = new ArrayList<>();
        apres.add(LISTE.getLast());
        apres.addAll(LISTE.subList(0, LISTE.size() - 1));

        assertThat(Reconciliation.parCle(LISTE, apres)
                .compte(Operation.DEPLACER))
                .as("cinq elements passent apres un element plus ancien")
                .isEqualTo(5);
    }

    // -- les hooks ---------------------------------------------------------

    @ParameterizedTest(name = "{0} → {1} effet(s), {2} nettoyage(s)")
    @CsvSource({"AUCUNE,4,3", "VIDES,1,0", "SURVEILLEES,2,1"})
    @DisplayName("⚠️ LA MESURE : le tableau de dependances decide de tout")
    void lesTroisFormesDeDependances(Composant.Dependances forme,
                                     int effets, int nettoyages) {
        // Quatre rendus ; la valeur surveillee change une seule fois.
        Composant composant = new Composant(forme, List.of());
        for (Object valeur : new Object[] {"java", "java", "devops", "devops"}) {
            composant.rendre(valeur, c -> { });
        }

        assertThat(composant.rendus()).isEqualTo(4);
        assertThat(composant.executionsDEffet()).isEqualTo(effets);
        assertThat(composant.nettoyages())
                .as("React nettoie l'effet precedent AVANT de le reexecuter")
                .isEqualTo(nettoyages);
    }

    @Test
    @DisplayName("⚠️ `useEffect(fn, [])` sur un composant filtrable ne recharge JAMAIS")
    void leTableauVideNeRechargeJamais() {
        Composant fige = new Composant(Composant.Dependances.VIDES, List.of());
        List<Object> filtresVus = new ArrayList<>();
        for (Object filtre : new Object[] {"java", "devops", "front"}) {
            fige.rendre(filtre, c -> filtresVus.add(filtre));
        }

        // Le bogue « ca ne se met pas a jour » dans sa forme la plus pure :
        // seul le premier filtre a declenche un chargement.
        assertThat(filtresVus).containsExactly("java");
        assertThat(fige.journalDesDependances())
                .as("le composant a pourtant bien vu les trois filtres")
                .containsExactly("java", "devops", "front");
    }

    @Test
    @DisplayName("reposer la MEME valeur ne declenche pas de rendu")
    void poserLaMemeValeur() {
        Composant composant =
                new Composant(Composant.Dependances.SURVEILLEES, 0);

        assertThat(composant.poserLEtat(List.of("a", "b"))).isTrue();
        assertThat(composant.poserLEtat(List.of("a", "b")))
                .as("c'est ce qui empeche la boucle effet → etat → effet")
                .isFalse();
    }

    // -- le magasin --------------------------------------------------------

    @Test
    @DisplayName("un reducteur pur laisse l'etat precedent intact")
    void leReducteurEstPur() {
        record Etat(List<String> items) {
        }
        Magasin<Etat> magasin = new Magasin<>(new Etat(List.of()),
                (etat, action) -> action.type().equals("ajout")
                        ? new Etat(List.of(String.valueOf(action.charge())))
                        : etat);

        Etat initial = magasin.etat();
        magasin.envoyer(new Magasin.Action("ajout", "OFF-101"));

        assertThat(magasin.etat().items()).containsExactly("OFF-101");
        assertThat(initial.items())
                .as("l'etat initial est toujours la — c'est ce qui permet de rejouer")
                .isEmpty();
        assertThat(magasin.historique()).hasSize(2);
    }

    @Test
    @DisplayName("une action inconnue ne declenche aucun rendu")
    void uneActionInconnueNeNotifiePas() {
        Magasin<String> magasin = new Magasin<>("initial",
                (etat, action) -> action.type().equals("connue")
                        ? "change" : etat);
        int[] notifications = {0};
        magasin.abonner(etat -> notifications[0]++);

        magasin.envoyer(new Magasin.Action("inconnue", null));
        assertThat(notifications[0]).isZero();

        magasin.envoyer(new Magasin.Action("connue", null));
        assertThat(notifications[0]).isEqualTo(1);
    }

    @ParameterizedTest(name = "a {0} niveaux : {1} composants sans magasin, {2} avec")
    @CsvSource({"1,2,2", "3,4,2", "6,7,2", "10,11,2"})
    @DisplayName("⚠️ a UN niveau, le magasin n'apporte rien")
    void lePropDrillingSeCompte(int profondeur, int sans, int avec) {
        assertThat(Magasin.composantsTraverses(profondeur, false)).isEqualTo(sans);
        assertThat(Magasin.composantsTraverses(profondeur, true)).isEqualTo(avec);
    }
}
