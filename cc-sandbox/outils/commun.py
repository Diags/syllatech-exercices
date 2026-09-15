"""Le peu que les six chapitres partagent.

Volontairement minuscule : un chapitre doit rester lisible seul, et un module
commun qui grossit finit par etre l'endroit ou le cours se cache.
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from outils.resolveur import Config   # noqa: E402


def utf8() -> None:
    """Les chapitres affichent « ~/.claude » et des guillemets francais.

    Sans ceci, la console Windows (cp1252) leve UnicodeEncodeError au premier
    caractere accentue, et le chapitre meurt avant sa premiere mesure.
    """
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:      # noqa: BLE001
            pass


def config(nom: str, portee: str = "projet") -> Config:
    return Config.fichier(RACINE / "configs" / f"{nom}.json", portee=portee)


def titre(numero: int, texte: str) -> None:
    print(f"\n{numero}. {texte}")
    print("   " + "─" * len(texte))


def ligne(gauche: str, droite: str, largeur: int = 34) -> None:
    print(f"   {gauche:<{largeur}} {droite}")
