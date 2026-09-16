"""Le peu que les six chapitres partagent."""

from __future__ import annotations

import contextlib
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


def titre(numero: int, texte: str) -> None:
    print(f"\n{numero}. {texte}")
    print("   " + "─" * len(texte))


def ligne(gauche: str, droite: str, largeur: int = 34) -> None:
    print(f"   {gauche:<{largeur}} {droite}")


@contextlib.contextmanager
def silence():
    """Tait le journal JSON du SDK, le temps d'une demonstration.

    `bedrock_agentcore.app` journalise chaque invocation — et chaque erreur
    interne, avec sa pile — en JSON sur la sortie. C'est juste ce qu'il faut
    en production et illisible dans un chapitre. On le tait donc ici, en
    sachant que **personne ne le tait en production, et personne ne le lit
    non plus** : c'est exactement pour cela que les pannes des sections 4 a 8
    passent inapercues.
    """
    journal = logging.getLogger("bedrock_agentcore.app")
    niveau, propage = journal.level, journal.propagate
    journal.setLevel(logging.CRITICAL)
    journal.propagate = False
    try:
        yield
    finally:
        journal.setLevel(niveau)
        journal.propagate = propage
