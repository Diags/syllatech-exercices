"""Chapitre 1 — Un agent ADK, et les trois objets qu'il faut autour.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.sessions import InMemorySessionService     # noqa: E402

from jobportal import console                              # noqa: E402
from jobportal.agents import assistant                     # noqa: E402
from jobportal.harnais import lancer                       # noqa: E402
from jobportal.modele import ModeleFactice                 # noqa: E402


async def demonstration() -> None:
    print("1. UN AGENT NE SE LANCE PAS TOUT SEUL\n")
    print("   Agent            ce qu'il est : instruction, outils, modele")
    print("   SessionService   ou vit l'etat, entre deux tours")
    print("   Runner           ce qui fait tourner l'un avec l'autre")
    print("\n   Les trois sont obligatoires. `adk web` et `adk run` les")
    print("   fabriquent pour vous — ce qui donne l'illusion qu'un Agent seul")
    print("   suffit, jusqu'au jour ou l'on ecrit du code.")

    print("\n2. LE PIEGE DU CHAPITRE 5, ET IL EST ICI DES LE DEPART\n")
    print("     session_service.create_session(...)        # le cours")
    print("     await session_service.create_session(...)  # ADK 1.x\n")
    service = InMemorySessionService()
    coroutine = service.create_session(app_name="jp", user_id="d", session_id="s")
    print(f"   sans await : {type(coroutine).__name__}")
    await coroutine
    print("   La session n'est creee qu'apres l'attente. Sans `await`, Python")
    print("   emet au mieux un « coroutine was never awaited » dans un coin,")
    print("   et l'on cherche du cote du Runner.")

    print("\n3. UN AGENT, UNE QUESTION\n")
    modele = ModeleFactice("assistant")
    trace = await lancer(assistant(modele), "Quelles offres DevOps a Lyon ?")
    print(f"   {trace.final[:92]}")
    print(f"\n   {trace.evenements} evenements, {modele.tours} appel(s) au modele")
    print(f"   outil appele : {modele.appels}")

    print("\n4. LE MODELE EST UN PARAMETRE, PAS UNE CHAINE\n")
    print("   Agent(model=\"gemini-flash-latest\")   resout vers un client Google")
    print("   Agent(model=ModeleFactice())          court-circuite la resolution")
    print("\n   `BaseLlm` n'a QU'UNE methode abstraite : generate_content_async,")
    print("   un generateur asynchrone de LlmResponse. C'est ce qui rend ce")
    print("   projet executable sans cle — et vos tests possibles.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
