"""Chapitre 6 — Evaluer son RAG : commencer par ce qui ne coute rien.

    uv run python chapitres/chapitre_6_evaluer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.evaluation import JEU, evaluer          # noqa: E402
from jobportal.rag import Rag                          # noqa: E402


def main() -> None:
    console.utf8()
    print("Les quatre metriques du cours, et lesquelles coutent quoi :\n")
    print("   rappel du contexte      calculable EXACTEMENT, sans modele")
    print("   precision du contexte   calculable EXACTEMENT, sans modele")
    print("   fidelite                demande un juge")
    print("   pertinence de la reponse demande un juge")
    print("\n   Commencez toujours par les deux premieres : un RAG qui echoue")
    print("   echoue presque toujours a la RECUPERATION, et le mesurer coute")
    print("   zero. Un juge sur une recuperation cassee ne vous apprendra que")
    print("   ce que vous saviez deja.\n")

    for mode in ("naif", "avance"):
        r = evaluer(Rag(mode))
        print(f"{mode.upper()} — rappel {r['rappel']:.0%}, "
              f"precision {r['precision']:.0%}, F1 {r['f1']:.0%}")
        for cas, m in r["detail"]:
            if m.rappel < 1.0 or m.precision < 0.5:
                print(f"   · « {cas['question'][:44]:46} » "
                      f"rappel {m.rappel:>4.0%}  precision {m.precision:>4.0%}")
        print()

    print("LA HIERARCHIE QUI COMPTE :")
    print("   Un passage MANQUE est definitivement perdu — aucun modele ne")
    print("   repondra avec un document qu'il n'a pas recu. Un passage EN TROP")
    print("   n'est que du bruit, que le modele sait souvent ignorer.")
    print("   Surveillez donc le rappel EN PREMIER, et n'echangez jamais du")
    print("   rappel contre de la precision sans une raison ecrite.")

    print(f"\nLE COUT REEL : les {len(JEU)} cas de ce jeu ont ete annotes a la")
    print("   main — pour chaque question, quels documents DOIVENT remonter.")
    print("   C'est la vraie depense d'une evaluation, et c'est pour cela")
    print("   qu'on l'evite. Trente cas annotes valent mieux que trois cents")
    print("   generes : ces derniers mesurent la generation, pas la verite.")


if __name__ == "__main__":
    main()
