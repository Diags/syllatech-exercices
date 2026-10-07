"""Chapitre 2 — Le decoupage, et ce qu'il decide pour toujours.

    uv run python chapitres/chapitre_2_decoupage.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.decoupe import SEPARATEURS, decouper    # noqa: E402
from jobportal.evaluation import evaluer               # noqa: E402
from jobportal.rag import Rag                          # noqa: E402
from jobportal.recherche import Index                  # noqa: E402


def main() -> None:
    console.utf8()
    print("Les separateurs, essayes DANS L'ORDRE :")
    for s in SEPARATEURS:
        print(f"   {s!r}")
    print("   → on coupe d'abord aux titres, en dernier recours au milieu")
    print("     d'une phrase. C'est ce qui garde les morceaux lisibles.\n")

    print("Effet de la taille des morceaux sur la recuperation :\n")
    print(f"   {'taille':>7} {'chevauch.':>10} {'morceaux':>9} {'rappel':>8} {'precision':>11}")
    for taille, chev in ((160, 0), (160, 40), (420, 80), (900, 80), (2000, 0)):
        rag = Rag("avance")
        rag.index = Index(decouper(taille, chev))
        r = evaluer(rag)
        print(f"   {taille:>7} {chev:>10} {len(rag.index.morceaux):>9} "
              f"{r['rappel']:>8.0%} {r['precision']:>11.0%}")

    print("\n   LISEZ CE TABLEAU AVEC ATTENTION, il dit deux choses.")
    print("\n   1. La precision s'effondre quand les morceaux grossissent :")
    print("      67 % a 160 signes, 39 % a 900. Un gros morceau ramene la")
    print("      reponse ET tout ce qui l'entoure — donc du bruit, a chaque")
    print("      fois, dans le contexte envoye au modele.")
    print("\n   2. Le rappel, lui, NE BOUGE PAS. 100 % partout.")
    print("\n   Ce second point n'est pas une bonne nouvelle : c'est la LIMITE")
    print("   DE LA METRIQUE. Elle compte les DOCUMENTS retrouves, et un")
    print("   document reste retrouve quelle que soit la facon dont on l'a")
    print("   coupe. Le degat du decoupage — une information tranchee en deux")
    print("   dont on ne recupere qu'une moitie — se produit a l'interieur du")
    print("   document, la ou cette mesure ne regarde pas.")
    print("\n   Pour le voir, il faudrait mesurer au PASSAGE : le morceau qui")
    print("   porte la reponse est-il dans ce qu'on a recupere ? C'est plus")
    print("   cher a annoter, et c'est pour cela qu'on s'en passe souvent — en")
    print("   croyant alors, a tort, que le decoupage n'a pas d'importance.")
    print("\n   Retenez surtout ceci : une metrique qui ne bouge jamais ne")
    print("   valide pas votre systeme, elle vous cache un angle mort.")
    print("\n   Quant au chevauchement, il ne change rien ici (28 morceaux dans")
    print("   les deux cas) : le corpus est trop structure pour qu'une coupure")
    print("   tombe au milieu d'une phrase. Sur du texte continu, il compte.")

    m = decouper()[0]
    print(f"\nUn morceau, avec ses metadonnees :\n")
    print(f"   id       : {m.id}")
    print(f"   source   : {m.metadonnees['source']}")
    print(f"   section  : {m.metadonnees['section']}")
    print(f"   texte    : {m.texte.strip().splitlines()[0][:58]}…")
    print("\n   Sans metadonnees, un morceau retrouve est un texte orphelin :")
    print("   on ne peut ni le citer, ni filtrer dessus, ni expliquer d'ou il")
    print("   vient. La citation n'est pas un ornement — c'est ce qui permet a")
    print("   l'utilisateur de verifier.")


if __name__ == "__main__":
    main()
