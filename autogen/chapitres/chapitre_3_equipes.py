"""Chapitre 3 — Ronde ou selecteur : ce que la souplesse coute.

    uv run python chapitres/chapitre_3_equipes.py
"""
from __future__ import annotations
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                       # noqa: E402
from jobportal.equipes import equipe_ronde, equipe_selective        # noqa: E402
from jobportal.modele import ClientFactice                          # noqa: E402


async def demonstration() -> None:
    print("1. LA RONDE — chacun parle a son tour, dans l'ordre de la liste\n")
    clients = (ClientFactice("chercheur"),
               ClientFactice("redacteur", dit_le_mot_de_fin=True))
    resultat = await equipe_ronde(clients).run(task="Le marche DevOps a Lyon")
    for message in resultat.messages:
        source = getattr(message, "source", "?")
        print(f"   {source:<12}{str(message.content)[:66]}")
    print(f"\n   arret : {resultat.stop_reason}")
    print(f"   appels au modele : chercheur={clients[0].tours}, "
          f"redacteur={clients[1].tours}")

    print("\n2. L'ORDRE EST GRATUIT\n")
    print("   Personne ne decide qui parle : la liste le dit. Zero appel de")
    print("   modele pour l'orchestration. C'est previsible, testable, et")
    print("   suffisant des que l'enchainement est connu d'avance.")

    print("\n3. LE SELECTEUR — un modele choisit qui parle\n")
    resultat = await equipe_selective().run(task="Le marche DevOps a Lyon")
    orateurs = [m.source for m in resultat.messages if hasattr(m, "source")]
    print(f"   orateurs : {orateurs}")
    print(f"   arret    : {resultat.stop_reason}")

    print("\n4. CE QUE LE SELECTEUR COUTE\n")
    print("   Un APPEL DE PLUS a chaque tour : avant chaque prise de parole,")
    print("   un modele lit toute la conversation pour dire un seul mot — le")
    print("   nom du prochain agent. Sur dix tours, c'est dix appels")
    print("   supplementaires, sur un contexte qui grossit.")
    print("\n   On y vient quand l'ordre DEPEND du sujet. Pas parce qu'on a")
    print("   trois agents.")

    print("\n5. LE PIEGE DU SELECTEUR\n")
    print("   Son prompt dit : « select the next role from [...]. Only return")
    print("   the role. » Une reponse qui n'est pas EXACTEMENT un nom de")
    print("   participant fait retomber AutoGen sur l'orateur precedent, avec")
    print("   un simple avertissement.")
    print("\n   L'equipe tourne alors, mal : le meme agent parle en boucle, et")
    print("   l'on croit que le selecteur « prefere » cet agent. Le client")
    print("   factice de ce projet traite ce cas — retirez `_selectionner` et")
    print("   relancez pour voir l'avertissement apparaitre.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
