"""Chapitre 2 — Les outils, et ce que reflect_on_tool_use coute.

    uv run python chapitres/chapitre_2_outils.py
"""
from __future__ import annotations
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_agentchat.agents import AssistantAgent           # noqa: E402

from jobportal import console                                 # noqa: E402
from jobportal.donnees import rechercher_offres, salaire_du_marche  # noqa: E402
from jobportal.modele import ClientFactice                    # noqa: E402


def agent(client, reflet: bool) -> AssistantAgent:
    return AssistantAgent("assistant", model_client=client,
                          tools=[rechercher_offres, salaire_du_marche],
                          reflect_on_tool_use=reflet,
                          system_message="Tu es l'assistant du portail. Cite les offres.")


async def demonstration() -> None:
    print("1. UN OUTIL EST UNE FONCTION ANNOTEE\n")
    print(f"   nom        {rechercher_offres.__name__}")
    print(f"   docstring  {rechercher_offres.__doc__}")
    print(f"   signature  {list(rechercher_offres.__annotations__)}")
    print("\n   La docstring devient la description envoyee au modele, les")
    print("   annotations deviennent le schema des arguments. Une fonction")
    print("   sans annotation produit un outil dont le modele ne sait pas quoi")
    print("   passer — et il passera quelque chose quand meme.")

    print("\n2. L'AGENT SE SERT-IL DU RETOUR ?\n")
    client = ClientFactice("assistant")
    resultat = await agent(client, True).run(task="Quelles offres DevOps a Lyon ?")
    reelles = json.loads(await rechercher_offres("DevOps", "Lyon"))
    cite = any(o.split(" — ")[0] in str(resultat.messages[-1].content) for o in reelles)
    print(f"   outil appele : {client.appels}")
    print(f"   arguments extraits de la question : mot_cle + ville")
    print(f"   cite une offre reelle : {'oui' if cite else 'non'}")
    print(f"   {str(resultat.messages[-1].content)[:96]}")

    print("\n3. CE QUE reflect_on_tool_use CHANGE\n")
    for reflet in (False, True):
        client = ClientFactice("assistant")
        resultat = await agent(client, reflet).run(task="Quelles offres DevOps ?")
        dernier = str(resultat.messages[-1].content)[:58]
        print(f"   reflect={str(reflet):<6}{client.tours} appel(s)   {len(resultat.messages)} messages")
        print(f"                 dernier : {dernier}")
    print("\n   A False, le retour brut de l'outil EST la reponse. A True,")
    print("   l'agent le reformule — un aller-retour de plus, donc des tokens")
    print("   de plus. Plus lisible pour un humain, inutile pour du code qui")
    print("   consomme du JSON.")

    print("\n4. L'OUTIL CHOISI DEPEND DE LA QUESTION\n")
    for question in ("Quelles offres Python ?", "Quel salaire pour Python ?"):
        client = ClientFactice("assistant")
        await agent(client, False).run(task=question)
        print(f"   {question:<32}{client.appels}")
    print("\n   Donner vingt outils a un agent dilue son choix autant que ca")
    print("   elargit la surface. Le moindre privilege vaut pour les agents")
    print("   comme pour le reste.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
