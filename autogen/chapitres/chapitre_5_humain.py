"""Chapitre 5 — L'humain est un MEMBRE, et l'etat se sauvegarde.

    uv run python chapitres/chapitre_5_humain.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_agentchat.conditions import MaxMessageTermination   # noqa: E402
from autogen_agentchat.teams import RoundRobinGroupChat          # noqa: E402

from jobportal import console                                    # noqa: E402
from jobportal.equipes import chercheur, equipe_avec_humain, redacteur  # noqa: E402
from jobportal.modele import ClientFactice                       # noqa: E402


async def demonstration() -> None:
    print("1. L'HUMAIN EST UN AGENT COMME LES AUTRES\n")
    resultat = await equipe_avec_humain(["Plutot a Lyon", "Ca me va"]).run(
        task="Je cherche un poste DevOps")
    for message in resultat.messages:
        source = getattr(message, "source", "?")
        print(f"   {source:<12}{str(message.content)[:62]}")
    print(f"\n   arret : {resultat.stop_reason}")

    print("\n2. input_func EST LE POINT D'EXTENSION\n")
    print("   UserProxyAgent(\"humain\", input_func=input)          en console")
    print("   UserProxyAgent(\"humain\", input_func=demander_web)   cote serveur")
    print("   UserProxyAgent(\"humain\", input_func=reponses.pop)   en test")
    print("\n   C'est ce qui rend le human-in-the-loop TESTABLE. Un agent")
    print("   humain branche en dur sur `input()` ne s'execute que devant un")
    print("   clavier — donc jamais en CI, donc jamais verifie.")

    print("\n3. SAUVEGARDER, PUIS REPRENDRE\n")
    equipe = RoundRobinGroupChat(
        [chercheur(), redacteur()],
        termination_condition=MaxMessageTermination(4))
    premier = await equipe.run(task="Le marche DevOps a Lyon")
    etat = await equipe.save_state()
    print(f"   premiere session  : {len(premier.messages)} messages")
    print(f"   etat sauvegarde   : {len(str(etat))} signes")

    reprise = RoundRobinGroupChat(
        [chercheur(), redacteur()],
        termination_condition=MaxMessageTermination(8))
    await reprise.load_state(etat)
    second = await reprise.run(task="Et les salaires ?")
    print(f"   apres load_state  : {len(second.messages)} messages")
    print(f"   l'equipe reprend ou elle s'etait arretee, dans un autre objet.")

    print("\n4. CE QUE L'ETAT CONTIENT — ET CE QU'IL NE CONTIENT PAS\n")
    print(f"   cles : {list(etat)[:4]}")
    print("\n   Il contient l'historique des messages. Il ne contient NI les")
    print("   clients de modele, NI les outils : ce sont des objets vivants,")
    print("   reconstruits a la reprise. Une equipe rechargee avec des agents")
    print("   differents accepte l'etat sans broncher — et se comporte")
    print("   autrement, sans rien signaler.")

    print("\n5. QUAND DEMANDER A L'HUMAIN\n")
    for quand, pourquoi in (
            ("avant une action irreversible", "un envoi ne se rattrape pas"),
            ("quand l'agent hesite", "un choix arbitraire coute plus qu'une question"),
            ("jamais « pour valider »", "une validation systematique n'est plus lue")):
        print(f"   {quand:<34}{pourquoi}")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
