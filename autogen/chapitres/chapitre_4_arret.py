"""Chapitre 4 — Conditions d'arret : le mot seul ne suffit jamais.

    uv run python chapitres/chapitre_4_arret.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from autogen_agentchat.conditions import (MaxMessageTermination,     # noqa: E402
                                          TextMentionTermination)
from autogen_agentchat.teams import RoundRobinGroupChat              # noqa: E402

from jobportal import console                                        # noqa: E402
from jobportal.equipes import chercheur, equipe_sans_arret, redacteur  # noqa: E402
from jobportal.modele import MOT_DE_FIN, ClientFactice               # noqa: E402


async def demonstration() -> None:
    print("1. LE MOT DE FIN SEUL — quand quelqu'un le dit\n")
    equipe = RoundRobinGroupChat(
        [chercheur(), redacteur()],
        termination_condition=TextMentionTermination(MOT_DE_FIN))
    resultat = await equipe.run(task="Le marche DevOps")
    print(f"   {len(resultat.messages)} messages, arret : {resultat.stop_reason}")

    print("\n2. LE MOT DE FIN SEUL — quand PERSONNE ne le dit\n")
    print("   Deux agents qui reformulent au lieu de conclure. Sans borne,")
    print("   cette equipe ne s'arreterait pas — on ne l'execute donc pas")
    print("   ici sans borne, ce serait une boucle infinie.")
    resultat = await equipe_sans_arret(borne=6).run(task="Le marche DevOps")
    print(f"\n   avec MaxMessageTermination(6) : {len(resultat.messages)} messages")
    print(f"   arret : {resultat.stop_reason}")

    print("\n3. LES DEUX, EN OU\n")
    print("   TextMentionTermination(\"TERMINE\") | MaxMessageTermination(10)")
    print("\n   Le mot seul laisse tourner une equipe qui ne conclut pas.")
    print("   La borne seule coupe une conversation utile au milieu. Les deux")
    print("   ensemble donnent : « on s'arrete quand c'est fini, et de toute")
    print("   facon on s'arrete ».")

    print("\n4. LA BORNE COMPTE LES MESSAGES, PAS LES TOURS\n")
    for borne in (3, 5, 8):
        resultat = await equipe_sans_arret(borne=borne).run(task="x")
        print(f"   borne={borne:<4}{len(resultat.messages)} messages rendus")
    print("\n   Le message de tache compte dedans. Une borne a 3 laisse donc")
    print("   deux prises de parole, pas trois — de quoi se tromper d'un cran")
    print("   en reglant, et de couper une reponse qu'on attendait.")

    print("\n5. L'ETAT SURVIT A L'ARRET\n")
    equipe = RoundRobinGroupChat(
        [chercheur(), redacteur()],
        termination_condition=MaxMessageTermination(4))
    await equipe.run(task="Le marche DevOps")
    etat = await equipe.save_state()
    print(f"   save_state() : {len(str(etat))} signes, cles {list(etat)[:3]}")
    print("\n   Une equipe arretee par une borne n'a pas fini : on la reprend")
    print("   avec load_state(). C'est ce qui rend une conversation longue")
    print("   possible sans tout garder en memoire vive.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
