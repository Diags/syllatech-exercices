"""Chapitre 2 — Dependances injectees et outils typés.

    uv run python chapitres/chapitre_2_deps.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic_ai.models.test import TestModel                   # noqa: E402

from jobportal import console                                   # noqa: E402
from jobportal.agents import Deps, agent_offres, agent_strict    # noqa: E402
from jobportal.donnees import DatabaseConn                       # noqa: E402
from jobportal.modele import modele_conseiller                   # noqa: E402


def main() -> None:
    console.utf8()
    deps = Deps(candidat_id=3, db=DatabaseConn())

    print("1. LES DEPS SONT INJECTEES, PAS GLOBALES\n")
    agent = agent_offres(modele_conseiller())
    resultat = agent.run_sync("Quelles sont mes offres ?", deps=deps)
    print(f"   candidat {deps.candidat_id} → {resultat.output.resume}")

    autre = Deps(candidat_id=7, db=DatabaseConn())
    resultat2 = agent.run_sync("Quelles sont mes offres ?", deps=autre)
    print(f"   candidat {autre.candidat_id} → {resultat2.output.resume}")
    print("\n   MEME agent, deux resultats. L'outil ne « connait » pas la base :")
    print("   il la recoit. On peut donc en passer une autre en test, une par")
    print("   client, une par requete — sans toucher au code de l'agent.")

    print("\n2. CE QUE LE MODELE VOIT DE L'OUTIL\n")
    espion = TestModel()
    agent_offres(espion).run_sync("Mes offres ?", deps=deps)
    for outil in espion.last_model_request_parameters.function_tools:
        print(f"   nom         {outil.name}")
        print(f"   description {outil.description}")
        print(f"   arguments   {outil.parameters_json_schema.get('properties')}")
    print("\n   La docstring devient la description ; les ANNOTATIONS de type")
    print("   deviennent le schema des arguments. Retirez l'annotation de")
    print("   « seulement_actives » et le modele ne saura plus quoi passer —")
    print("   il passera quelque chose quand meme.")

    print("\n3. DEUX NIVEAUX DE VALIDATION\n")
    print("   Pydantic valide la FORME : un entier est un entier.")
    print("   Un validateur de sortie valide le SENS : l'offre citee existe-t-elle ?")
    print("\n   Un modele qui invente une offre plausible produit une sortie")
    print("   parfaitement valide au sens du schema. C'est la que le schema")
    print("   s'arrete, et que le validateur commence.\n")

    strict = agent_strict(modele_conseiller())
    resultat = strict.run_sync("Mes offres ?", deps=deps)
    reelles = set(resultat.output.offres_citees)
    print(f"   {len(reelles)} offre(s) citee(s), toutes verifiees dans la base.")

    print("\n4. CE QUI SE PASSE QUAND LE MODELE INVENTE\n")

    def menteur(messages, info):
        from pydantic_ai.messages import ModelResponse, ToolCallPart
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {
            "resume": "voici", "offres_citees": ["Astronaute — Mars, 900k"],
            "confiance": 9})])

    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai import UnexpectedModelBehavior
    try:
        agent_strict(FunctionModel(menteur)).run_sync("Mes offres ?", deps=deps)
        print("   (le modele s'est corrige)")
    except UnexpectedModelBehavior as e:
        print(f"   {type(e).__name__} apres epuisement des reprises.")
        print(f"   « {str(e)[:70]}… »")
    print("\n   Le validateur a leve ModelRetry, PydanticAI a renvoye le")
    print("   message AU MODELE, qui a re-invente la meme chose. Au bout des")
    print("   reprises, l'erreur remonte a l'appelant : elle n'est pas")
    print("   silencieuse. Une offre inventee ne sort JAMAIS de l'agent.")


if __name__ == "__main__":
    main()
