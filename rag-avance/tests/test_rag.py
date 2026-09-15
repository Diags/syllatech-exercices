"""Ce que le pipeline doit garantir.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import pytest

from jobportal.corpus import DOCUMENTS
from jobportal.decoupe import decouper
from jobportal.evaluation import JEU, evaluer
from jobportal.rag import Rag
from jobportal.recherche import Index, Morceau, hybride, rrf
from jobportal.rerank import reclasser, score_paire


@pytest.fixture(scope="module")
def index() -> Index:
    return Index(decouper())


# --------------------------------------------------------------- decoupage

def test_chaque_morceau_porte_ses_metadonnees():
    """Un morceau sans source est un texte orphelin : impossible a citer."""
    for m in decouper():
        assert m.metadonnees["source"] in DOCUMENTS
        assert "section" in m.metadonnees


def test_les_morceaux_respectent_la_taille_demandee():
    for m in decouper(taille=200, chevauchement=0):
        assert len(m.texte) <= 260, f"morceau trop long : {len(m.texte)}"


def test_plus_les_morceaux_sont_petits_plus_ils_sont_nombreux():
    assert len(decouper(160, 0)) > len(decouper(420, 80)) > len(decouper(900, 80))


# --------------------------------------------------------------- recherche

def test_bm25_trouve_un_terme_rare(index):
    """Kafka n'apparait que dans une fiche : le test echouerait si l'IDF
    ne jouait pas son role."""
    assert index.bm25("kafka", 1)[0].metadonnees["source"] == "jp-001"


def test_les_trigrammes_rattrapent_une_faute_de_frappe(index):
    """LA raison d'etre de cette seconde jambe. « kubernete » sans s."""
    trouves = {m.metadonnees["source"] for m in index.vectorielle("kubernete", 3)}
    assert "jp-005" in trouves


def test_les_deux_moteurs_divergent_vraiment(index):
    """Deux moteurs qui classent pareil ne se completent pas — la fusion
    n'apporterait alors rien. C'est le defaut du premier essai de ce projet."""
    requetes = ["kubernete en production", "tests automatise",
                "experience agents IA", "accessible aux agents en atelier"]
    divergences = sum(1 for q in requetes
                      if [m.id for m in index.bm25(q, 3)] != [m.id for m in index.vectorielle(q, 3)])
    assert divergences >= 2, "les deux jambes se ressemblent trop"


def test_rrf_ne_regarde_que_les_rangs():
    a = Morceau("x", "", {}), Morceau("y", "", {})
    b = Morceau("y", "", {}), Morceau("z", "", {})
    fusion = [m.id for m in rrf([list(a), list(b)])]
    # y est present dans les deux listes : il doit passer devant.
    assert fusion[0] == "y"


# -------------------------------------------------------------- reclassement

def test_le_reclassement_prefere_la_couverture(index):
    q = "astreinte partagee entre quatre personnes"
    candidats = hybride(index, q, 6)
    premier = reclasser(q, candidats, 1)[0]
    assert premier.metadonnees["source"] == "jp-005"


def test_un_passage_sans_aucun_terme_marque_zero(index):
    assert score_paire("kubernetes terraform", Morceau("z", "Rien a voir ici.", {})) == 0.0


# ---------------------------------------------------------------- pipeline

def test_le_pipeline_avance_bat_le_naif():
    """LA propriete du projet. Si elle tombe, le cours ne demontre plus rien."""
    naif, avance = evaluer(Rag("naif")), evaluer(Rag("avance"))
    assert avance["rappel"] >= naif["rappel"]
    assert avance["f1"] > naif["f1"]


def test_le_rappel_est_complet_en_avance():
    assert evaluer(Rag("avance"))["rappel"] == 1.0


def test_chaque_cas_du_jeu_dit_pourquoi_il_existe():
    for cas in JEU:
        assert cas.get("pourquoi"), f"cas sans justification : {cas['question']}"


def test_une_question_hors_sujet_ne_ramene_rien():
    assert Rag("avance").repondre("zzzz qqqq").texte == "Information non disponible."


def test_la_reponse_cite_ses_sources():
    r = Rag("avance").repondre("Un poste Kubernetes a Lyon ?")
    assert r.sources and all(s in DOCUMENTS for s in r.sources)
    assert "[" in r.texte, "les passages doivent etre cites par leur identifiant"
