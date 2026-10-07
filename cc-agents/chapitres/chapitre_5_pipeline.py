"""Chapitre 5 — Le pipeline complet sur le job portal.

    uv run python chapitres/chapitre_5_pipeline.py

Explorer → implementer → relire → corriger. Sequentiel par nature : chaque
etape consomme le livrable de la precedente.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, depot, travaux   # noqa: E402
from jobportal.agents import Session, tokens    # noqa: E402


def implementer(rapport_exploration: str) -> list:
    """L'etape que l'on NE delegue pas.

    Le cours l'explique : c'est le maillon ou le contexte « conventions du
    projet » doit etre vif. La session vient de lire le rapport de
    l'explorateur ; elle ecrit en le suivant. Deleguer ici ferait repartir un
    agent qui ignore tout de ce qu'on vient de decider.
    """
    return depot.diff()


def main() -> None:
    console.utf8()
    session = Session()

    print("ETAPE 1 — l'explorateur cartographie le terrain\n")
    carte = session.deleguer("explorateur", "cartographie le module candidatures",
                             travaux.explorer("candidatures"))
    print("   " + carte.texte.replace("\n", "\n   "))
    print(f"   lu par l'agent : {carte.tokens_internes} tokens · "
          f"remonte : {carte.tokens_rendus}")

    print("\nETAPE 2 — la session implemente, sans deleguer\n")
    diff = implementer(carte.texte)
    print(f"   {len(diff)} fichiers ecrits, en suivant les conventions du rapport.")
    print("   Aucun sous-agent ici : le contexte « ce qu'on vient de decider »")
    print("   est vif dans la session, et un agent neuf l'ignorerait.")

    print("\nETAPE 3 — le reviseur relit le diff\n")
    revue = session.deleguer("reviseur", "relis le diff de la branche",
                             travaux.reviser(diff))
    for ligne in revue.texte.splitlines():
        print("   " + ligne)

    print("\nETAPE 4 — la session corrige le confirme, et commite\n")
    confirmes = [c for c in revue.constats if c.get("verdict") == "confirme"]
    for c in confirmes:
        print(f"   corrige {c['fichier']}:{c['ligne']} — {c['message']}")
    doutes = [c for c in revue.constats if c.get("verdict") == "douteux"]
    for c in doutes:
        print(f"   a trancher {c['fichier']}:{c['ligne']} — {c['message']}")

    print("\n---\n")
    print("CE QUE LE PIPELINE A COUTE, ET CE QU'IL A EVITE\n")
    tout = sum(tokens(depot.lire(c)) for c in depot.lister())
    print(f"   {'le depot entier':<38}{tout:>7} tokens")
    print(f"   {'contexte de la session a la fin':<38}"
          f"{session.contexte.taille:>7} tokens")
    print(f"   {'dont rapport d exploration':<38}{carte.tokens_rendus:>7} tokens")
    print(f"   {'dont rapport de revue':<38}{revue.tokens_rendus:>7} tokens")
    print(f"\n   La session a orchestre une exploration de {carte.tokens_internes}")
    print(f"   tokens et une revue de {revue.tokens_internes}, en n'en portant")
    print(f"   que {session.contexte.taille}. Le savoir a circule sous forme de")
    print("   rapports, jamais d'un contexte geant — c'est exactement ce qui")
    print("   rend le resultat plus fiable qu'une passe unique.")
    print(f"\n   Facture relative : {session.facture:.1f} (unites Haiku x 1000 tokens)")


if __name__ == "__main__":
    main()
