"""Ce que le serveur doit garantir, verifie automatiquement.

Lancer :  uv run --extra dev pytest -q
"""

import pytest

from jobportal import donnees
from jobportal.serveur import (
    creer_candidature,
    lettre_motivation,
    offre,
    rechercher_offres,
    serveur,
)


def test_le_serveur_porte_le_nom_du_projet():
    assert serveur.name == "jobportal"


def test_recherche_insensible_aux_accents_et_a_la_casse():
    a = rechercher_offres("DEVELOPPEUR")
    b = rechercher_offres("developpeur")
    assert a == b and len(a) >= 2


def test_recherche_vide_rend_tout_le_catalogue():
    assert len(rechercher_offres("")) == len(donnees.OFFRES)


def test_une_resource_rend_du_texte_lisible():
    texte = offre("JP-002")
    assert "Ingénieur IA" in texte and "syllatech" in texte


def test_une_resource_inconnue_ne_leve_pas():
    # Une resource est une lecture : elle explique, elle ne casse pas.
    assert "JP-404" in offre("JP-404")


def test_une_candidature_est_enregistree():
    avant = len(donnees.candidatures())
    creer_candidature("JP-001", "CV de test")
    assert len(donnees.candidatures()) == avant + 1


def test_une_candidature_sur_offre_inconnue_leve():
    # Un outil qui ecrit doit refuser bruyamment : sinon l'agent croit avoir
    # reussi et continue sur une fausse hypothese.
    with pytest.raises(ValueError):
        creer_candidature("JP-999", "CV de test")


def test_un_cv_vide_est_refuse():
    with pytest.raises(ValueError):
        creer_candidature("JP-001", "   ")


def test_le_prompt_reprend_ses_parametres():
    texte = lettre_motivation("Ingénieur IA", "syllatech")
    assert "Ingénieur IA" in texte and "syllatech" in texte
