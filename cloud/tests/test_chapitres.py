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
    ("chapitre_1_fondamentaux.py", "LES SLA SE MULTIPLIENT"),
    ("chapitre_2_calcul_stockage.py", "LA DONNEE REFROIDIT"),
    ("chapitre_3_reseau_securite.py", "CE QUE LA POLITIQUE ACCORDE"),
    ("chapitre_4_donnees.py", "UNE ANALYSE SUR LA PRODUCTION"),
    ("chapitre_5_couts.py", "ETEINDRE LE SOIR"),
    ("chapitre_6_certification.py", "UNE QUESTION, QUATRE VERDICTS"),
])
def test_chaque_chapitre_tourne(fichier: str, attendu: str):
    assert attendu in executer(fichier)


def test_le_chapitre_1_montre_les_trois_couches_inalienables():
    sortie = executer("chapitre_1_fondamentaux.py")

    assert "couches a votre charge              11           7           4"\
        in sortie
    assert "99.7003 %" in sortie
    assert "35 580,00 €" in sortie


def test_le_chapitre_2_mesure_le_cycle_de_vie():
    sortie = executer("chapitre_2_calcul_stockage.py")

    assert "3 312,00 €" in sortie
    assert "517,60 €" in sortie
    assert "(84 %)" in sortie


def test_le_chapitre_3_mesure_la_politique_et_le_trou_mfa():
    """⚠️ Les deux mesures phares du projet."""
    sortie = executer("chapitre_3_reseau_securite.py")

    assert "accorde 7 action(s) sur 12" in sortie
    assert "accorde 2 action(s) sur 12" in sortie
    assert "appel qui n'annonce RIEN" in sortie
    assert "est absente de la demande" in sortie
    assert "11" in sortie                     # les 11 adresses d'un /28


def test_le_chapitre_4_compare_les_couches():
    sortie = executer("chapitre_4_donnees.py")

    assert "x1.85" in sortie
    assert "systeme d'exploitation" in sortie


def test_le_chapitre_5_mesure_la_derive_et_le_facteur():
    sortie = executer("chapitre_5_couts.py")

    assert "x4.21" in sortie
    assert "48 % de la facture" in sortie
    assert "— (juste)" in sortie


def test_le_chapitre_6_montre_une_question_a_trois_reponses():
    sortie = executer("chapitre_6_certification.py")

    assert "3 sur 4" in sortie
    assert "rendre le bucket public en lecture" in sortie
    assert "aucun mot qui tranche" in sortie
    assert "contradictoires" in sortie


def test_les_six_chapitres_existent():
    assert len(sorted(CHAPITRES.glob("chapitre_*.py"))) == 6
