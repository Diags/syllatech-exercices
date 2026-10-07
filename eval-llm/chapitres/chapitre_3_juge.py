"""Chapitre 3 — Le juge : ce qu'on lui confie, et ce qu'on ne lui confie pas.

Le cours présente le LLM-as-a-judge. Ce chapitre défend une position plus
précise : **n'appelez un juge que pour ce qu'aucune règle ne sait juger.**

    uv run python chapitres/chapitre_3_juge.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                  # noqa: E402
from jobportal.juge import juger_ancrage                # noqa: E402

SOURCES = [donnees.get_offre("JP-005")]

GRILLE = """  5 = exacte, complète, fidèle aux sources
  3 = correcte mais incomplète
  1 = fausse ou hors-sujet"""


def main() -> None:
    console.utf8()
    print("La grille du cours :\n" + GRILLE)
    print(f"\nSOURCE : {SOURCES[0].splitlines()[0]}\n")

    cas = [
        "SRE / plateforme Kubernetes chez Clauger, à Lyon, en CDI.",
        "Un poste d'infrastructure.",
        "Poste de SRE à Berlin, 90 000 € et quatre jours par semaine.",
    ]
    depart = time.perf_counter()
    for texte in cas:
        v = juger_ancrage(texte, SOURCES)
        print(f"   note {v.note}/5  ancrage {v.ancrage:>4.0%}  « {texte[:52]} »")
        print(f"             {v.raison}")
    duree = (time.perf_counter() - depart) * 1000

    print(f"\n   trois verdicts en {duree:.2f} ms, sans réseau, sans coût,")
    print("   et reproductibles à l'identique.")

    print("\nCE QUE CE JUGE-CI NE SAIT PAS FAIRE :")
    print("   · dire si le TON convient au public visé ;")
    print("   · repérer une réponse juste mais inutilement blessante ;")
    print("   · comparer deux réponses également ancrées.")
    print("   Pour cela, oui, il faut un modèle.")

    print("\nDEUX PRÉCAUTIONS si vous prenez un juge LLM :")
    print("   · jugez avec un AUTRE modèle que celui qui a répondu — un")
    print("     modèle qui s'auto-note se trouve remarquable ;")
    print("   · gardez une grille CHIFFRÉE et des exemples de chaque note,")
    print("     sinon deux exécutions du même juge ne donnent pas la même")
    print("     échelle, et votre historique de scores ne veut plus rien dire.")


if __name__ == "__main__":
    main()
