"""Les six chapitres tournent, et disent toujours la meme chose.

Ce qui est verifie n'est pas « ca n'a pas plante » mais « la mesure
annoncee est bien celle qui s'affiche ». Un chapitre dont la narration se
desaccorde de sa mesure devient faux sans faire d'erreur.
"""

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
    ("chapitre_1_docker.py", "UNE IMAGE EST UN EMPILEMENT DE CALQUES"),
    ("chapitre_2_dockerfile.py", "L'ORDRE DES COUCHES"),
    ("chapitre_3_compose.py", "`depends_on` N'ATTEND PAS"),
    ("chapitre_4_kubernetes.py", "`kubectl apply` N'EXECUTE RIEN"),
    ("chapitre_5_avance.py", "`requests` PLACE, `limits` TUE"),
    ("chapitre_6_production.py", "`latest` NE DEPLOIE RIEN"),
])
def test_chaque_chapitre_tourne(fichier: str, attendu: str):
    assert attendu in executer(fichier)


def test_le_chapitre_1_extrait_le_secret_dune_couche():
    sortie = executer("chapitre_1_docker.py")

    assert "visible dans le conteneur : None" in sortie
    assert "DB_PASSWORD=mot-de-passe-factice-du-cours" in sortie
    assert "⚠️ tag mobile" in sortie
    assert "PID 1 = /bin/sh" in sortie


def test_le_chapitre_2_mesure_zero_couche_contre_cinq():
    """⚠️ La mesure phare du projet."""
    sortie = executer("chapitre_2_dockerfile.py")

    assert "Dockerfile.naif  → 5 couches, 114.5 s" in sortie
    assert "Dockerfile       → 0 couches, 0.0 s" in sortie
    assert "6 controles, 6 ecarts" in sortie


def test_le_chapitre_3_compte_une_connexion_refusee():
    sortie = executer("chapitre_3_compose.py")

    assert "→ 1 connexion(s) refusee(s)" in sortie
    assert "→ 0 connexion(s) refusee(s)" in sortie
    assert "cycle dans « depends_on »" in sortie


def test_le_chapitre_4_montre_le_service_sans_endpoint():
    sortie = executer("chapitre_4_kubernetes.py")

    assert "Pods existants juste apres l'apply : 0" in sortie
    assert "<none>" in sortie
    assert "Pods recrees               : 0" in sortie


def test_le_chapitre_5_mesure_trois_contre_zero():
    sortie = executer("chapitre_5_avance.py")

    assert "minimum de pods prets pendant la bascule : 3" in sortie
    assert "minimum de pods prets pendant la bascule : 0" in sortie
    assert "ProgressDeadlineExceeded" in sortie
    assert "Pods d'origine encore en place : 3 sur 3" in sortie
    assert "OOMKilled" in sortie


def test_le_chapitre_6_mesure_le_tag_latest():
    sortie = executer("chapitre_6_production.py")

    assert "manifestes des revisions 1 et 2 identiques : True" in sortie
    assert "manifestes des revisions 1 et 2 identiques : False" in sortie
    assert "ReplicaSets crees  : 1" in sortie
    assert "ReplicaSets crees  : 2" in sortie
    assert "rollback vers 1" in sortie


def test_les_six_chapitres_existent():
    assert len(sorted(CHAPITRES.glob("chapitre_*.py"))) == 6
