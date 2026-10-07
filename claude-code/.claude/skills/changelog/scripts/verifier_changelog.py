#!/usr/bin/env python3
"""Verifie qu'un CHANGELOG.md a une section [Unreleased] et des rubriques valides."""

import re
import sys
from pathlib import Path

RUBRIQUES = {"Ajoute", "Ajouté", "Corrige", "Corrigé", "Modifie", "Modifié",
             "Retire", "Retiré", "Securite", "Sécurité"}


def verifier(texte: str) -> list[str]:
    soucis = []
    if "[Unreleased]" not in texte:
        soucis.append("section [Unreleased] absente")
    for m in re.finditer(r"^###\s+(.+)$", texte, re.MULTILINE):
        if m.group(1).strip() not in RUBRIQUES:
            soucis.append(f"rubrique inconnue : « {m.group(1).strip()} »")
    return soucis


def main() -> int:
    fichier = Path(sys.argv[1] if len(sys.argv) > 1 else "CHANGELOG.md")
    if not fichier.exists():
        print(f"  {fichier} absent")
        return 1
    soucis = verifier(fichier.read_text(encoding="utf-8"))
    for s in soucis:
        print(f"  REFUSE : {s}")
    if not soucis:
        print("  CHANGELOG valide")
    return 1 if soucis else 0


if __name__ == "__main__":
    sys.exit(main())
