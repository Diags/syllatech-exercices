"""Chapitre 5 — Flows : ce qui doit etre fiable ne va pas dans un crew.

    uv run python chapitres/chapitre_5_flows.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import ClassVar
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                    # noqa: E402
from jobportal.flux import VeilleFlow            # noqa: E402
from jobportal.modele import ModeleFactice       # noqa: E402


class Compteur(ModeleFactice):
    total: ClassVar[int] = 0

    def call(self, *a, **k):
        Compteur.total += 1
        return super().call(*a, **k)


def main() -> None:
    console.utf8()

    print("1. UN CREW N'EST PAS UN FLOW\n")
    print("   Crew  l'enchainement est decide par le MODELE (ou par l'ordre")
    print("         de la liste). Il coute, et il varie.")
    print("   Flow  l'enchainement est du CODE : @start, @router, @listen.")
    print("         Il ne coute rien et ne varie pas.")

    print("\n2. LES DEUX BRANCHES, PARCOURUES POUR DE VRAI\n")
    for vide, etiquette in ((False, "rapport rempli"), (True, "rapport vide")):
        Compteur.total = 0
        flux = VeilleFlow(Compteur(), "DevOps", collecte_vide=vide)
        with console.sans_bruit():
            _r = flux.kickoff()
        resultat = _r
        print(f"   {etiquette:<18}{' → '.join(flux.journal)}")
        print(f"   {'':<18}{Compteur.total} appel(s) au modele")
        print(f"   {'':<18}{str(resultat)[:70]}\n")

    print("   La branche « resoumettre » ne coute RIEN : elle n'appelle aucun")
    print("   agent. Dans un crew, la meme decision serait prise par un")
    print("   modele — donc payee, et parfois mal prise.")

    print("\n3. LE PIEGE DU CHAPITRE : LE NOM DU HANDLER\n")
    print("   La video ecrit :\n")
    print("     @listen(\"publier\")")
    print("     def publier(self): ...\n")
    print("   CrewAI 1.x le REFUSE a la construction du flux :")
    print("   « a listener triggered by its own completion creates an")
    print("   infinite loop ». La classe ne se cree meme pas.")
    print("\n   Le handler doit porter un autre nom que l'evenement qu'il")
    print("   ecoute. Ici : evenement « publier », handler `envoyer_newsletter`.")

    print("\n4. UN AUTRE PIEGE, CELUI-LA SILENCIEUX\n")
    print("   Redefinir une methode @start() dans une sous-classe PERD le")
    print("   decorateur : il est enregistre a la creation de la classe mere.")
    print("   Le flux s'arrete alors apres la premiere etape, sans erreur et")
    print("   sans trace. D'ou le parametre `collecte_vide` plutot qu'un")
    print("   heritage — la solution la plus evidente est la mauvaise.")

    print("\n5. LA REGLE QUI EN DECOULE\n")
    print("   Ce qui doit etre FIABLE va dans le Flow : les seuils, les")
    print("   branchements, les garde-fous, les reprises.")
    print("   Ce qui demande du JUGEMENT va dans le Crew : analyser, rediger,")
    print("   decider de ce qui merite d'etre dit.")
    print("\n   Un routeur ecrit en Python se teste sans modele, se rejoue a")
    print("   l'identique, et ne se trompe pas un jour sur dix.")


if __name__ == "__main__":
    main()
