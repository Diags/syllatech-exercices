"""Chapitre 2 — Construire un jeu de test qui sert à quelque chose.

Trois types de cas, et c'est le deuxième et le troisième qui font tout le
travail. Ce chapitre le démontre en chiffres.

    uv run python chapitres/chapitre_2_dataset.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.agent import agent                      # noqa: E402
from jobportal.evaluation import evaluer               # noqa: E402
from jobportal.jeu import JEU, PAR_TYPE                # noqa: E402


def main() -> None:
    console.utf8()
    print(f"Le jeu compte {len(JEU)} cas :\n")
    for t, cas in PAR_TYPE.items():
        print(f"   {t:<12} {len(cas):>2} cas — {cas[0]['pourquoi']}")

    print("\nMaintenant, la démonstration. Voici l'agent v1, évalué")
    print("UNIQUEMENT sur les cas nominaux :\n")
    v1 = agent("v1")
    nominal = evaluer(v1, PAR_TYPE["nominal"])
    print(f"   score : {nominal.score:.0%}   — irréprochable.")

    print("\nLe même agent, sur le jeu complet :\n")
    complet = evaluer(v1)
    for t, s in sorted(complet.par_type().items()):
        alerte = "  ← " + "!" * 3 if s < 0.6 else ""
        print(f"   {t:<12} {s:>5.0%}{alerte}")
    print(f"   {'GLOBAL':<12} {complet.score:>5.0%}")

    print("\nVoilà le piège du chapitre. Un jeu qui ne contient que des cas")
    print("nominaux donne 100 % à un agent qui INVENTE quand il ne sait pas.")
    print("C'est même le plus sûr moyen de ne jamais voir une hallucination :")
    print("on ne lui pose que des questions dont on connaît la réponse.")
    print("\nEt remarquez le score global : il masque déjà l'effondrement.")
    print("Ne suivez jamais un score agrégé sans sa ventilation.")


if __name__ == "__main__":
    main()
