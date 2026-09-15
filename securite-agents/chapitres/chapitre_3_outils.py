"""Chapitre 3 — Moindre privilege : trois mecanismes, et un seul tient toujours.

    uv run python chapitres/chapitre_3_outils.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.defenses import Outils, Refus               # noqa: E402


def essai(outils: Outils, nom: str, **arguments) -> str:
    try:
        return outils.appeler(nom, arguments)
    except Refus as refus:
        return f"REFUSE — {refus}"


def main() -> None:
    console.utf8()

    print("1. LA LISTE BLANCHE — un outil absent n'existe pas\n")
    outils = Outils(autorises={"chercher_offres", "lire_offre", "envoyer_email"})
    for nom in ("chercher_offres", "supprimer_offre", "lire_fichier"):
        print(f"   {nom:<20}{essai(outils, nom, id=1)}")
    print("\n   « Rends service au mieux » avec tous les outils, c'est LLM06.")
    print("   Un outil qu'on n'expose pas n'a besoin d'aucune defense.")

    print("\n2. LE ROLE — un outil present peut rester refuse\n")
    for role in ("candidat", "rh"):
        o = Outils(autorises={"supprimer_offre"}, role=role)
        print(f"   role={role:<10}{essai(o, 'supprimer_offre', id=7)}")
    print("\n   Le controle se fait DANS l'outil, a partir du contexte de")
    print("   securite de l'appelant — pas dans le prompt. Un GRANT ne se")
    print("   fait pas convaincre par une phrase.")

    print("\n3. LA VALIDATION HUMAINE — la seule qui tienne sans rien prevoir\n")
    o = Outils(autorises={"envoyer_email"})
    print(f"   {essai(o, 'envoyer_email', destinataire='externe@exemple.com')}")
    print(f"   en attente : {o.en_attente}")
    print("\n   L'agent ne POSSEDE aucun outil d'envoi direct : il ne peut que")
    print("   proposer. La difference est structurelle — elle ne repose sur")
    print("   aucune reconnaissance d'attaque, donc elle protege aussi contre")
    print("   celles qu'on n'a pas imaginees.")
    print("\n   Le critere n'est pas « dangereux » mais IRREVERSIBLE : un envoi")
    print("   ne se rattrape pas, une lecture si.")

    print("\n4. LE JOURNAL — qui, quoi, quand\n")
    for acteur, action, details in o.journal.lignes:
        print(f"   {acteur:<10}{action:<28}{details}")
    o = Outils(autorises={"chercher_offres"})
    essai(o, "supprimer_offre", id=1)
    for acteur, action, details in o.journal.lignes:
        print(f"   {acteur:<10}{action:<28}{details}")
    print("\n   Les REFUS sont traces aussi, et c'est le plus utile : un refus")
    print("   est un signal d'attaque. Sans journal, on ne sait meme pas")
    print("   qu'on a ete attaque.")

    print("\n5. LES BORNES DURES — LLM10\n")
    o = Outils(autorises={"chercher_offres"}, max_appels=3)
    for n in range(5):
        sortie = essai(o, "chercher_offres", mot="x")
        print(f"   appel {n + 1} : {sortie}")
    print("\n   Une boucle d'agent qui s'emballe ne se voit qu'a la facture.")
    print("   Une borne dure la rend visible tout de suite.")

    print("\n6. LE KILL SWITCH\n")
    o = Outils(autorises={"chercher_offres"}, actifs=False)
    print(f"   {essai(o, 'chercher_offres', mot='x')}")
    print("\n   Un interrupteur qui debranche TOUS les outils : l'agent")
    print("   redevient un simple chatbot, sans redeploiement. C'est ce qu'on")
    print("   veut a 3 h du matin quand quelque chose ne va pas.")


if __name__ == "__main__":
    main()
