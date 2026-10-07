"""Chapitre 1 — Pourquoi MCP : de M×N à M+N.

Le cours affirme que MCP fait passer les intégrations de M×N à M+N. C'est le
genre d'affirmation qu'on retient mieux en la voyant chiffrée, alors ce
chapitre la calcule au lieu de la répéter.

    uv run python chapitres/chapitre_1_pourquoi.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console               # noqa: E402

APPLICATIONS = ["Claude", "Cursor", "votre agent maison", "un pipeline CI"]
OUTILS = ["PostgreSQL", "GitHub", "le navigateur", "le job portal", "Slack"]


def sans_standard(m: int, n: int) -> int:
    """Chaque application doit coder un connecteur pour chaque outil."""
    return m * n


def avec_standard(m: int, n: int) -> int:
    """Chaque application parle le protocole une fois ; chaque outil l'expose
    une fois. Les deux côtés s'ignorent."""
    return m + n


def main() -> None:
    console.utf8()
    m, n = len(APPLICATIONS), len(OUTILS)
    print(f"{m} applications : {', '.join(APPLICATIONS)}")
    print(f"{n} outils       : {', '.join(OUTILS)}\n")

    avant, apres = sans_standard(m, n), avec_standard(m, n)
    print(f"  sans standard : {m} × {n} = {avant:>3} connecteurs à écrire et à maintenir")
    print(f"  avec MCP      : {m} + {n} = {apres:>3} implémentations")
    print(f"  économie      : {avant - apres} connecteurs, soit {1 - apres / avant:.0%}\n")

    print("Et l'écart se creuse avec la taille du parc :")
    print(f"  {'apps':>5} {'outils':>7} {'sans':>7} {'avec':>6}   rapport")
    for k in (5, 10, 20, 50):
        print(f"  {k:>5} {k:>7} {sans_standard(k, k):>7} {avec_standard(k, k):>6}   ×{sans_standard(k, k) / avec_standard(k, k):.1f}")

    print("\nCe n'est donc pas « un format de plus » : c'est le passage d'une")
    print("croissance quadratique à une croissance linéaire. À dix outils et dix")
    print("applications, on écrit 20 choses au lieu de 100.")


if __name__ == "__main__":
    main()
