"""Les six chapitres tournent, et disent ce qu'ils annoncent.

Un chapitre qui plante n'enseigne rien — et sur la branche « depart », où le
code est à compléter, c'est le mode de panne le plus probable. Ces tests
n'inspectent pas la prose : ils vérifient que chaque chapitre va au bout et
que ses mesures clés sont bien dans sa sortie.
"""

from __future__ import annotations

import importlib
import re

import pytest

CHAPITRES = [
    ("chapitres.chapitre_1_demarrer", ["low-level API", "pathPrefix", "27"]),
    ("chapitres.chapitre_2_llm", ["openAI", "failover", "conditional"]),
    ("chapitres.chapitre_3_mcp", ["prefixMode", "openapi", "failClosed"]),
    ("chapitres.chapitre_4_a2a", ["a2a", "endpointPicker", "selfHosted"]),
    ("chapitres.chapitre_5_securite", ["optional", "fail to deny", "creditCard"]),
    ("chapitres.chapitre_6_integration", ["ANTHROPIC_BASE_URL", "CEL"]),
]


@pytest.mark.parametrize("module, reperes", CHAPITRES,
                         ids=[m for m, _ in CHAPITRES])
def test_un_chapitre_va_au_bout(module, reperes, capsys):
    importlib.import_module(module).principal()
    sortie = capsys.readouterr().out
    assert len(sortie.splitlines()) > 60, "un chapitre trop court a plante"
    for repere in reperes:
        assert repere in sortie, f"{repere!r} absent de {module}"


def test_le_chapitre_1_compte_les_exemples(capsys):
    importlib.import_module("chapitres.chapitre_1_demarrer").principal()
    sortie = capsys.readouterr().out
    assert re.search(r"acceptees par le schema publie\s+27", sortie)


def test_le_chapitre_2_evalue_vraiment_le_cel(capsys):
    importlib.import_module("chapitres.chapitre_2_llm").principal()
    sortie = capsys.readouterr().out
    for modele in ("tri-soigne", "tri-rapide"):
        assert modele in sortie
    assert "hors CEL standard" in sortie


def test_le_chapitre_5_montre_le_deny_qui_laisse_passer(capsys):
    importlib.import_module("chapitres.chapitre_5_securite").principal()
    sortie = capsys.readouterr().out
    section = sortie.split("5. LA MEME REGLE")[1].split("6. LA FORME")[0]
    assert "AUTORISE" in section
    assert "faux positif" in sortie


def test_le_chapitre_6_detecte_le_chevauchement(capsys):
    importlib.import_module("chapitres.chapitre_6_integration").principal()
    sortie = capsys.readouterr().out
    assert re.search(r"requetes que DEUX routes attrapent\s+2", sortie)
