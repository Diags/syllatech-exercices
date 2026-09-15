"""Le peu que les six chapitres partagent."""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

AMONT = RACINE / "amont"
FEATURES_AMONT = AMONT / "features"
SCHEMA = AMONT / "devContainer.base.schema.json"
SCHEMA_FEATURE = AMONT / "devContainerFeature.schema.json"
PORTAIL = RACINE / ".devcontainer"
A_CORRIGER = RACINE / "configs" / "a-corriger"


def utf8() -> None:
    """Les chapitres affichent « postCreateCommand » et des guillemets francais.

    Sans ceci, la console Windows (cp1252) leve UnicodeEncodeError au premier
    caractere accentue, et le chapitre meurt avant sa premiere mesure.
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


def tableau(entetes: list[str], lignes: list[list[str]],
            largeurs: list[int]) -> None:
    print("   " + "".join(e.ljust(l) for e, l in zip(entetes, largeurs)))
    print("   " + "".join("─" * (l - 2) + "  " for l in largeurs))
    for rang in lignes:
        print("   " + "".join(str(c).ljust(l) for c, l in zip(rang, largeurs)))


def plier(texte: str, largeur: int = 64) -> list[str]:
    lignes, courante = [], ""
    for mot in texte.split():
        if len(courante) + len(mot) + 1 > largeur:
            lignes.append(courante)
            courante = mot
        else:
            courante = f"{courante} {mot}".strip()
    return lignes + ([courante] if courante else [])
