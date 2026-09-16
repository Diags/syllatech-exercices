"""Chapitre 1 — Pourquoi deleguer : la meme tache, mesuree deux fois.

    uv run python chapitres/chapitre_1_pourquoi.py

Le cours affirme qu'un sous-agent « ne renvoie que sa conclusion » et que la
fenetre principale « reste legere ». Ici, on compte.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, depot, travaux        # noqa: E402
from jobportal.agents import Contexte, Session, tokens  # noqa: E402


def sans_deleguer(module: str) -> Contexte:
    """La session fait le travail elle-meme : tout atterrit chez elle."""
    contexte = Contexte("session principale — sans delegation")
    for chemin in depot.lister(module):
        contexte.ajouter("Read", depot.lire(chemin))
    return contexte


def main() -> None:
    console.utf8()
    module = "offres"

    print("1. LA SESSION EXPLORE ELLE-MEME\n")
    seul = sans_deleguer(module)
    print(f"   {len(seul.entrees)} fichiers lus, {seul.taille} tokens dans la fenetre.")
    print("   Ces tokens y RESTENT : chaque tour suivant les repaie, et les")
    print("   consignes de depart s'y diluent.\n")

    print("2. LA SESSION DELEGUE\n")
    session = Session()
    rapport = session.deleguer("explorateur", f"cartographie le module {module}",
                               travaux.explorer(module))
    print(rapport.texte)
    print(f"   L'agent a charge {rapport.tokens_internes} tokens dans SON contexte.")
    print(f"   La session principale en recoit {rapport.tokens_rendus}.\n")

    print("3. LE RAPPORT\n")
    facteur = seul.taille / max(rapport.tokens_rendus, 1)
    print(f"   {'sans delegation':<34}{seul.taille:>7} tokens")
    print(f"   {'avec delegation':<34}{rapport.tokens_rendus:>7} tokens")
    print(f"   {'reste chez l agent, puis disparait':<34}"
          f"{rapport.tokens_internes:>7} tokens")
    print(f"\n   La fenetre principale porte {facteur:.0f}x moins.")

    print("\n4. MAIS DELEGUER N'EST PAS GRATUIT\n")
    trois_lignes = "corrige la faute de frappe ligne 12 de offres/api.py"
    cout_direct = tokens(trois_lignes) + tokens(depot.lire("offres/api.py"))
    print(f"   Corriger trois lignes, en direct  : {cout_direct:>6} tokens")
    print(f"   Les memes, via un sous-agent      : {rapport.tokens_internes:>6} tokens")
    print("     (prompt systeme + exploration + rapport, pour trois lignes)")
    print("\n   La regle du chapitre, verifiee dans les deux sens : on delegue")
    print("   l'ISOLABLE et le VOLUMINEUX EN LECTURE. Pour une retouche que la")
    print("   session a deja sous les yeux, ouvrir un sous-agent coute plus")
    print("   cher que de la faire — et fait perdre le contexte de ce qu'on")
    print("   vient de decider.")


if __name__ == "__main__":
    main()
