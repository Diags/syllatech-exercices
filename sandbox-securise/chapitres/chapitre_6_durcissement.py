"""Chapitre 6 — Durcissement et tests d'evasion : ce qui se rejoue.

    uv run python chapitres/chapitre_6_durcissement.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

from jobportal import console                       # noqa: E402
from jobportal.conteneur import durcie, verifier    # noqa: E402
from evasion import tableau                         # noqa: E402

COMMANDES_VUES = [
    ("docker run --rm runner python -c $CODE",
     "la premiere version, « on durcira plus tard »"),
    ("docker run --rm --network=none --memory=256m runner python -c $CODE",
     "apres le premier incident : deux drapeaux"),
    ("docker run --rm -v /data:/data --user root --privileged runner python -c $CODE",
     "apres « ca ne marche pas », a 18 h un vendredi"),
]


def main() -> None:
    console.utf8()
    tableau()

    print("\n  9. LE DURCISSEMENT SE DEGRADE — trois commandes vues en vrai\n")
    for ligne, contexte in COMMANDES_VUES:
        soucis = verifier(ligne)
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        print(f"     {erreurs:>2} erreur(s)  {contexte}")
        print(f"                 {ligne[:74]}")
    bonne = durcie(image="runner:python", code="$CODE", runtime="runsc")
    print(f"     {sum(1 for s in verifier(bonne) if s.gravite == 'erreur'):>2} erreur(s)  "
          f"la commande generee par conteneur.py")

    print("\n     La troisieme est la plus instructive : elle a ete ECRITE par")
    print("     quelqu'un qui savait, un soir ou il fallait que ca marche.")
    print("     C'est ainsi qu'un durcissement disparait — pas par ignorance,")
    print("     par urgence. D'ou le verificateur en CI.")

    print("\n  10. LES TESTS D'EVASION SONT DES TESTS COMME LES AUTRES\n")
    print("     · ils vivent dans tests/, pas dans un document ;")
    print("     · ils echouent quand la protection tombe, pas six mois apres ;")
    print("     · ils incluent le CODE HONNETE — une isolation qui casse")
    print("       l'usage legitime sera retiree dans la semaine.")
    print("\n     uv run python outils/evasion.py --ci")
    print("     uv run --extra dev pytest -q")

    print("\n  11. CE QUE CE PROJET NE PROUVE PAS\n")
    print("     · Le niveau « conteneur » n'est pas execute ici : il est")
    print("       genere et verifie. Un noyau Linux et Docker sont requis.")
    print("     · Le corpus contient 9 evasions PUBLIQUES. Zero evasion")
    print("       reussie ne veut pas dire zero vulnerabilite.")
    print("     · Sous Windows, les bornes « resource » n'existent pas : le")
    print("       tableau le dit en tete plutot que de laisser croire.")
    print("\n     Le dire fait partie du travail. Un bac a sable dont on")
    print("     surestime la portee est plus dangereux que pas de bac a sable")
    print("     du tout — parce qu'on lui confie ce qu'on ne lui confierait pas.")


if __name__ == "__main__":
    main()
