"""Les six chapitres tournent, et disent toujours la meme chose."""

from __future__ import annotations

import io
import runpy
from contextlib import redirect_stdout
from pathlib import Path

import pytest

CHAPITRES = Path(__file__).resolve().parent.parent / "chapitres"

_SORTIES: dict[str, str] = {}


def executer(nom: str) -> str:
    if nom not in _SORTIES:
        capture = io.StringIO()
        with redirect_stdout(capture):
            runpy.run_path(str(CHAPITRES / nom), run_name="__main__")
        _SORTIES[nom] = capture.getvalue()
    return _SORTIES[nom]


@pytest.mark.parametrize("fichier, attendu", [
    ("chapitre_1_demarrer.py", "`kubectl apply` NE DEMARRE RIEN"),
    ("chapitre_2_crds.py", "CE QUE LE SCHEMA ELAGUE"),
    ("chapitre_3_outils.py", "LE MEME AGENT, SANS SES YEUX"),
    ("chapitre_4_a2a.py", "CE QUE LA DELEGATION COUTE"),
    ("chapitre_5_observabilite.py", "LA TRACE QUI SE COUPE EN DEUX"),
    ("chapitre_6_spring.py", "UN 200 QUI REND DU HTML"),
])
def test_chaque_chapitre_tourne(fichier: str, attendu: str):
    assert attendu in executer(fichier)


def test_le_chapitre_1_montre_lagent_orphelin():
    sortie = executer("chapitre_1_demarrer.py")

    assert "Conditions de l'agent     : aucune" in sortie
    assert "ModelConfig « modele-qui-nexiste-pas » introuvable" in sortie
    assert "Ready=False" in sortie


def test_le_chapitre_2_mesure_lelagage():
    """⚠️ La mesure phare du projet."""
    sortie = executer("chapitre_2_crds.py")

    assert "admis, 2 champ(s) elague(s) en silence" in sortie
    assert "spec.declarative.systemMesssage" in sortie
    assert "systemMessage    = ''" in sortie
    assert "maxIterations    = 10" in sortie


def test_le_chapitre_3_mesure_le_grounding():
    sortie = executer("chapitre_3_outils.py")

    assert "liveness" in sortie                     # la reponse de memoire
    assert "OutOfMemoryError" in sortie             # la reponse ancree
    assert "n'est pas accorde a cet agent" in sortie
    assert "supprime" in sortie                     # le prompt n'arrete rien


def test_le_chapitre_4_compte_les_appels():
    sortie = executer("chapitre_4_a2a.py")

    assert "cycle de delegation : agent-ping → agent-pong → agent-ping" in sortie
    assert "invoke_agent agent-etat" in sortie
    assert "8 appels au modele contre 5" in sortie


def test_le_chapitre_5_casse_la_trace():
    sortie = executer("chapitre_5_observabilite.py")

    assert "gen_ai.usage.input_tokens" in sortie
    assert "RIEN N'A ECHOUE" in sortie
    assert "traceparent" in sortie


def test_le_chapitre_6_montre_les_deux_sens():
    sortie = executer("chapitre_6_spring.py")

    assert "POST /api/a2a/kagent/assistant-sre" in sortie
    assert "elague : ['userId', 'priorite']" in sortie
    assert "et non en JSON" in sortie
    assert "rechercher_offres" in sortie


def test_les_six_chapitres_existent():
    assert len(sorted(CHAPITRES.glob("chapitre_*.py"))) == 6
