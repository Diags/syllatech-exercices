"""Chapitre 2 — Les outils : la docstring EST le contrat.

    uv run python chapitres/chapitre_2_outils.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.agents import assistant                          # noqa: E402
from jobportal.donnees import query, rechercher_offres, salaire_du_marche  # noqa: E402
from jobportal.harnais import lancer                            # noqa: E402
from jobportal.modele import ModeleFactice                      # noqa: E402


async def demonstration() -> None:
    print("1. UN OUTIL EST UNE FONCTION ANNOTEE\n")
    print(f"   nom        {rechercher_offres.__name__}")
    print(f"   signature  {rechercher_offres.__annotations__}")
    print("\n   docstring :")
    for ligne in (rechercher_offres.__doc__ or "").strip().splitlines():
        print(f"     {ligne}")
    print("\n   ADK lit TOUT cela : le nom, les annotations, et la docstring")
    print("   au format Google. Les « Args: » deviennent la description de")
    print("   chaque parametre. Une docstring vague produit un outil que le")
    print("   modele appelle mal — et aucune erreur ne le signale.")

    print("\n2. LE « Returns: dict » N'EST PAS UNE CONVENTION DE STYLE\n")
    print(f"   succes : {rechercher_offres('DevOps', 'Lyon')['status']}")
    print(f"   echec  : {rechercher_offres('COBOL', 'Lyon')}")
    print("\n   ADK serialise le retour tel quel vers le modele. Un dict nomme")
    print("   se relit — « status », « offres », « message ». Une chaine se")
    print("   devine, et le modele devine mal.")
    print("\n   Le champ « status » est la convention d'ADK : c'est ce qui")
    print("   permet au modele de distinguer « rien trouve » d'une panne.")

    print("\n3. L'AGENT SE SERT-IL DU RETOUR ?\n")
    modele = ModeleFactice("assistant")
    trace = await lancer(assistant(modele), "Quelles offres DevOps a Lyon ?")
    reelles = rechercher_offres("DevOps", "Lyon")["offres"]
    cite = any(o.split(" — ")[0] in trace.final for o in reelles)
    print(f"   outil appele : {modele.appels}")
    print(f"   cite une offre reelle : {'oui' if cite else 'non'}")
    print(f"   {trace.final[:92]}")

    print("\n4. L'OUTIL CHOISI DEPEND DE LA QUESTION\n")
    for question in ("Quelles offres Python ?", "Quel salaire pour Python ?"):
        modele = ModeleFactice("assistant")
        await lancer(assistant(modele), question)
        print(f"   {question:<32}{modele.appels}")

    print("\n5. LES OUTILS INTEGRES, ET LEUR LIMITE\n")
    print("   from google.adk.tools import google_search")
    print("\n   `google_search` est un outil INTEGRE : il tourne cote Google,")
    print("   avec le modele Gemini. Il ne se combine pas librement avec des")
    print("   fonctions maison sur tous les modeles — c'est une contrainte de")
    print("   plateforme, pas une contrainte d'ADK, et elle ne se voit qu'a")
    print("   l'execution.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
