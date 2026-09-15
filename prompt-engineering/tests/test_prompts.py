"""Ce que le projet doit garantir.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "chapitres"))

import pytest

from jobportal.evaluation import comparer, evaluer
from jobportal.modele import ModeleJouet, modele
from jobportal.prompts import ANCRE, JEU_DE_TEST, V1, V2, V3, VERSIONS
from jobportal.schemas import Analyse, analyser_sortie


# ------------------------------------------------------------- le modele

def test_il_lit_vraiment_les_exemples_du_prompt():
    """Le coeur du projet : si le modele n'extrayait pas les exemples, la
    progression des scores serait un trucage."""
    assert ModeleJouet.exemples_du_prompt(V1) == []
    assert len(ModeleJouet.exemples_du_prompt(V2)) == 3
    assert len(ModeleJouet.exemples_du_prompt(V3)) == 6


def test_sans_exemple_il_ne_sait_pas_decider():
    r = modele().repondre(V1.format(entree="Recruteur au top"), "Recruteur au top")
    assert "aucun exemple" in r.diagnostic


def test_le_raisonnement_n_apparait_que_s_il_est_demande():
    entree = "Ambiance froide mais salaire correct"
    assert modele().repondre(V2.format(entree=entree), entree).raisonnement == []
    assert modele().repondre(V3.format(entree=entree), entree).raisonnement != []


# ------------------------------------------------------- la progression

def test_les_scores_progressent_de_v1_a_v3():
    """LA propriete du projet : un meilleur prompt donne un meilleur score,
    par un mecanisme reel."""
    v1, v2, v3 = comparer(modele(), VERSIONS, JEU_DE_TEST)
    assert v1.taux < v2.taux < v3.taux


def test_le_jeu_de_test_documente_chaque_cas():
    """Un jeu de test sans intention est un jeu qu'on n'ose plus modifier."""
    for cas in JEU_DE_TEST:
        assert cas["pourquoi"], f"cas sans justification : {cas['entree']}"


def test_aucune_version_n_atteint_100_pour_cent():
    """Un prompt parfait sur son propre jeu de test signale un jeu taille
    pour le prompt. On garde donc un echec explique (voir chapitre 2)."""
    assert max(r.taux for r in comparer(modele(), VERSIONS, JEU_DE_TEST)) < 1.0


# ------------------------------------------------------------ l'ancrage

def test_le_modele_refuse_quand_le_contexte_ne_dit_rien():
    contexte = "Ingenieur IA, Teletravail, CDI. Competences : python, llm."
    r = modele().repondre(ANCRE.format(contexte=contexte, entree="Quel est le salaire ?"),
                          "Quel est le salaire ?", contexte)
    assert r.refus and r.texte == "Information non disponible."


def test_il_repond_quand_le_contexte_porte_l_information():
    contexte = "Ingenieur IA, Teletravail, CDI. Competences : python, llm."
    q = "Quelles competences pour ce poste ?"
    r = modele().repondre(ANCRE.format(contexte=contexte, entree=q), q, contexte)
    assert not r.refus


# --------------------------------------------------- les sorties structurees

def test_une_sortie_conforme_est_acceptee():
    objet, err = analyser_sortie('{"avis": "Offre solide pour un junior.", '
                                 '"risque": 3, "manques": ["salaire"]}')
    assert isinstance(objet, Analyse) and not err and objet.risque == 3


@pytest.mark.parametrize("texte,attendu", [
    ("Voici mon avis : solide.", "pas du JSON"),
    ('{"avis": "Bien.", "risque": 3, "manques": []}', "avis"),
    ('{"avis": "Offre correcte mais floue.", "risque": 42, "manques": []}', "risque"),
])
def test_les_sorties_non_conformes_sont_refusees_avec_la_bonne_raison(texte, attendu):
    objet, err = analyser_sortie(texte)
    assert objet is None and attendu in err


# ------------------------------------------------------------ les chapitres

def test_la_compaction_garde_les_derniers_tours_intacts():
    from chapitre_5_contexte import GARDES, compacter
    historique = [{"role": "user", "content": f"tour {i} : " + "x" * 80} for i in range(10)]
    compacte, agi = compacter(historique)
    assert agi
    assert compacte[-GARDES:] == historique[-GARDES:]
    assert "résumé" in compacte[0]["content"]
