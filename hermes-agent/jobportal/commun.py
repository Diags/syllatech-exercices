"""Le peu que les six chapitres partagent."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
COMPETENCES = RACINE / "jobportal" / "skills"
sys.path.insert(0, str(RACINE))

# ⚠️ AVANT TOUT IMPORT DE HERMES, ET C'EST LA RAISON D'ETRE DE CE BLOC.
#
# Importer un module de Hermes suffit a creer son dossier de travail :
# SOUL.md, state.db, sessions/, logs/, skills/, memories/ — sous
# %LOCALAPPDATA%\hermes (Windows) ou ~/.hermes. Pas besoin d'avoir lance la
# commande `hermes` : l'import y suffit.
#
# Un cours ne doit pas laisser d'etat sur la machine de qui le suit. On
# bascule donc HERMES_HOME vers un dossier temporaire, et tout ce que les
# chapitres ecrivent — memoire, taches planifiees, journaux — y va.
#
# `setdefault` : qui veut viser sa vraie installation pose la variable
# lui-meme avant de lancer un chapitre.
#
# Constate en ecrivant ce projet : les premieres sondes ont laisse trente
# entrees « Fait 000 : xxx » dans un vrai MEMORY.md, et un test a ensuite vu
# 31 entrees la ou il en attendait une.
os.environ.setdefault(
    "HERMES_HOME", tempfile.mkdtemp(prefix="hermes-cours-"))


def utf8() -> None:
    """Hermes rend des messages avec des tirets cadratins et des guillemets.

    Sans ceci, la console Windows (cp1252) leve UnicodeEncodeError en
    affichant l'erreur de consolidation du MemoryStore — et l'on croit a un
    bug de Hermes.
    """
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:      # noqa: BLE001
            pass


def titre(numero: int, texte: str) -> None:
    print(f"\n{numero}. {texte}")
    print("   " + "─" * len(texte))


def ligne(gauche: str, droite: str, largeur: int = 34) -> None:
    print(f"   {gauche:<{largeur}} {droite}")


def competence(nom: str) -> str:
    """Le texte d'un SKILL.md du projet."""
    return (COMPETENCES / nom / "SKILL.md").read_text(encoding="utf-8")


def toutes_les_competences() -> list[tuple[str, str]]:
    return sorted((chemin.parent.name, chemin.read_text(encoding="utf-8"))
                  for chemin in COMPETENCES.glob("*/SKILL.md"))
