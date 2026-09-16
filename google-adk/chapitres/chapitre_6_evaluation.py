"""Chapitre 6 — Callbacks, evaluation et deploiement.

    uv run python chapitres/chapitre_6_evaluation.py
"""
from __future__ import annotations
import asyncio
import json
import sys
import tomllib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.adk import Agent                                 # noqa: E402
from google.adk.models import LlmResponse                    # noqa: E402
from google.genai import types                               # noqa: E402

from jobportal import console                                # noqa: E402
from jobportal.agents import modele                          # noqa: E402
from jobportal.donnees import rechercher_offres              # noqa: E402
from jobportal.harnais import lancer                         # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


async def demonstration() -> None:
    print("1. UN CALLBACK OBSERVE — ou COURT-CIRCUITE\n")
    vus: list[str] = []

    def avant_modele(callback_context, llm_request):
        vus.append(str(llm_request.contents[-1].parts[0].text or "")[:40])
        return None        # None = on laisse passer

    agent = Agent(name="observe", model=modele(None, "observe"),
                  instruction="Tu aides les candidats.",
                  tools=[rechercher_offres],
                  before_model_callback=avant_modele)
    trace = await lancer(agent, "Quelles offres DevOps a Lyon ?")
    print(f"   {len(vus)} appel(s) observe(s) : {vus}")
    print(f"   reponse : {trace.final[:60]}")

    print("\n2. RENDRE UNE LlmResponse COURT-CIRCUITE L'APPEL\n")

    def refuser(callback_context, llm_request):
        return LlmResponse(content=types.Content(
            role="model",
            parts=[types.Part(text="Question hors du perimetre du portail.")]))

    garde = Agent(name="garde", model=modele(None, "garde"),
                  instruction="Tu aides les candidats.",
                  before_model_callback=refuser)
    trace = await lancer(garde, "Donne-moi la recette du cassoulet")
    print(f"   {trace.final}")
    print("\n   Le modele n'a PAS ete appele : pas de tokens, pas de latence,")
    print("   pas de fuite. C'est le meilleur endroit pour un garde-fou —")
    print("   avant l'appel, pas apres la reponse.")

    print("\n3. LES QUATRE POINTS D'ACCROCHE\n")
    for nom, quand in (("before_agent_callback", "avant tout le cycle de l'agent"),
                       ("before_model_callback", "avant chaque appel au modele"),
                       ("before_tool_callback", "avant chaque appel d'outil"),
                       ("after_tool_callback", "apres, pour filtrer le retour")):
        print(f"   {nom:<24}{quand}")
    print("\n   `before_tool_callback` est celui qu'on oublie : c'est la que")
    print("   se refuse un appel d'outil dangereux, avec le contexte de")
    print("   l'utilisateur — pas dans le prompt.")

    print("\n4. L'EVALUATION — un jeu de cas versionne\n")
    exemple = {
        "eval_set_id": "cas_metier",
        "eval_cases": [{
            "eval_id": "offres_devops_lyon",
            "conversation": [{
                "user_content": {"parts": [{"text": "Quelles offres DevOps a Lyon ?"}]},
                "final_response": {"parts": [{"text": "Les offres DevOps a Lyon."}]},
            }],
        }],
    }
    print("   evals/cas_metier.evalset.json :")
    for ligne in json.dumps(exemple, indent=2, ensure_ascii=False).splitlines()[:9]:
        print(f"     {ligne}")
    print("\n     $ adk eval mon_agent evals/cas_metier.evalset.json")
    print("\n   Deux mesures : la TRAJECTOIRE (a-t-il appele les bons outils,")
    print("   dans le bon ordre ?) et la REPONSE. La premiere est celle qui")
    print("   attrape les regressions — une reponse peut rester correcte")
    print("   pendant qu'un outil a cesse d'etre appele.")

    print("\n5. LE DEPLOIEMENT\n")
    for commande, quoi in (
            ("adk web", "l'interface de test, en local"),
            ("adk run", "le dialogue en terminal"),
            ("adk api_server", "une API FastAPI, chez vous"),
            ("adk deploy cloud_run", "un conteneur sur Cloud Run"),
            ("adk deploy agent_engine", "Vertex Agent Engine, manage")):
        print(f"   {commande:<24}{quoi}")
    print("\n   Les deux dernieres supposent un projet Google Cloud. Les trois")
    print("   premieres tournent sans — c'est ce que ce projet utilise.")

    print("\n6. LES VERSIONS\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   Borne des deux cotes. ADK 1.x a rendu `create_session`")
    print("   asynchrone : le code du chapitre 5 ne cree plus de session sans")
    print("   `await`, et rien d'evident ne le dit.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
