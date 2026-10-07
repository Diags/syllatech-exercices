"""Les couts, la responsabilite partagee, et le moteur d'examen."""

from __future__ import annotations

import pytest

from jobportal import couts, examen, questions, responsabilite, tarifs

CRITERES = ["le plus economique", "le plus disponible", "le plus securise",
            "le moins d'administration"]


# ── les couts ────────────────────────────────────────────────────────────

def test_le_facteur_allume_en_permanence_ne_depend_daucun_prix():
    """⚠️ LA MESURE DU CHAPITRE 5 : c'est un rapport d'heures."""
    assert couts.FACTEUR_ALLUME_EN_PERMANENCE == pytest.approx(4.21, abs=0.01)
    assert couts.FACTEUR_ALLUME_EN_PERMANENCE == pytest.approx(
        couts.HEURES_PAR_MOIS / couts.HEURES_OUVREES_PAR_MOIS)


def test_eteindre_la_nuit_economise_les_trois_quarts():
    ressource = couts.Ressource("recette", "moyenne", "recette")

    economie = couts.eteindre_la_nuit(ressource)

    assert economie / ressource.cout == pytest.approx(
        1 - 1 / couts.FACTEUR_ALLUME_EN_PERMANENCE, abs=0.01)


def test_les_engagements_reduisent_dans_lordre_annonce():
    ordre = ["a la demande", "reserve 1 an", "reserve 3 ans", "spot"]
    montants = [couts.cout_calcul("grande", engagement=e) for e in ordre]

    assert montants == sorted(montants, reverse=True)
    assert montants[2] / montants[0] == pytest.approx(
        tarifs.ENGAGEMENTS["reserve 3 ans"])


def test_le_cout_est_lineaire_en_exemplaires_et_en_heures():
    un = couts.cout_calcul("petite", heures=100)

    assert couts.cout_calcul("petite", heures=200) == pytest.approx(un * 2)
    assert couts.cout_calcul("petite", heures=100,
                             exemplaires=3) == pytest.approx(un * 3)


def test_le_cycle_de_vie_economise_plus_de_quatre_cinquiemes():
    """⚠️ LA MESURE DU CHAPITRE 2."""
    sans = couts.cout_sur_la_duree(4000, 36)
    avec = couts.cout_sur_la_duree(4000, 36, [
        couts.Regle(30, "acces-rare"), couts.Regle(90, "archive"),
        couts.Regle(365, "archive-profonde")])

    assert avec < sans
    assert 1 - avec / sans > 0.8


def test_le_trafic_entrant_est_gratuit_le_sortant_ne_lest_pas():
    assert couts.cout_reseau(2000, "entree") == 0.0
    assert couts.cout_reseau(2000, "sortie internet") > 100


def test_la_replication_est_facturee_des_deux_cotes():
    une = couts.cout_replication(500, 1)
    deux = couts.cout_replication(500, 2)
    trois = couts.cout_replication(500, 3)

    assert une == 0.0
    assert trois == pytest.approx(deux * 2)
    assert deux == pytest.approx(
        500 * (tarifs.RESEAU["entre zones (emission)"]
               + tarifs.RESEAU["entre zones (reception)"]))


def test_le_right_sizing_descend_quand_il_faut_et_pas_autrement():
    trop_grande = couts.Observation("tres-grande", 0.05, 0.11, 0.10)
    juste = couts.Observation("grande", 0.30, 0.55, 0.40)

    assert couts.ajuster(trop_grande, marge=2.0) == "moyenne"
    assert couts.ajuster(juste, marge=1.3) == "grande"     # rien a faire
    assert couts.economie(trop_grande, 2.0)[1] > 0


def test_une_facture_sans_etiquettes_est_aveugle():
    facture = couts.Facture([
        couts.Ressource("a", "petite", "prod",
                        etiquettes={"projet": "x", "equipe": "y",
                                    "environnement": "prod"}),
        couts.Ressource("b", "petite", "?", etiquettes={}, utilisee=False),
    ])

    assert facture.part_non_etiquetee == pytest.approx(0.5)
    assert facture.gaspillage == pytest.approx(facture.total / 2)
    assert "(non etiquete)" in facture.par_etiquette("equipe")


@pytest.mark.parametrize("appel, motif", [
    (lambda: couts.cout_calcul("gigantesque"), "gabarit inconnu"),
    (lambda: couts.cout_calcul("petite", engagement="gratuit"),
     "engagement inconnu"),
    (lambda: couts.cout_stockage(1, "tiede"), "palier inconnu"),
    (lambda: couts.cout_reseau(1, "de biais"), "sens de trafic inconnu"),
])
def test_ce_qui_nexiste_pas_leve(appel, motif):
    with pytest.raises(couts.ErreurCout, match=motif):
        appel()


# ── la responsabilite partagee ───────────────────────────────────────────

