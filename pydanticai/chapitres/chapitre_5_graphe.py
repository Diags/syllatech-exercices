"""Chapitre 5 — Pydantic Graph et tests.

    uv run python chapitres/chapitre_5_graphe.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                # noqa: E402
from jobportal.donnees import DatabaseConn                   # noqa: E402
from jobportal.graphe import SEUIL, conseiller, graphe       # noqa: E402
from jobportal.modele import modele_conseiller               # noqa: E402


async def demonstration() -> None:
    print("1. L'API A CHANGE — la video montre une forme qui ne marche plus\n")
    print("     graphe = Graph(nodes=[Analyser, Decider, Rediger])   # TypeError\n")
    from pydantic_graph import Graph
    try:
        Graph(nodes=[])
        print("   (l'ancienne forme fonctionne sur cette installation)")
    except TypeError as e:
        print(f"   TypeError: {str(e)[:88]}…")
    print("\n   « Graph » n'est plus construit directement : il est PRODUIT")
    print("   par un GraphBuilder. Les etapes s'ecrivent comme des fonctions")
    print("   decorees, les aretes se declarent, et build() rend le graphe.")

    print("\n2. LE GRAPHE SE LIT SANS S'EXECUTER\n")
    for ligne in graphe.render().splitlines():
        print("   " + ligne)
    print("\n   C'est du Mermaid : collez-le dans n'importe quel rendu Markdown.")
    print("   Un graphe qu'on peut DESSINER est un graphe qu'on peut relire en")
    print("   revue — ce qu'aucune boucle d'agent ne permet.")

    print(f"\n3. LES DEUX BRANCHES, PARCOURUES POUR DE VRAI (seuil = {SEUIL})\n")
    db = DatabaseConn()
    compte = {"analyser": 0, "renoncer": 0}
    for candidat in sorted(db.noms):
        sortie, etat = await conseiller(candidat, db, modele_conseiller())
        prise = etat.etapes[-1]
        compte[prise] += 1
        if compte[prise] <= 2:
            print(f"   candidat {candidat:<3}{len(etat.offres)} offre(s)  "
                  f"→ {' → '.join(etat.etapes)}")
            print(f"       {sortie[:78]}")
    print(f"\n   {compte['analyser']} candidats analyses, "
          f"{compte['renoncer']} ecartes sans appeler de modele.")

    print("\n4. POURQUOI CETTE BRANCHE VAUT DE L'ARGENT\n")
    print("   Dans un agent unique, la decision « ai-je assez de matiere ? »")
    print("   serait prise PAR le modele : elle serait payee, et parfois mal")
    print("   prise. Ici elle est prise par du code — gratuitement, toujours")
    print("   de la meme facon, et elle se teste sans modele du tout.")
    print(f"\n   {compte['renoncer']} appels de modele evites sur {len(db.noms)},")
    print("   avec une regle de trois lignes.")

    print("\n5. L'ETAT EST INSPECTABLE A CHAQUE ETAPE\n")
    sortie, etat = await conseiller(3, db, modele_conseiller())
    print(f"   candidat        {etat.candidat_id}")
    print(f"   offres lues     {len(etat.offres)}")
    print(f"   etapes          {etat.etapes}")
    print(f"   recommandation  {type(etat.recommandation).__name__}")
    print(f"   confiance       {etat.recommandation.confiance}")
    print("\n   C'est ce qui rend un graphe testable : on n'assert pas sur une")
    print("   sortie finale opaque, on assert sur le CHEMIN. « Ce candidat a")
    print("   bien evite l'appel de modele » est une assertion utile.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
