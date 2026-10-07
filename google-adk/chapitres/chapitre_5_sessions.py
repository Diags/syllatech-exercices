"""Chapitre 5 — Sessions, etat et memoire : trois choses distinctes.

    uv run python chapitres/chapitre_5_sessions.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk.memory import InMemoryMemoryService          # noqa: E402
from google.adk.runners import Runner                        # noqa: E402
from google.adk.sessions import InMemorySessionService       # noqa: E402
from google.genai import types                               # noqa: E402

from jobportal import console                                # noqa: E402
from jobportal.agents import assistant, pipeline             # noqa: E402
from jobportal.harnais import lancer                         # noqa: E402


async def dialogue(runner, utilisateur, session, question) -> str:
    message = types.Content(role="user", parts=[types.Part(text=question)])
    final = ""
    async for evenement in runner.run_async(user_id=utilisateur,
                                            session_id=session,
                                            new_message=message):
        if evenement.is_final_response() and evenement.content:
            final = evenement.content.parts[0].text or final
    return final


async def demonstration() -> None:
    print("1. LES TROIS OBJETS, ET CE QU'ILS PORTENT\n")
    print("   Session   un fil de conversation : ses evenements, son etat")
    print("   State     un dictionnaire, dans la session — output_key y ecrit")
    print("   Memory    ce qui survit AUX sessions, pour un utilisateur")
    print("\n   Les confondre coute : l'etat meurt avec la session, la memoire")
    print("   non. Un fait durable range dans l'etat disparait au prochain fil.")

    print("\n2. L'ETAT, ECRIT PAR output_key\n")
    trace = await lancer(pipeline(), "Les offres DevOps")
    for cle, valeur in trace.etat.items():
        print(f"   {cle:<12}{str(valeur)[:64]}")

    print("\n3. LA SESSION PORTE L'HISTORIQUE\n")
    service = InMemorySessionService()
    await service.create_session(app_name="jp", user_id="d", session_id="s1")
    runner = Runner(agent=assistant(), app_name="jp", session_service=service)

    for question in ("Quelles offres DevOps a Lyon ?", "Et a Paris ?"):
        reponse = await dialogue(runner, "d", "s1", question)
        session = await service.get_session(app_name="jp", user_id="d",
                                            session_id="s1")
        print(f"   {question:<32}{len(session.events)} evenements accumules")

    print("\n   Chaque tour s'ajoute. C'est ce qui permet au second de")
    print("   comprendre « et a Paris ? » — et c'est aussi ce qui fait grossir")
    print("   ce qu'on envoie au modele a chaque appel.")

    print("\n4. DEUX SESSIONS NE SE VOIENT PAS\n")
    await service.create_session(app_name="jp", user_id="d", session_id="s2")
    await dialogue(runner, "d", "s2", "Bonjour")
    s1 = await service.get_session(app_name="jp", user_id="d", session_id="s1")
    s2 = await service.get_session(app_name="jp", user_id="d", session_id="s2")
    print(f"   session s1 : {len(s1.events)} evenements")
    print(f"   session s2 : {len(s2.events)} evenements")
    print("\n   Meme utilisateur, meme agent, deux fils independants. C'est")
    print("   voulu — et c'est pourquoi la memoire existe.")

    print("\n5. LA MEMOIRE, ELLE, TRAVERSE LES SESSIONS\n")
    memoire = InMemoryMemoryService()
    await memoire.add_session_to_memory(s1)
    resultat = await memoire.search_memory(app_name="jp", user_id="d",
                                           query="DevOps")
    print(f"   apres add_session_to_memory + search_memory(\"DevOps\") :")
    print(f"   {len(resultat.memories)} souvenir(s) retrouve(s)")
    print("\n   Le service en memoire vive suffit a comprendre le mecanisme et")
    print("   perd tout au redemarrage. En production : VertexAiMemoryBankService,")
    print("   ou votre propre implementation de BaseMemoryService.")

    print("\n6. LE PIEGE QUI COUTE UNE HEURE\n")
    print("     session_service.create_session(...)        # sans await")
    print("\n   Rend une coroutine que personne n'attend. La session n'existe")
    print("   pas, `run_async` echoue plus loin, et le message ne parle pas de")
    print("   la session. C'est ce que le cours ecrit — ADK 1.x a rendu cette")
    print("   methode asynchrone.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
