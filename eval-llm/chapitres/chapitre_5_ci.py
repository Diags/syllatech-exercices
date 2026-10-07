"""Chapitre 5 — Le test de non-régression, et le seuil qui le rend utile.

    uv run python chapitres/chapitre_5_ci.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.agent import agent                      # noqa: E402
from jobportal.evaluation import evaluer               # noqa: E402

SEUIL = 0.90


def main() -> None:
    console.utf8()
    print(f"Le seuil de non-régression : {SEUIL:.0%}\n")
    for v in ("v1", "v2", "v3"):
        score = evaluer(agent(v)).score
        verdict = "PASSE" if score >= SEUIL else "BLOQUE la fusion"
        print(f"   {v}  score {score:.2f}   → {verdict}")

    print("\nC'est tout le dispositif : trois lignes dans un test, et une")
    print("modification de prompt qui dégrade la qualité ne peut plus être")
    print("fusionnée sans que quelqu'un le décide explicitement.")

    print("\nCOMMENT CHOISIR LE SEUIL — la question qu'on élude :")
    print("   · trop bas, il ne bloque jamais rien et rassure à tort ;")
    print("   · trop haut, il bloque tout, on le désactive « temporairement »,")
    print("     et il ne revient jamais.")
    print("   La règle qui marche : le prendre LÉGÈREMENT SOUS le score")
    print("   actuel, et le remonter à chaque amélioration confirmée. Un")
    print("   seuil est un cliquet, pas un objectif.")

    print("\nEN INTÉGRATION CONTINUE :")
    print("   .github/workflows/eval.yml, sur chaque PR touchant les prompts")
    print("   ou l'agent :  pytest tests/test_eval.py")
    print("\n   Et faites échouer le test avec le SCORE dans le message. Un")
    print("   « assert False » sans chiffre oblige à rejouer l'évaluation en")
    print("   local pour savoir de combien on a régressé.")


if __name__ == "__main__":
    main()
