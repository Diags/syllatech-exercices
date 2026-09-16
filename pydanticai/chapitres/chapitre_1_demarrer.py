"""Chapitre 1 — La sortie est un modele Pydantic, donc elle est VALIDEE.

    uv run python chapitres/chapitre_1_demarrer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError                       # noqa: E402

from jobportal import console                              # noqa: E402
from jobportal.agents import Analyse, agent_conseil        # noqa: E402
from jobportal.modele import en_factice                    # noqa: E402


def main() -> None:
    console.utf8()

    print("1. UN AGENT, UNE SORTIE TYPEE\n")
    resultat = agent_conseil().run_sync("Dois-je accepter cette offre a 45k ?")
    print(f"   type   {type(resultat.output).__name__}")
    print(f"   sortie {resultat.output}")
    print(f"   usage  {resultat.usage}")
    if en_factice():
        print("\n   (modele factice : la sortie est plausible mais vide de sens.")
        print("    Ce qui compte ici est qu'elle soit du BON TYPE.)")

    print("\n2. CE QUE « VALIDEE » VEUT DIRE\n")
    for essai in ({"conseil": "Accepte", "risque": 3},
                  {"conseil": "Accepte", "risque": 42},
                  {"conseil": "", "risque": 3}):
        try:
            Analyse(**essai)
            print(f"   {str(essai):<44} accepte")
        except ValidationError as e:
            souci = e.errors()[0]
            print(f"   {str(essai):<44} REFUSE — {souci['loc'][0]} : {souci['msg']}")

    print("\n   Ces contraintes ne sont pas de la documentation : elles")
    print("   s'executent. Un risque a 42 n'est pas « une reponse un peu")
    print("   bizarre » — c'est une ValidationError, et PydanticAI renvoie")
    print("   l'erreur AU MODELE pour qu'il se corrige. Vous n'ecrivez pas")
    print("   ce controle, et vous ne l'oubliez donc jamais.")

    print("\n3. LE SCHEMA QUE LE MODELE RECOIT\n")
    schema = Analyse.model_json_schema()
    for nom, champ in schema["properties"].items():
        contraintes = {k: v for k, v in champ.items()
                       if k in ("minimum", "maximum", "minLength", "description")}
        print(f"   {nom:<10}{champ.get('type', '?'):<10}{contraintes}")
    print("\n   Il est deduit de la classe. Les bornes ge/le deviennent")
    print("   minimum/maximum, la description devient un indice pour le")
    print("   modele. Une classe bien ecrite est donc un meilleur prompt.")

    print("\n4. LE MODELE EST UN PARAMETRE, PAS UNE CONSTANTE\n")
    print("   agent_conseil()              -> factice, sans cle")
    print("   agent_conseil(TestModel())   -> factice, impose")
    print("   ANTHROPIC_API_KEY posee      -> anthropic:claude-sonnet-5")
    print("\n   C'est ce qui rend ce projet executable chez vous sans rien")
    print("   payer, et ce qui rend ses tests possibles. Un modele ecrit en")
    print("   dur dans le code d'un agent rend l'agent intestable.")


if __name__ == "__main__":
    main()
