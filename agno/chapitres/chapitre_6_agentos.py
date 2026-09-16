"""Chapitre 6 — AgentOS : ce qu'il faut savoir avant de deployer.

    uv run python chapitres/chapitre_6_agentos.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.agents import conseiller_avec_memoire, equipe  # noqa: E402
from jobportal.modele import ModeleFactice                 # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    console.utf8()

    print("1. AgentOS DEMANDE FastAPI, ET CE N'EST PAS DIT\n")
    try:
        from agno.os import AgentOS       # noqa: F401
        print("   AgentOS importe : FastAPI est installe.")
    except ModuleNotFoundError as e:
        print(f"   ModuleNotFoundError: {e}")
        print("\n   Agno 3.x est modulaire : le coeur n'embarque ni FastAPI, ni")
        print("   SQLAlchemy, ni lancedb, ni les clients de fournisseurs. Chaque")
        print("   chapitre du cours ajoute donc une dependance que la video ne")
        print("   mentionne pas :")
        print("     Claude(...)                → pip install anthropic")
        print("     SqliteDb(db_file=...)      → SQLAlchemy")
        print("     LanceDb(...)               → lancedb, plus un embedder")
        print("     AgentOS(...)               → fastapi")
        print("\n   Ce n'est pas un defaut d'Agno : c'est un choix d'installation")
        print("   legere. Mais un projet qui suit le cours de bout en bout")
        print("   echoue quatre fois, chaque fois sur une erreur d'import qui")
        print("   ne dit rien du chapitre en cours.")

    print("\n2. LA FORME, ELLE, TIENT EN QUATRE LIGNES\n")
    print("     from agno.os import AgentOS")
    print("     agent_os = AgentOS(agents=[conseiller], teams=[equipe])")
    print("     app = agent_os.get_app()      # une application FastAPI")
    print("     # $ fastapi run serve.py")
    print("\n   AgentOS n'est pas un service distant : c'est une application")
    print("   FastAPI que VOUS hebergez. Les agents, leurs sessions et leurs")
    print("   memoires restent chez vous — point qui decide souvent de")
    print("   l'adoption en entreprise.")

    print("\n3. CE QUI CHANGE ENTRE run() ET UNE API\n")
    points = [
        ("user_id", "obligatoire des qu'il y a des memoires — sinon elles fuient"),
        ("session_id", "c'est lui qui porte l'historique ; l'oublier le perd"),
        ("db", "InMemoryDb perd tout au redemarrage : en production, une vraie"),
        ("timeouts", "un agent a outils peut faire dix allers-retours"),
        ("cout", "a mesurer PAR requete utilisateur, pas par appel modele"),
    ]
    for nom, note in points:
        print(f"   {nom:<12}{note}")

    print("\n4. LES DEUX IDENTIFIANTS, EN PRATIQUE\n")
    from agno.db.in_memory import InMemoryDb
    base = InMemoryDb()
    agent = conseiller_avec_memoire(ModeleFactice(), base)
    for utilisateur, session, question in [
        ("alice", "s1", "Je cherche un poste DevOps"),
        ("bob", "s2", "Je cherche un poste Java"),
        ("alice", "s3", "Que sais-tu de moi ?"),
    ]:
        agent.run(question, user_id=utilisateur, session_id=session)
    for utilisateur in ("alice", "bob"):
        memoires = [m.memory for m in base.get_user_memories(user_id=utilisateur)]
        print(f"   {utilisateur:<8}{memoires}")
    print("\n   Deux utilisateurs, deux jeux de memoires, aucune fuite. C'est")
    print("   `user_id` qui cloisonne — pas la session, pas l'agent. L'oublier")
    print("   dans une API melange les profils de tous vos utilisateurs, et")
    print("   rien ne le signale avant qu'un client ne le voie.")

    print("\n5. LES VERSIONS\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   Borne des deux cotes. Agno 3.x a renomme des parametres d'Agent")
    print("   (enable_user_memories, chapitre 4) : une borne haute est la")
    print("   seule chose qui distingue « ca marchait hier » d'un projet")
    print("   qu'on peut donner a quelqu'un.")


if __name__ == "__main__":
    main()
