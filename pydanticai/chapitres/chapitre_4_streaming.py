"""Chapitre 4 — Le streaming d'une sortie STRUCTUREE.

    uv run python chapitres/chapitre_4_streaming.py

Diffuser du texte est facile. Diffuser un OBJET valide alors qu'il n'est pas
encore complet, c'est le probleme que PydanticAI resout.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import BaseModel, Field                        # noqa: E402
from pydantic_ai import Agent                                # noqa: E402
from pydantic_ai.models.test import TestModel                # noqa: E402

from jobportal import console                                # noqa: E402
from jobportal.modele import modele, modele_diffuseur        # noqa: E402


class Rapport(BaseModel):
    titre: str = Field(min_length=1)
    points: list[str] = Field(default_factory=list)


async def demonstration() -> None:
    agent = Agent(modele(modele_diffuseur()), output_type=Rapport)

    print("1. LA SORTIE ARRIVE PAR MORCEAUX, ET RESTE VALIDE\n")
    async with agent.run_stream("Analyse le marche DevOps") as flux:
        n = 0
        async for partiel in flux.stream_output():
            n += 1
            print(f"   partiel {n} : titre={partiel.titre!r}")
            for point in partiel.points:
                print(f"               · {point}")
    print(f"\n   {n} objet(s) partiel(s), tous du type Rapport.")
    print("   C'est la difficulte reelle : a mi-chemin, le JSON du modele est")
    print("   INCOMPLET — une accolade manque, une chaine n'est pas fermee.")
    print("   PydanticAI le repare a la volee et valide ce qui est deja la,")
    print("   en relachant les champs encore absents. Vous recevez donc un")
    print("   objet utilisable, pas une chaine a parser vous-meme.")

    print("\n2. LES TROIS FACONS DE DIFFUSER\n")
    async with Agent(modele(TestModel()), output_type=Rapport).run_stream("x") as flux:
        methodes = [m for m in dir(flux) if m.startswith("stream")]
        for m in methodes:
            print(f"   {m}")
    print("\n   stream_output   les objets partiels, valides — pour une IHM")
    print("   stream_text     le texte brut — seulement si output_type est str")
    print("   stream_response les evenements du modele — pour tracer, debeuguer")

    print("\n3. CE QUE LE STREAMING NE FAIT PAS\n")
    print("   Il ne reduit pas le cout : les memes tokens sont factures.")
    print("   Il ne reduit pas la latence TOTALE : le dernier morceau arrive")
    print("   au meme moment. Il reduit la latence PERCUE — le premier")
    print("   morceau arrive bien plus tot. C'est une propriete d'interface,")
    print("   pas de performance, et la confondre mene a l'utiliser la ou")
    print("   personne ne regarde l'ecran : dans un traitement par lot, il")
    print("   n'apporte rien et complique le code.")

    print("\n4. UN VALIDATEUR + DU STREAMING = ATTENTION\n")
    print("   Un validateur de sortie (chapitre 2) ne peut pas s'executer sur")
    print("   un objet PARTIEL sans risquer de refuser ce qui allait devenir")
    print("   valide. Les deux se combinent, mais la validation de sens")
    print("   n'a lieu qu'a la fin : pendant le flux, ne montrez pas ce que")
    print("   vous n'avez pas encore verifie.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
