"""Chapitre 1 — AutoGen est asynchrone de bout en bout.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_agentchat.agents import AssistantAgent       # noqa: E402

from jobportal import console                             # noqa: E402
from jobportal.equipes import assistant                   # noqa: E402
from jobportal.modele import ClientFactice                # noqa: E402


async def demonstration() -> None:
    print("1. UN AGENT, UNE TACHE\n")
    client = ClientFactice("assistant")
    agent = AssistantAgent("assistant", model_client=client,
                           system_message="Tu es l'assistant du portail syllatech.")
    resultat = await agent.run(task="Dis bonjour a syllatech")
    for message in resultat.messages:
        print(f"   {type(message).__name__:<22}{str(message.content)[:64]}")

    print("\n2. TOUT EST ASYNCHRONE, ET CE N'EST PAS UN DETAIL\n")
    print("   agent.run(...)          coroutine")
    print("   agent.run_stream(...)   generateur asynchrone")
    print("   client.create(...)      coroutine")
    print("\n   Un `await` oublie ne leve pas d'erreur : il rend un objet")
    print("   coroutine, que l'on affiche, et l'on croit avoir une reponse.")
    print("   C'est le premier piege d'AutoGen, et il est silencieux.")

    print("\n3. LE CLIENT DE MODELE EST UN PARAMETRE\n")
    print("   AssistantAgent(..., model_client=ClientFactice())   sans cle")
    print("   AssistantAgent(..., model_client=OpenAIChatCompletionClient(...))")
    print("\n   ⚠️ `OpenAIChatCompletionClient` vient d'`autogen_ext`, UN PAQUET")
    print("   SEPARE : « pip install autogen-agentchat » ne le tire pas.")
    print("   Le cours le dit et l'installe ; ce projet ne l'installe")
    print("   PAS, parce qu'il demande une cle d'API.")
    print("\n   `ChatCompletionClient` est l'interface commune : huit membres")
    print("   abstraits. jobportal/modele.py en ecrit un, et c'est ce qui rend")
    print("   ce projet executable chez vous.")

    print("\n4. CE QUE COMPTE LE CLIENT\n")
    print(f"   tours             {client.tours}")
    print(f"   usage             {client.total_usage()}")
    print("\n   `total_usage()` fait partie de l'interface : AutoGen le")
    print("   consulte. Un client qui rend zero partout n'est pas faux — il")
    print("   ne facture rien — mais il ne mesure rien non plus.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
