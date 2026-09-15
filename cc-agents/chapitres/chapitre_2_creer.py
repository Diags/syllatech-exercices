"""Chapitre 2 — Creer un agent : le fichier, et ce que « tools » garantit.

    uv run python chapitres/chapitre_2_creer.py

Le cours dit que restreindre les outils « n'est pas qu'une optimisation, c'est
une garantie ». Une garantie, ca se verifie : on demande a chaque agent
d'ecrire, et on regarde qui y arrive.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.agents import (DOSSIER_AGENTS, Agent, OutilRefuse,  # noqa: E402
                              Rapport, Session, charger)


def tente_d_ecrire(agent: Agent, tache: str, outils: dict) -> Rapport:
    """Un agent qui essaie de corriger le code au lieu de le juger."""
    outils["Edit"]("auth/jetons.py", 'SECRET = "dev-secret-2019"',
                   'SECRET = os.environ["SECRET"]')
    return Rapport(agent.nom, "j'ai corrige le secret en dur")


def main() -> None:
    console.utf8()

    print("1. UN AGENT EST UN FICHIER\n")
    for nom, agent in sorted(charger().items()):
        outils = ", ".join(agent.outils)
        print(f"   {nom:<20} model: {agent.modele:<8} tools: {outils}")
    print(f"\n   Ils viennent de {DOSSIER_AGENTS.relative_to(DOSSIER_AGENTS.parent.parent)}/,")
    print("   se versionnent avec le code, et arrivent chez toute l'equipe au")
    print("   prochain git pull. Aucune API, aucun code.")

    print("\n2. « tools » N'EST PAS UN CONSEIL\n")
    session = Session()
    for nom in ("reviseur", "reviseur-permissif"):
        try:
            rapport = session.deleguer(nom, "relis auth/jetons.py", tente_d_ecrire)
            print(f"   {nom:<20} A ECRIT  → « {rapport.texte} »")
        except OutilRefuse as refus:
            print(f"   {nom:<20} REFUSE   → {refus}")

    print("\n   Les deux agents ont le meme prompt de revision et la meme envie")
    print("   de bien faire. Un seul a le droit d'ecrire — celui a qui on n'a")
    print("   PAS mis de champ « tools ». En son absence, un sous-agent herite")
    print("   de tous les outils de la session, Write et Edit compris.")
    print("\n   C'est le moindre privilege : la difference tient en une ligne de")
    print("   front-matter, et elle ne produit aucune erreur tant que l'agent")
    print("   n'essaie pas. Le jour ou il essaie, il est trop tard.")

    print("\n3. LA DESCRIPTION DECLENCHE, LE PROMPT DECRIT LE METIER\n")
    explorateur = charger()["explorateur"]
    print(f"   description ({len(explorateur.description)} signes) — lue pour CHOISIR l'agent :")
    print(f"     « {explorateur.description[:72]}… »")
    print(f"\n   prompt systeme ({len(explorateur.prompt)} signes) — lu une fois l'agent choisi :")
    print(f"     « {explorateur.prompt.splitlines()[0]} … »")
    print("\n   Le prompt de cet explorateur impose un format de rapport en")
    print("   quatre points. C'est ce qui le rend reutilisable tel quel dans le")
    print("   pipeline du chapitre 5 : l'orchestrateur sait ce qu'il recevra.")


if __name__ == "__main__":
    main()
