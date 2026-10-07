"""Chapitre 4 — Les agents de workflow : l'ordre sans appel de modele.

    uv run python chapitres/chapitre_4_workflow.py
"""
from __future__ import annotations
import asyncio
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk import Agent                                # noqa: E402
from google.adk.agents import SequentialAgent               # noqa: E402

from jobportal import console                               # noqa: E402
from jobportal.agents import boucle, coordinateur, eventail, modele, pipeline  # noqa: E402
from jobportal.harnais import lancer                        # noqa: E402
from jobportal.modele import ModeleFactice                  # noqa: E402


async def demonstration() -> None:
    print("1. LE PIPELINE — deux agents relies par l'ETAT\n")
    trace = await lancer(pipeline(), "Les offres DevOps")
    for cle, valeur in trace.etat.items():
        print(f"   etat[{cle!r}] = {str(valeur)[:66]}")
    print(f"\n   final : {trace.final[:80]}")
    print("\n   `output_key=\"analyse\"` ecrit dans l'etat ; le `{analyse}` de")
    print("   l'instruction du redacteur est substitue par ADK AVANT l'appel.")
    print("   Le lien n'est pas un passage d'argument : c'est une variable de")
    print("   session, et elle survit a l'agent qui l'a ecrite.")

    print("\n2. UNE CLE MAL ORTHOGRAPHIEE — ce qu'ADK en fait\n")
    casse = SequentialAgent(name="casse", sub_agents=[
        Agent(name="a", model=modele(None, "a"), instruction="Analyse.",
              output_key="analyse"),
        Agent(name="b", model=modele(None, "b"),
              instruction="Redige a partir de {analyze}."),   # faute de frappe
    ])
    try:
        await lancer(casse, "Les offres DevOps")
        print("   (aucune erreur — ce n'est pas ce qui se produit ici)")
    except KeyError as souci:
        print(f"   KeyError: {souci}")
    print("\n   ADK REFUSE, et c'est une bonne nouvelle : beaucoup de")
    print("   frameworks laissent le litteral tel quel, et l'agent travaille")
    print("   alors sur le mot « {analyze} » sans que rien ne le dise.")
    print("\n   Le defaut restant est que l'erreur arrive A L'EXECUTION, pas")
    print("   a la construction du pipeline. Une branche rarement empruntee")
    print("   peut donc porter une faute de frappe pendant des mois. Un test")
    print("   qui traverse chaque chemin la trouve ; la relecture, non.")

    print("\n3. L'EVENTAIL — deux agents en meme temps, deux cles\n")
    trace = await lancer(eventail(), "Les offres DevOps")
    for cle, valeur in trace.etat.items():
        print(f"   etat[{cle!r}] = {str(valeur)[:58]}")
    print("\n   Chacun ecrit SA cle. Deux agents qui ecriraient la meme se")
    print("   marcheraient dessus — sans erreur, et le dernier gagnerait.")

    print("\n4. LA BOUCLE — et sa borne\n")
    for tours in (1, 3):
        modele_boucle = ModeleFactice("affineur")
        await lancer(boucle(modele_boucle, tours), "Ameliore la synthese")
        print(f"   max_iterations={tours}   {modele_boucle.tours} appel(s) au modele")
    print("\n   `max_iterations` n'est pas une precaution : sans elle, un")
    print("   LoopAgent tourne jusqu'a ce qu'un sous-agent leve une escalade.")
    print("   Un agent qui reformule au lieu de conclure ne la leve jamais.")

    print("\n5. WORKFLOW OU DELEGATION ?\n")
    sequentiel = ModeleFactice("pipeline")
    await lancer(pipeline(sequentiel), "Les offres DevOps")
    delegue = ModeleFactice("coordinateur")
    await lancer(coordinateur(delegue), "Quelles offres DevOps ?")
    print(f"   SequentialAgent (2 agents)   {sequentiel.tours} appel(s)")
    print(f"   coordinateur + 1 expert      {delegue.tours} appel(s)")
    print("\n   A ce format, les deux content PAREIL — et le dire est plus")
    print("   utile que d'annoncer un gain qui n'existe pas ici.")

    print("\n   Ou l'ecart apparait : a chaque MAILLON de plus.\n")
    for n in (2, 3, 4):
        etapes = ModeleFactice("chaine")
        chaine = SequentialAgent(name=f"chaine{n}", sub_agents=[
            Agent(name=f"e{i}", model=etapes, instruction=f"Etape {i}.",
                  output_key=f"e{i}") for i in range(n)])
        await lancer(chaine, "Les offres DevOps")
        print(f"     {n} etapes en workflow     {etapes.tours} appel(s)")
    print("\n   Un workflow paie UN appel par etape : l'ordre est ecrit en")
    print("   Python, personne ne decide. Un coordinateur en paie un de plus")
    print("   a chaque passage de main, pour choisir a qui.")
    print("\n   Mais la vraie raison de preferer un workflow n'est pas le")
    print("   cout : c'est qu'un ordre ecrit en Python se teste, se relit, et")
    print("   ne varie pas d'une execution a l'autre.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
