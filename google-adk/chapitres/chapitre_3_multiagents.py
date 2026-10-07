"""Chapitre 3 — La delegation : c'est la DESCRIPTION qui decide.

    uv run python chapitres/chapitre_3_multiagents.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk import Agent                                # noqa: E402

from jobportal import console                               # noqa: E402
from jobportal.agents import coordinateur, modele           # noqa: E402
from jobportal.donnees import rechercher_offres, salaire_du_marche  # noqa: E402
from jobportal.harnais import lancer                        # noqa: E402
from jobportal.modele import ModeleFactice                  # noqa: E402


async def demonstration() -> None:
    print("1. UN COORDINATEUR ET DEUX EXPERTS\n")
    racine = coordinateur()
    print(f"   {racine.name}")
    for enfant in racine.sub_agents:
        print(f"     {enfant.name:<20}{enfant.description}")

    print("\n2. LA QUESTION DECIDE DU DESTINATAIRE\n")
    for question in ("Quel salaire pour DevOps ?", "Quelles offres DevOps ?"):
        trace = await lancer(coordinateur(), question)
        chemin = []
        for auteur in trace.auteurs:
            if not chemin or chemin[-1] != auteur:
                chemin.append(auteur)
        print(f"   {question:<30}{' → '.join(chemin)}")
        print(f"   {'':<30}{trace.final[:58]}")

    print("\n3. C'EST LA DESCRIPTION QUI DECIDE, PAS L'INSTRUCTION\n")
    print("   ADK liste les sous-agents dans l'instruction du coordinateur,")
    print("   avec leur `description` — jamais leur `instruction`. Un expert")
    print("   sans description est invisible au routage, et la delegation se")
    print("   fait au hasard sans qu'aucune erreur ne le dise.")

    muet = Agent(name="expert_muet", model=modele(None, "muet"),
                 tools=[salaire_du_marche])
    print(f"\n   description d'un agent qui n'en declare pas : {muet.description!r}")

    print("\n4. transfer_to_agent EST UN OUTIL, ET IL VA DANS LES DEUX SENS\n")
    modele_espion = ModeleFactice("coordinateur")
    await lancer(coordinateur(modele_espion), "Quelles offres DevOps ?")
    print(f"   outils appeles par le coordinateur : {modele_espion.appels}")
    print("\n   ADK ajoute `transfer_to_agent` des qu'un agent a des")
    print("   `sub_agents` — et il le donne AUSSI aux sous-agents, pour qu'ils")
    print("   puissent rendre la main. Un modele qui le choisit")
    print("   systematiquement fait rebondir la question jusqu'a epuisement de")
    print("   la pile : l'erreur qui sort alors est un « RecursionError » dans")
    print("   un deepcopy Pydantic, qui ne parle ni d'agents ni de delegation.")

    print("\n5. CE QUE LA DELEGATION COUTE\n")
    seul = ModeleFactice("assistant")
    from jobportal.agents import assistant
    await lancer(assistant(seul), "Quelles offres DevOps ?")
    coord = ModeleFactice("coordinateur")
    await lancer(coordinateur(coord), "Quelles offres DevOps ?")
    print(f"   un agent outille       {seul.tours} appel(s)")
    print(f"   coordinateur + expert  {coord.tours} appel(s)")
    print("\n   Le coordinateur reflechit AVANT de deleguer : c'est un appel")
    print("   de plus, sur un contexte complet, pour produire un seul nom.")
    print("   On y vient quand les competences sont vraiment distinctes.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
