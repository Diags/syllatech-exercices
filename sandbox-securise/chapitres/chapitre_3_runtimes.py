"""Chapitre 3 — Conteneur durci, gVisor, microVM : ce qui change vraiment.

    uv run python chapitres/chapitre_3_runtimes.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                    # noqa: E402
from jobportal.conteneur import durcie, verifier  # noqa: E402

RUNTIMES = [
    ("runc (defaut)", "le noyau de l'HOTE", "faible", "~50 ms",
     "une faille noyau = evasion complete"),
    ("gVisor (runsc)", "un noyau en espace utilisateur", "forte", "~150 ms",
     "les appels systeme n'atteignent plus le noyau hote"),
    ("Kata / Firecracker", "une microVM dediee", "tres forte", "~400 ms",
     "une frontiere materielle, comme une VM"),
]


def main() -> None:
    console.utf8()

    print("1. LE MEME CONTENEUR, TROIS FRONTIERES\n")
    print(f"   {'runtime':<22}{'ce qui execute les appels':<34}"
          f"{'isolation':<12}{'demarrage':<11}")
    for nom, quoi, force, cout, _ in RUNTIMES:
        print(f"   {nom:<22}{quoi:<34}{force:<12}{cout:<11}")
    print()
    for nom, _, _, _, note in RUNTIMES:
        print(f"   {nom:<22}{note}")
    print("\n   ⚠️ Les temps de demarrage sont des ORDRES DE GRANDEUR tires de")
    print("   la litterature, pas des mesures faites ici : aucun de ces trois")
    print("   runtimes ne tourne sur cette machine. Mesurez les votres — le")
    print("   rapport entre eux est stable, les valeurs absolues non.")

    print("\n2. CE QUE « DURCI » NE SUFFIT PAS A DIRE\n")
    print("   Un conteneur durci avec runc partage le noyau de l'hote. Tous")
    print("   les drapeaux du chapitre 2 reduisent CE QUE le code peut")
    print("   demander au noyau — ils ne changent pas le fait qu'il lui parle")
    print("   directement. Une faille dans un appel systeme non filtre, et la")
    print("   frontiere disparait.")
    print("\n   C'est acceptable pour du code qu'on connait mal. Ca ne l'est")
    print("   pas pour du code ecrit par quelqu'un qui veut sortir.")

    print("\n3. LA BASCULE : une ligne\n")
    print("   " + durcie(image="runner:python", code="...")[:88] + "…")
    print("   " + durcie(image="runner:python", code="...", runtime="runsc")[:88] + "…")
    print("\n   Sur Kubernetes, c'est une RuntimeClass :")
    print("     spec.runtimeClassName: gvisor      # ou « kata »")
    print("\n   Le cout n'est pas nul — gVisor intercepte, donc ralentit les")
    print("   programmes qui font beaucoup d'appels systeme (E/S intensives).")
    print("   Un calcul pur n'y perd presque rien. Mesurez AVANT de trancher.")

    print("\n4. LES DEUX COMMANDES SONT-ELLES AUSSI SURES ?\n")
    for runtime in (None, "runsc"):
        ligne = durcie(image="runner:python", code="...", runtime=runtime)
        soucis = verifier(ligne)
        print(f"   {'runc' if runtime is None else runtime:<10}{len(soucis)} souci(s)")
    print("\n   Le verificateur dit « 0 » dans les deux cas — et c'est exact :")
    print("   il verifie les DRAPEAUX, pas le runtime. Aucun outil statique ne")
    print("   vous dira que runc partage le noyau : c'est une decision")
    print("   d'architecture, pas un oubli de configuration.")

    print("\n5. CHOISIR\n")
    choix = [
        ("code interne, revu", "runc durci", "le cout d'une microVM ne se justifie pas"),
        ("code d'apprenants", "gVisor", "adversaire reel, charge modeste"),
        ("code arbitraire d'Internet", "microVM", "l'adversaire a du temps"),
    ]
    for cas, reponse, pourquoi in choix:
        print(f"   {cas:<30}{reponse:<14}{pourquoi}")


if __name__ == "__main__":
    main()