def test_trois_couches_restent_a_vous_dans_tous_les_modeles():
    """⚠️ Aucun modele ne vous decharge de vos donnees."""
    toujours = {c.nom for c in responsabilite.toujours_a_vous()}

    assert toujours == {"donnees", "identites et acces",
                        "configuration du service"}


def test_le_nombre_de_couches_decroit_avec_la_delegation():
    compte = responsabilite.compter()

    assert compte["sur site"] > compte["IaaS"] > compte["PaaS"] > compte["SaaS"]
    assert compte["SaaS"] == 3


def test_le_systeme_dexploitation_est_la_frontiere_iaas_paas():
    iaas = {c.nom for c in responsabilite.a_vous("IaaS")}
    paas = {c.nom for c in responsabilite.a_vous("PaaS")}

    assert "systeme d'exploitation" in iaas
    assert "systeme d'exploitation" not in paas


def test_un_modele_inconnu_leve():
    with pytest.raises(responsabilite.ErreurResponsabilite, match="inconnu"):
        responsabilite.a_vous("FaaS")


# ── l'examen ─────────────────────────────────────────────────────────────

def test_aucune_question_na_dex_aequo():
    """Une question a egalite sur un axe n'a pas de meilleure reponse."""
    for cle, question in questions.BANQUE.items():
        for critere in CRITERES:
            question.bonne_reponse(critere)      # leve si egalite


def test_la_meme_question_change_de_reponse_selon_le_critere():
    """⚠️ LA MESURE DU CHAPITRE 6."""
    question = questions.BANQUE["base-de-donnees"]
    reponses = {c: question.bonne_reponse(c).lettre for c in CRITERES}

    assert len(set(reponses.values())) == 3
    assert reponses["le plus economique"] != reponses["le plus disponible"]
    assert reponses["le moins d'administration"] != reponses["le plus disponible"]


def test_le_moins_cher_peut_etre_le_pire():
    """Le moteur applique le critere sans juger — et c'est instructif."""
    question = questions.BANQUE["acces-au-bucket"]

    economique = question.bonne_reponse("le plus economique")
    securise = question.bonne_reponse("le plus securise")

    assert "public" in economique.texte
    assert "role limite" in securise.texte
    assert economique.securite < securise.securite


@pytest.mark.parametrize("enonce, attendu", [
    ("Quelle solution est la plus economique ?", "le plus economique"),
    ("Quelle architecture est la plus resiliente ?", "le plus disponible"),
    ("Laquelle offre la plus haute disponibilite ?", "le plus disponible"),
    ("Laquelle est la plus securisee ?", "le plus securise"),
    ("Laquelle demande le moins d'administration ?",
     "le moins d'administration"),
    ("Quelle option est la moins chere ?", "le plus economique"),
])
def test_le_mot_qui_tranche_est_detecte(enonce: str, attendu: str):
    assert examen.detecter(enonce) == attendu


def test_un_enonce_sans_mot_qui_tranche_leve():
    with pytest.raises(examen.ErreurExamen, match="aucun mot qui tranche"):
        examen.detecter("Quelle solution recommandez-vous ?")


def test_deux_criteres_contradictoires_levent():
    with pytest.raises(examen.ErreurExamen, match="contradictoires"):
        examen.detecter("La plus economique ET la plus disponible ?")


def test_une_question_a_egalite_leve():
    jumelles = examen.Question("x", "y", [
        examen.Option("A", "a", cout=5, disponibilite=5, securite=5,
                      administration=5),
        examen.Option("B", "b", cout=5, disponibilite=5, securite=5,
                      administration=5),
    ])

    with pytest.raises(examen.ErreurExamen, match="egalite"):
        jumelles.bonne_reponse("le plus economique")


def test_une_copie_rend_plus_quune_note():
    reponses = [
        examen.Reponse(questions.BANQUE["base-de-donnees"],
                       "le plus disponible", "C", 40),
        examen.Reponse(questions.BANQUE["acces-au-bucket"],
                       "le plus securise", "A", 400),
    ]
    copie = examen.Copie(reponses, minutes_autorisees=5)

    assert copie.note == 0.5
    assert copie.par_domaine() == {"donnees": (1, 1),
                                   "reseau et securite": (0, 1)}
    assert copie.a_revoir() == ["reseau et securite"]
    assert len(copie.chronophages()) == 1
    assert not copie.dans_les_temps   # 440 s pour 300 s autorisees


def test_la_correction_dit_pourquoi_chaque_autre_est_mauvaise():
    copie = examen.Copie([examen.Reponse(
        questions.BANQUE["base-de-donnees"], "le plus disponible", "B")])

    lignes = examen.corriger(copie)

    assert any("attendu C" in ligne for ligne in lignes)
    assert sum(1 for ligne in lignes if " non : " in ligne) == 3
