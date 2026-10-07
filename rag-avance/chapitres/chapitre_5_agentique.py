"""Chapitre 5 — RAG agentique : quand une seule recherche ne suffit pas.

Un RAG classique fait UNE recherche avec la question telle quelle. Certaines
questions ne s'y pretent pas — et ce chapitre montre lesquelles, et pourquoi.

    uv run python chapitres/chapitre_5_agentique.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.rag import Rag                          # noqa: E402

COMPARAISON = "Compare les postes de Lyon et celui de Nantes"


def decomposer(question: str) -> list[str]:
    """La decomposition qu'un agent ferait faire au modele.

    Ici elle est ecrite a la main — le projet tourne sans modele. Ce qui
    compte n'est pas QUI decompose, mais le fait que LA DECOMPOSITION SOIT
    NECESSAIRE : c'est ce que la comparaison ci-dessous etablit.
    """
    if "compare" in question.lower():
        return ["postes a Lyon", "poste a Nantes"]
    return [question]


def main() -> None:
    console.utf8()
    rag = Rag("avance")

    print(f"Question : « {COMPARAISON} »\n")
    print("1. UNE SEULE RECHERCHE, avec la question telle quelle :\n")
    directe = rag.recuperer(COMPARAISON, 3)
    sources_directes = sorted({m.metadonnees["source"] for m in directe})
    for m in directe:
        print(f"   {m.id:<10} {m.texte.strip().splitlines()[0][:54]}")
    print(f"\n   documents couverts : {', '.join(sources_directes)}")

    print("\n2. DECOMPOSEE EN DEUX RECHERCHES :\n")
    toutes = set()
    for sous in decomposer(COMPARAISON):
        res = rag.recuperer(sous, 2)
        srcs = sorted({m.metadonnees["source"] for m in res})
        toutes |= set(srcs)
        print(f"   « {sous} » → {', '.join(srcs)}")
    print(f"\n   documents couverts : {', '.join(sorted(toutes))}")

    manques = toutes - set(sources_directes)
    if manques:
        print(f"\n   La recherche unique avait MANQUE : {', '.join(sorted(manques))}")

    print("\nPOURQUOI LA RECHERCHE UNIQUE ECHOUE ICI :")
    print("   « Compare A et B » est une question dont AUCUN document ne")
    print("   contient la reponse. Chercher la phrase entiere ramene ce qui")
    print("   ressemble le plus a la phrase entiere — c'est-a-dire souvent")
    print("   un seul des deux cotes, et jamais la comparaison.")
    print("\n   Un agent ne cherche pas mieux : il cherche PLUSIEURS FOIS, et")
    print("   il decide quand s'arreter. C'est la seule difference, et elle")
    print("   suffit a traiter une categorie entiere de questions.")
    print("\n   Le prix : deux fois plus d'appels, une latence doublee, et un")
    print("   comportement moins previsible. Ne rendez pas agentique un RAG")
    print("   dont les questions tiennent en une recherche.")


if __name__ == "__main__":
    main()
