"""Chapitre 6 — Core : quand AgentChat ne suffit plus.

    uv run python chapitres/chapitre_6_core.py
"""
from __future__ import annotations
import asyncio
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_core import (AgentId, MessageContext, RoutedAgent,      # noqa: E402
                          SingleThreadedAgentRuntime, message_handler)

from jobportal import console                                       # noqa: E402
from jobportal.donnees import query                                 # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


@dataclass
class Tache:
    mot_cle: str


@dataclass
class Resultat:
    mot_cle: str
    combien: int


class Compteur(RoutedAgent):
    """Un agent Core : pas de modele, pas de prompt — un gestionnaire de message.

    C'est toute la difference avec AgentChat. Ici, rien ne « discute » : on
    route des messages types vers des gestionnaires. Le modele n'apparait que
    si l'on decide d'en appeler un.
    """

    def __init__(self) -> None:
        super().__init__("Compte les offres")
        self.recus: list[str] = []

    @message_handler
    async def sur_tache(self, message: Tache, ctx: MessageContext) -> Resultat:
        self.recus.append(message.mot_cle)
        offres = await query(message.mot_cle)
        return Resultat(message.mot_cle, len(offres))


async def demonstration() -> None:
    print("1. UN AGENT CORE EST UN ROUTEUR DE MESSAGES\n")
    runtime = SingleThreadedAgentRuntime()
    await Compteur.register(runtime, "compteur", lambda: Compteur())
    runtime.start()

    for mot in ("DevOps", "Python", "COBOL"):
        resultat = await runtime.send_message(Tache(mot), AgentId("compteur", "defaut"))
        print(f"   {mot:<10}{resultat.combien} offre(s)")
    await runtime.stop()

    print("\n   Aucun modele appele. Aucun prompt. Un message type, un")
    print("   gestionnaire, une reponse typee — c'est de l'acteur, pas du")
    print("   dialogue.")

    print("\n2. AGENTCHAT SUFFIT A LA PLUPART DES CAS\n")
    for cas, reponse in (
            ("une equipe qui discute", "AgentChat"),
            ("un human-in-the-loop", "AgentChat"),
            ("des milliers de messages/s", "Core"),
            ("plusieurs processus ou machines", "Core (gRPC)"),
            ("du publish/subscribe par sujet", "Core")):
        print(f"   {cas:<34}{reponse}")
    print("\n   Core n'est pas « AgentChat en mieux » : c'est une couche plus")
    print("   basse. On y descend quand la CONVERSATION n'est plus le bon")
    print("   modele — pas quand on veut plus de performance.")

    print("\n3. LE RUNTIME DISTRIBUE\n")
    print("   SingleThreadedAgentRuntime   un processus, ordonnance")
    print("   GrpcWorkerAgentRuntime       plusieurs processus ou machines")
    print("\n   Le code des agents ne change pas : seul le runtime change.")
    print("   C'est la promesse d'AutoGen Core, et elle tient — au prix d'un")
    print("   modele de programmation nettement moins direct.")

    print("\n4. LES PAQUETS ET LEURS VERSIONS\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   ⚠️ Trois paquets, pas un : autogen-core (le socle),")
    print("   autogen-agentchat (les equipes) et autogen-ext (les clients de")
    print("   modele, les outils tiers). Le cours importe le troisieme sans le")
    print("   citer — c'est la premiere erreur d'installation.")
    print("\n   AutoGen Studio est un quatrieme paquet encore, pour prototyper")
    print("   des equipes sans code. Ce qu'il produit est du JSON que ces")
    print("   memes classes relisent.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
