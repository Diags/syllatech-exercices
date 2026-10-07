"""Les six chapitres tournent, et disent ce qu'ils annoncent.

Un chapitre qui plante n'enseigne rien — et sur la branche « depart », ou le
code est a completer, c'est le mode de panne le plus probable. Ces tests
n'inspectent pas la prose : ils verifient que chaque chapitre va au bout et
que ses mesures cles sont bien dans sa sortie.
"""

from __future__ import annotations

import importlib
import re

import pytest

CHAPITRES = [
    ("chapitres.chapitre_1_demarrer", ["ar.dev/v1alpha1", "docker compose"]),
    ("chapitres.chapitre_2_artefacts", ["npx -y", "uvx ", "TaggedArtifact"]),
    ("chapitres.chapitre_3_publier", ["← personne", "hors ligne"]),
    ("chapitres.chapitre_4_consommer", ["latest", "labels="]),
    ("chapitres.chapitre_5_passerelle", ["SecretKeyRef", "iconUrl"]),
    ("chapitres.chapitre_6_gouvernance", ["0.0.0", "aucune"]),
]


@pytest.mark.parametrize("module, reperes",
                         CHAPITRES, ids=[m for m, _ in CHAPITRES])
def test_un_chapitre_va_au_bout(module, reperes, capsys):
    importlib.import_module(module).principal()
    sortie = capsys.readouterr().out
    assert len(sortie.splitlines()) > 40, "un chapitre trop court a plante"
    for repere in reperes:
        assert repere in sortie, f"{repere!r} absent de {module}"


def test_le_chapitre_3_compte_bien_trois_trous(capsys):
    importlib.import_module("chapitres.chapitre_3_publier").principal()
    sortie = capsys.readouterr().out
    assert sortie.count("← personne") == 3
    assert re.search(r"acceptes par les trois +3", sortie)


def test_le_chapitre_4_montre_l_etiquette_qui_bouge(capsys):
    importlib.import_module("chapitres.chapitre_4_consommer").principal()
    sortie = capsys.readouterr().out
    assert "skills/tri-candidatures" in sortie
    assert "skills/tri-candidatures-v2" in sortie
    assert re.search(r"references de l'agent qui cassent +0", sortie)
