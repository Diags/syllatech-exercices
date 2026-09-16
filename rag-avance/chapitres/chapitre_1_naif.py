"""Chapitre 1 — Pourquoi le RAG naif echoue.

Il n'echoue pas parce que le modele est mauvais. Il echoue parce qu'on ne lui
a pas donne le bon passage — et aucun modele ne repond a partir d'un document
qu'il n'a pas recu.

    uv run python chapitres/chapitre_1_naif.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal.evaluation import JEU, evaluer       # noqa: E402
from jobportal.rag import Rag                       # noqa: E402


def main() -> None:
    console.utf8()
    naif, avance = evaluer(Rag("naif")), evaluer(Rag("avance"))

    print("Le meme corpus, le meme jeu de questions, deux pipelines :\n")
    print(f"   {'':8} {'rappel':>8} {'precision':>11} {'F1':>6}")
    for nom, r in (("naif", naif), ("avance", avance)):
        print(f"   {nom:8} {r['rappel']:>8.0%} {r['precision']:>11.0%} {r['f1']:>6.0%}")

    print("\n   naif   : un seul moteur, pas de fusion, pas de reclassement")
    print("   avance : deux moteurs fusionnes, puis reclasses\n")

    manques = [(cas, m) for cas, m in naif["detail"] if m.rappel < 1.0]
    if manques:
        print("Ce que le pipeline naif a MANQUE :\n")
        for cas, m in manques:
            print(f"   « {cas['question']} »  rappel {m.rappel:.0%}")
            print(f"      attendus : {', '.join(sorted(cas['attendus']))}")
            print(f"      pourquoi ce cas existe : {cas['pourquoi']}\n")

    print("Retenez la hierarchie : un passage MANQUE est definitivement perdu,")
    print("un passage EN TROP n'est que du bruit. C'est pourquoi on surveille")
    print("le rappel en premier — et pourquoi on recupere large avant de")
    print("trier fin (chapitre 4).")


if __name__ == "__main__":
    main()
