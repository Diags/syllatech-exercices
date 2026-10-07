"""Chapitre 3 — Qdrant, execute pour de vrai.

Le cours montre QdrantClient("localhost", port=6333). Peu de gens ont un
Qdrant qui tourne en lisant un cours. QdrantClient(":memory:") est le MEME
client, la MEME API, en memoire : tout ce fichier s'execute.

    uv run python chapitres/chapitre_3_qdrant.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.qdrant import chercher, client_prepare          # noqa: E402


def main() -> None:
    console.utf8()
    client = client_prepare()
    print("Collection creee et remplie, en memoire. Aucun Docker.\n")

    print("1. RECHERCHE SIMPLE — « Kubernetes a Lyon »\n")
    for r in chercher(client, "Kubernetes a Lyon", 4):
        print(f"   {r['score']:.3f}  {r['titre']}")

    print("\n2. AVEC UN FILTRE sur la charge utile — ville = Nantes\n")
    for r in chercher(client, "Kubernetes a Lyon", 4, ville="Nantes"):
        print(f"   {r['score']:.3f}  {r['titre']}")
    print("\n   Les scores BAISSENT : on demande les plus proches PARMI les")
    print("   offres nantaises, et elles ressemblent moins a la requete. Un")
    print("   filtre ne rend pas les resultats meilleurs, il change la")
    print("   population — c'est evident dit comme ca, et c'est pourtant la")
    print("   source d'etonnement numero un.")

    print("\n3. DEUX FILTRES — senior, a Paris\n")
    for r in chercher(client, "machine learning", 4, ville="Paris", senior=True):
        print(f"   {r['score']:.3f}  {r['titre']}")

    print("\nLE POINT QUI COMPTE VRAIMENT :\n")
    print("   Ce filtre n'est pas un WHERE applique apres coup. Qdrant le")
    print("   pousse DANS le parcours de l'index. La difference se voit sur")
    print("   un filtre selectif : en post-filtrage, l'index remonte ses k")
    print("   meilleurs, le filtre en elimine la quasi-totalite, et l'on rend")
    print("   deux resultats au lieu de cinq.")
    print("\n   Ce bug ne plante pas. Il rend moins de resultats que demande,")
    print("   en silence, et seulement sur les requetes tres filtrees — donc")
    print("   rarement en test, souvent en production.")

    print("\n   Pour passer a un vrai serveur, une seule ligne change :")
    print("      QdrantClient(\":memory:\")  →  QdrantClient(\"localhost\", port=6333)")


if __name__ == "__main__":
    main()
