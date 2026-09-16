"""Chapitre 4 — Le reviseur, et la verification adversariale.

    uv run python chapitres/chapitre_4_reviseur.py

« Un modele qui cherche des bugs en trouve toujours. » Le cours le dit ; ce
chapitre le montre, puis montre ce qui reste apres relecture.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, depot, travaux   # noqa: E402
from jobportal.agents import Session            # noqa: E402


def main() -> None:
    console.utf8()
    diff = depot.diff()
    print(f"Le diff de la branche : {len(diff)} fichiers.")
    print("On ne revoit PAS tout le depot (52 fichiers) — seulement ce qui a")
    print(f"change. {', '.join(f.chemin for f in diff)}\n")

    print("1. LA PREMIERE PASSE — tout ce que le reviseur a trouve\n")
    session = Session()
    brut = session.deleguer("reviseur", "relis le diff",
                            travaux.reviser(diff, adversarial=False))
    genres = {}
    for c in brut.constats:
        genres[c["genre"]] = genres.get(c["genre"], 0) + 1
    print(f"   {len(brut.constats)} constats :")
    for genre, n in sorted(genres.items(), key=lambda x: -x[1]):
        print(f"     {n:>3}  {genre}")
    print("\n   Un rapport de 28 lignes ou 3 comptent. On les lit une fois, on")
    print("   les survole la deuxieme, et on desactive le reviseur la troisieme.")

    print("\n2. LA SECONDE PASSE — chaque constat relu DANS LE CODE\n")
    session = Session()
    verifie = session.deleguer("reviseur", "relis le diff",
                               travaux.reviser(diff, adversarial=True))
    print(verifie.texte)

    print("\n3. CE QUE LA RELECTURE A CHANGE\n")
    garde = len(verifie.constats)
    print(f"   {'constats bruts':<30}{len(brut.constats):>5}")
    print(f"   {'presentes apres relecture':<30}{garde:>5}")
    print(f"   {'ecartes':<30}{len(brut.constats) - garde:>5}")

    print("\n   Le tri n'a pas consulte le motif qui a produit le constat : il a")
    print("   relu la ligne et cherche une preuve independante. C'est ce que")
    print("   « prouve-le, sinon jette-le » veut dire concretement.")

    print("\n4. LE CONSTAT DOUTEUX — pourquoi trois verdicts et non deux\n")
    for c in verifie.constats:
        if c.get("verdict") == "douteux":
            print(f"   {c['fichier']}:{c['ligne']}  {c['code']}")
            print(f"   → {c['raison']}")
    print("\n   Celui-la ressemble trait pour trait a un identifiant fuite. Le")
    print("   jeter comme du bruit perdrait une information reelle ; le")
    print("   presenter comme confirme ferait perdre du temps a qui le corrige.")
    print("   Un constat n'est pas seulement vrai ou faux.")


if __name__ == "__main__":
    main()
