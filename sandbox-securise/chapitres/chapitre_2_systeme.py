"""Chapitre 2 — Isolation par le systeme : le processus d'abord, le noyau ensuite.

    uv run python chapitres/chapitre_2_systeme.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                        # noqa: E402
from jobportal.conteneur import OBLIGATOIRES, durcie, verifier       # noqa: E402
from jobportal.evasions import EVASIONS                              # noqa: E402
from jobportal.niveaux import bornes_disponibles, naif, processus    # noqa: E402


def main() -> None:
    console.utf8()

    print("1. UN INTERPRETE SEPARE : ce qui change, ligne a ligne\n")
    print(f"   {'evasion':<42}{'naif':>10}{'processus':>12}")
    for e in EVASIONS:
        print(f"   {e.nom:<42}"
              f"{('ECHAPPE' if naif(e.code).echappe else 'bloque'):>10}"
              f"{('ECHAPPE' if processus(e.code).echappe else 'bloque'):>12}")

    print("\n2. LE CONTRESENS A EVITER\n")
    print("   « processus » arrete MOINS de lignes que « restreint ». Ce n'est")
    print("   pas un recul : il ne retire aucun nom — « import os » y marche —")
    print("   mais le dommage MEURT AVEC LE SOUS-PROCESSUS. Une boucle infinie")
    print("   ne fige plus le service, une remontee d'arbre de classes")
    print("   n'atteint plus votre memoire.")
    print("\n   Restreindre et contenir sont deux axes, pas deux marches.")

    print("\n3. CE QUE LE PROCESSUS N'APPORTE PAS\n")
    for e in EVASIONS:
        if processus(e.code).echappe and e.nommage == "conteneur":
            print(f"   {e.nom:<42}{e.cherche}")
    print("\n   Reseau, disque, voisinage. Un processus a toujours une pile")
    print("   reseau et les droits de l'utilisateur : c'est le noyau qu'il")
    print("   faut solliciter, pas la bibliotheque standard.")

    print(f"\n4. LES BORNES « resource » : {bornes_disponibles()}\n")
    if not bornes_disponibles():
        print("   Absentes sur cette machine (Windows). RLIMIT_AS et")
        print("   RLIMIT_NPROC sont POSIX. Le delai s'applique, la borne")
        print("   memoire non — et une isolation dont on ignore ce qu'elle")
        print("   fait en production n'est pas une isolation.")

    print("\n5. LE NOYAU : trois mecanismes, et ce que chacun retire\n")
    mecanismes = [
        ("namespaces", "la VUE : PID, reseau, montages, utilisateurs"),
        ("cgroups", "les RESSOURCES : CPU, memoire, nombre de processus"),
        ("seccomp", "les APPELS SYSTEME eux-memes, un par un"),
    ]
    for nom, quoi in mecanismes:
        print(f"   {nom:<14}{quoi}")
    print("\n   Les trois sont necessaires et aucun ne suffit : un namespace")
    print("   reseau sans cgroup laisse une fork bomb ; un cgroup sans seccomp")
    print("   laisse appeler ce qu'on veut au noyau.")

    print("\n6. LA COMMANDE DURCIE, ET CE QUE CHAQUE DRAPEAU RETIRE\n")
    for drapeau, (retire, evasion) in OBLIGATOIRES.items():
        print(f"   {drapeau:<34}{retire}")
    print(f"\n   {durcie(image='runner:python', code='...')[:96]}…")
    print(f"\n   Verification : {len(verifier(durcie(image='r', code='x')))} souci(s).")
    print("   Cette commande se relit comme du code — c'est ce que fait")
    print("   jobportal/conteneur.py, et il tourne sans Docker.")


if __name__ == "__main__":
    main()
