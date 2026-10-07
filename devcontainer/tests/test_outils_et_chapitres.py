"""Les deux outils, et les six chapitres.

Un outil dont le code de sortie ment ne sert à rien en CI ; un chapitre qui
plante n'enseigne rien. C'est tout ce que ces tests vérifient.
"""

from __future__ import annotations

import importlib
import re

import pytest

from jobportal.commun import A_CORRIGER, PORTAIL
from outils import ordre_features, verifier_devcontainer

PORTAIL_JSON = str(PORTAIL / "devcontainer.json")


def fautifs() -> list[str]:
    return [str(p) for p in sorted(A_CORRIGER.glob("*.json"))]


# ── verifier_devcontainer ───────────────────────────────────────────────

def test_le_portail_passe(capsys):
    assert verifier_devcontainer.principal([PORTAIL_JSON]) == 0
    sortie = capsys.readouterr().out
    assert "le schema publie accepte cette configuration" in sortie
    assert "⚠" not in sortie


def test_cinq_fautifs_sur_douze_sont_refuses(capsys):
    code = verifier_devcontainer.principal(fautifs() + ["--base", str(PORTAIL)])
    assert code == 5
    assert "5 fichier(s) refuse(s) sur 12" in capsys.readouterr().out


def test_les_avertissements_ne_font_pas_echouer(capsys):
    """Un fichier valide qui merite un commentaire sort en 0."""
    code = verifier_devcontainer.principal(
        [str(A_CORRIGER / "09-attach-lourd.json")])
    sortie = capsys.readouterr().out
    assert code == 0
    assert "⚠" in sortie
    assert "REFUS" not in sortie


def test_le_jsonc_est_signale(capsys):
    verifier_devcontainer.principal([PORTAIL_JSON])
    assert "json.load` echouerait" in capsys.readouterr().out


def test_la_virgule_finale_est_signalee(capsys):
    verifier_devcontainer.principal(
        [str(A_CORRIGER / "12-virgule-finale.json")])
    sortie = capsys.readouterr().out
    assert "virgule finale ligne(s) 8" in sortie
    assert "allowTrailingCommas: false" in sortie


def test_le_mode_brut_rend_les_erreurs_de_jsonschema(capsys):
    verifier_devcontainer.principal(
        [str(A_CORRIGER / "02-image-et-build.json"), "--brut"])
    sortie = capsys.readouterr().out
    # Le message brut designe la branche qu'on ne visait pas : c'est le
    # point du chapitre 1.
    assert "REFUS" in sortie
    assert "Unevaluated properties" in sortie


def test_le_mode_muet(capsys):
    verifier_devcontainer.principal(fautifs() + ["--muet"])
    assert capsys.readouterr().out.strip() == "5 fichier(s) refuse(s) sur 12"


# ── ordre_features ──────────────────────────────────────────────────────

def test_l_ordre_du_portail(capsys):
    assert ordre_features.principal([PORTAIL_JSON, "--tours"]) == 0
    sortie = capsys.readouterr().out
    assert "A installer : 4" in sortie
    assert "tour 1" in sortie and "tour 2" in sortie


def test_la_double_installation_est_visible(capsys):
    ordre_features.principal([str(A_CORRIGER / "11-ordre-impossible.json")])
    sortie = capsys.readouterr().out
    assert "A installer : 3" in sortie
    assert "tiree par dependsOn" in sortie


def test_le_env_montre_les_defauts(capsys):
    ordre_features.principal([PORTAIL_JSON, "--env"])
    sortie = capsys.readouterr().out
    assert "VERSION=21" in sortie
    assert "(defaut)" in sortie


def test_sans_feature_il_n_y_a_rien_a_ordonner(capsys):
    code = ordre_features.principal(
        [str(A_CORRIGER / "09-attach-lourd.json")])
    assert code == 0
    assert "Aucune Feature" in capsys.readouterr().out


# ── les chapitres ───────────────────────────────────────────────────────

CHAPITRES = [
    ("chapitres.chapitre_1_pourquoi", ["allowTrailingCommas", "oneOf"]),
    ("chapitres.chapitre_2_image", ["build.context", "pom.xml"]),
    ("chapitres.chapitre_3_features", ["installsAfter", "dependsOn", "tour"]),
    ("chapitres.chapitre_4_cycle", ["waitFor", "SANS shell"]),
    ("chapitres.chapitre_5_ports", ["_FA", "_REMOTE_USER"]),
    ("chapitres.chapitre_6_compose", ["stopCompose", "workspaceFolder"]),
]


@pytest.mark.parametrize("module, reperes", CHAPITRES,
                         ids=[m for m, _ in CHAPITRES])
def test_un_chapitre_va_au_bout(module, reperes, capsys):
    importlib.import_module(module).principal()
    sortie = capsys.readouterr().out
    assert len(sortie.splitlines()) > 50, "un chapitre trop court a plante"
    for repere in reperes:
        assert repere in sortie, f"{repere!r} absent de {module}"


def test_le_chapitre_3_montre_les_deux_ordres(capsys):
    importlib.import_module("chapitres.chapitre_3_features").principal()
    sortie = capsys.readouterr().out
    assert "dotnet → oryx → python" in sortie
    assert "2 / 3" in sortie


def test_le_chapitre_5_montre_la_collision(capsys):
    importlib.import_module("chapitres.chapitre_5_ports").principal()
    sortie = capsys.readouterr().out
    assert re.search(r"collision sur _FA\s+2fa et 22fa", sortie)
    assert "VERSION exportee malgre tout" in sortie
