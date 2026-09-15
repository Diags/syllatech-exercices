"""Le peu que les six chapitres partagent."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))


def utf8() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:      # noqa: BLE001
            pass
    # Agno journalise chaque run de l'agent. C'est utile en production et
    # illisible dans un chapitre : les six en font des dizaines.
    logging.getLogger("agno").setLevel(logging.CRITICAL)


def titre(numero: int, texte: str) -> None:
    print(f"\n{numero}. {texte}")
    print("   " + "─" * len(texte))


def ligne(gauche: str, droite: str, largeur: int = 34) -> None:
    print(f"   {gauche:<{largeur}} {droite}")


def plier(texte: str, largeur: int = 64) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    return lignes + ([courante] if courante else [])
