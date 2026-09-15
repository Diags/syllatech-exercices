"""Chapitre 1 — Role, goal, backstory : trois champs qui decident de tout.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.equipe import chercheur, equipe_simple, redacteur  # noqa: E402
from jobportal.modele import ModeleFactice                      # noqa: E402


def main() -> None:
    console.utf8()

    print("1. UN AGENT, UNE TACHE, UN EQUIPAGE\n")
    m = ModeleFactice()
    resultat = equipe_simple(m).kickoff(inputs={"sujet": "DevOps"})
    print(f"   {str(resultat)[:96]}")

    print("\n2. LES TROIS CHAMPS NE SONT PAS DES ETIQUETTES\n")
    for agent in (chercheur(m), redacteur(m)):
        print(f"   role      {agent.role}")
        print(f"   goal      {agent.goal}")
        print(f"   backstory {agent.backstory}\n")
    print("   Ils composent le prompt systeme. Deux agents avec les memes")
    print("   trois champs sont deux fois le meme agent — et une equipe de")
    print("   clones coute trois fois plus cher qu'un agent seul pour le")
    print("   meme resultat.")

    print("\n3. CE QUE RENDS UN kickoff()\n")
    for champ in ("raw", "pydantic", "json_dict", "tasks_output", "token_usage"):
        valeur = getattr(resultat, champ, None)
        apercu = (f"{len(valeur)} element(s)" if isinstance(valeur, list)
                  else str(valeur)[:56])
        print(f"   {champ:<16}{apercu}")

    print("\n4. LE MODELE EST UN PARAMETRE\n")
    print("   Agent(..., llm=ModeleFactice())   sans cle, deterministe")
    print("   Agent(..., llm='claude-sonnet-5') le vrai modele")
    print("\n   ⚠️ CrewAI 1.x n'embarque plus LiteLLM : le coeur ne connait")
    print("   qu'une liste fermee de fournisseurs (openai, anthropic, google,")
    print("   bedrock, ollama…). Tout le reste demande « crewai[litellm] », et")
    print("   l'erreur parle d'installation la ou l'on cherchait autre chose.")


if __name__ == "__main__":
    main()
