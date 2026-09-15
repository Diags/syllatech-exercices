"""Chapitre 6 — Ce que chaque agent coute, et quand ne pas deleguer.

    uv run python chapitres/chapitre_6_couts.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, depot, travaux            # noqa: E402
from jobportal.agents import COUT, Session, charger, fan_out, tokens  # noqa: E402


def main() -> None:
    console.utf8()

    print("1. LE CHAMP « model » : payer la puissance la ou elle change le resultat\n")
    agents = charger()
    session = Session()
    carte = session.deleguer("explorateur", "cartographie offres",
                             travaux.explorer("offres"))
    revue = session.deleguer("reviseur", "relis le diff", travaux.reviser(depot.diff()))

    print(f"   {'agent':<14}{'modele':<9}{'tokens':>8}{'x cout':>8}{'facture':>10}")
    for rapport in (carte, revue):
        a = agents[rapport.agent]
        print(f"   {a.nom:<14}{a.modele:<9}{rapport.tokens_internes:>8}"
              f"{COUT[a.modele]:>8.0f}{rapport.cout:>10.1f}")

    sur_sonnet = carte.tokens_internes * COUT["sonnet"] / 1000
    print(f"\n   L'explorateur sur Sonnet couterait {sur_sonnet:.1f} au lieu de "
          f"{carte.cout:.1f}.")
    print("   Il lit et resume : le raisonnement n'y change presque rien. Le")
    print("   reviseur, lui, tient tout entier dans son jugement — c'est la")
    print("   qu'on paie. Une ligne de front-matter, et la facture d'une")
    print("   exploration divise par trois.")

    print("\n2. LE FAN-OUT MULTIPLIE LA FACTURE\n")
    session = Session()
    modules = ("auth", "offres", "candidatures", "build")
    fan_out(session, [("explorateur", f"cartographie {m}", travaux.explorer(m))
                      for m in modules])
    print(f"   {len(modules)} explorateurs en parallele : facture {session.facture:.1f}")
    print(f"   Un seul explorateur                   : facture {carte.cout:.1f}")
    print("\n   Le temps d'attente, lui, n'a pas bouge. Un fan-out de cinq")
    print("   agents, c'est cinq additions — on parallelise pour un gain reel,")
    print("   jamais par reflexe.")

    print("\n3. LA MEILLEURE OPTIMISATION : NE PAS DELEGUER\n")
    petite = "renomme la variable « res » en « resultat » dans offres/api.py"
    direct = tokens(petite) + tokens(depot.lire("offres/api.py"))
    session = Session()
    delegue = session.deleguer("explorateur", petite, travaux.explorer("offres"))
    print(f"   {'en direct dans la session':<34}{direct:>7} tokens")
    print(f"   {'via un sous-agent':<34}{delegue.tokens_internes:>7} tokens")
    print(f"\n   {delegue.tokens_internes / direct:.0f}x plus cher, et plus lent, pour un")
    print("   contexte que la session possedait deja. Une retouche de trois")
    print("   lignes, une tache couplee au fil de la conversation : on la fait.")

    print("\n4. LE TABLEAU DE DECISION\n")
    cas = [
        ("cartographier un module inconnu", "oui", "volumineux en lecture, isolable"),
        ("auditer les dependances", "oui", "long, sans lien avec la conversation"),
        ("relire le diff avant commit", "oui", "isolable, et un avis neuf est un atout"),
        ("corriger trois lignes visibles", "non", "la session a deja le contexte"),
        ("continuer ce qu'on vient de decider", "non", "l'agent neuf ignore la decision"),
        ("ecrire dans le meme fichier qu'un autre", "non", "ce n'est pas parallelisable"),
    ]
    for tache, verdict, raison in cas:
        print(f"   {verdict:<5} {tache:<42}{raison}")

    print("\n   La question du chapitre 1, a chaque maillon : cette etape gagne-")
    print("   t-elle a partir dans un contexte neuf, ou perd-elle a le faire ?")


if __name__ == "__main__":
    main()
