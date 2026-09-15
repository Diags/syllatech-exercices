"""Le peu que les six chapitres partagent."""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

SECRET_JWT = "secret-de-demonstration-de-la-passerelle"


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


def config(nom: str = "passerelle") -> Path:
    return RACINE / "config" / f"{nom}.yaml"


EQUIPES = (("data", {"budget_max": 1.00}),
           ("rh", {"budget_max": 0.02, "modeles": ("rapide",)}))


def monter(nom: str = "passerelle", equipes=EQUIPES):
    """La passerelle complete : proxy + registre + coffre.

    C'est le montage que fait `docker-compose` en production — gateway, proxy,
    base des cles — reduit a trois objets.
    """
    from .budgets import Registre
    from .passerelle import Passerelle
    from .proxy import Proxy

    registre = Registre()
    coffre = {equipe: registre.generer(equipe, **options).cle
              for equipe, options in equipes}
    return Passerelle(proxy=Proxy.depuis(config(nom)), registre=registre,
                      secret_jwt=SECRET_JWT, coffre=coffre)
