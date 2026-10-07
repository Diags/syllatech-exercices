"""Chapitre 3 — Instructions dynamiques et historique de conversation.

    uv run python chapitres/chapitre_3_messages.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic_ai.models.test import TestModel                   # noqa: E402

from jobportal import console                                   # noqa: E402
from jobportal.agents import Deps, agent_offres, agent_personnalise  # noqa: E402
from jobportal.donnees import DatabaseConn                       # noqa: E402
from jobportal.modele import modele_conseiller                   # noqa: E402


def instructions_envoyees(resultat) -> str:
    """Les instructions REELLEMENT envoyees, lues dans le message.

    Elles ne sont pas dans `last_model_request_parameters` : elles voyagent
    sur le `ModelRequest` lui-meme, champ `instructions`. Les chercher au
    mauvais endroit rend « (aucune) » et laisse croire que le decorateur ne
    marche pas — alors qu'il marche.
    """
    for message in resultat.all_messages():
        rendu = getattr(message, "instructions", None)
        if rendu:
            return " | ".join(l for l in rendu.splitlines() if l.strip())
    return "(aucune)"


def main() -> None:
    console.utf8()
    deps = Deps(candidat_id=5, db=DatabaseConn())

    print("1. INSTRUCTIONS STATIQUES vs DYNAMIQUES\n")
    sans = agent_offres(TestModel()).run_sync("Bonjour", deps=deps)
    print(f"   sans decorateur : {instructions_envoyees(sans)}")

    avec_deco = agent_personnalise(TestModel()).run_sync("Bonjour", deps=deps)
    print(f"   avec decorateur : {instructions_envoyees(avec_deco)!r}")
    print("\n   Le nom du candidat vient de la BASE, lu a l'execution. Une")
    print("   instruction passee en parametre serait figee a la construction")
    print("   de l'agent ; celle-ci est reevaluee a chaque run.")

    print("\n2. LA PREUVE : DEUX CANDIDATS, DEUX INSTRUCTIONS\n")
    for candidat in (5, 12):
        r = agent_personnalise(TestModel()).run_sync(
            "Bonjour", deps=Deps(candidat_id=candidat, db=DatabaseConn()))
        print(f"   candidat {candidat:<4}{instructions_envoyees(r)!r}")

    print("\n3. L'HISTORIQUE NE SE TRANSPORTE PAS TOUT SEUL\n")
    agent = agent_offres(modele_conseiller())
    r1 = agent.run_sync("Quelles sont mes offres ?", deps=deps)
    print(f"   tour 1 : {len(r1.all_messages())} messages au total")

    sans = agent.run_sync("Et pour un poste DevOps ?", deps=deps)
    print(f"   tour 2 SANS historique : {len(sans.all_messages())} messages")
    print("     l'agent repart de zero — il ne sait rien du tour precedent")

    avec = agent.run_sync("Et pour un poste DevOps ?", deps=deps,
                          message_history=r1.new_messages())
    print(f"   tour 2 AVEC historique : {len(avec.all_messages())} messages")
    print("     l'agent voit la question ET la reponse du tour 1")

    print("\n   C'est un choix EXPLICITE, et c'est mieux ainsi : un agent qui")
    print("   accumulerait tout seul finirait par payer tres cher un contexte")
    print("   dont il n'a plus besoin. Vous decidez de ce qui suit.")

    print("\n4. all_messages() ET new_messages() NE DISENT PAS LA MEME CHOSE\n")
    print(f"   r1.all_messages()  {len(r1.all_messages())}  tout, historique d'entree compris")
    print(f"   r1.new_messages()  {len(r1.new_messages())}  seulement ce que CE run a produit")
    print(f"   avec.all_messages() {len(avec.all_messages())}  le run precedent + celui-ci")
    print("\n   Passer all_messages() au lieu de new_messages() sur une longue")
    print("   conversation duplique l'historique a chaque tour. La facture")
    print("   grandit en carre, et rien ne le signale avant la note.")

    print("\n5. CE QUE CONTIENT UN MESSAGE\n")
    for message in r1.all_messages():
        genres = [type(p).__name__ for p in message.parts]
        print(f"   {type(message).__name__:<16}{genres}")


if __name__ == "__main__":
    main()
