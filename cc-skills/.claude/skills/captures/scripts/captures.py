#!/usr/bin/env python3
"""Simule la capture des pages du job portal.

Pas de navigateur ici : ce projet doit tourner apres un « uv sync ». Ce que
le script demontre, c'est le POINT DU CHAPITRE — un script livre AVEC la
skill, invoque par un chemin qui part de la skill et non du dossier courant.
"""

import sys
from pathlib import Path

PAGES = ["accueil", "offres", "offre-detail", "candidature", "profil", "admin"]
CASSEES = {"admin"}     # pour montrer qu'un echec se signale, pas se tait


def main() -> int:
    dossier = Path(__file__).resolve().parent.parent
    print(f"  script lance depuis : {dossier.name}/scripts/")
    print(f"  (CLAUDE_SKILL_DIR aurait pointe ici : {dossier})\n")

    echecs = []
    for page in PAGES:
        if page in CASSEES:
            print(f"  ECHEC  {page}")
            echecs.append(page)
        else:
            print(f"  ok     {page}")

    print(f"\n  {len(PAGES) - len(echecs)}/{len(PAGES)} pages capturees")
    if echecs:
        print(f"  a corriger : {', '.join(echecs)}")
    return 1 if echecs else 0


if __name__ == "__main__":
    sys.exit(main())
