"""Chapitre 1 — Le modele de menace : ce que l'anti-patron concede.

    uv run python chapitres/chapitre_1_menace.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal.evasions import EVASIONS             # noqa: E402
from jobportal.niveaux import naif                  # noqa: E402


def main() -> None:
    console.utf8()
    print("1. LE CODE DU CHAPITRE, TEL QUEL\n")
    print("     r = subprocess.run([\"python\", \"-c\", code_candidat],")
    print("                        capture_output=True, text=True)")
    print("\n   Trois absences, et chacune coute :")
    print("     · aucune isolation  → vos droits, vos fichiers, votre reseau")
    print("     · aucun timeout     → une boucle infinie fige le service")
    print("     · aucune borne      → une allocation tue la machine")

    print("\n2. CE QU'IL CONCEDE, MESURE\n")
    for e in EVASIONS:
        r = naif(e.code)
        print(f"   {'ECHAPPE' if r.echappe else 'bloque ':<9}{e.nom:<42}{e.cherche}")

    print("\n3. LE MODELE DE MENACE, EN TROIS QUESTIONS\n")
    questions = [
        ("D'ou vient le code ?", "d'un candidat qu'on ne connait pas"),
        ("Que peut-il atteindre ?", "tout ce que le processus peut atteindre"),
        ("Que perd-on s'il s'echappe ?", "la machine, les autres candidatures, la base"),
    ]
    for question, reponse in questions:
        print(f"   {question:<32}{reponse}")
    print("\n   La troisieme decide du niveau. Isoler coute — en latence, en")
    print("   complexite, en exploitation. On ne paie ce prix qu'en sachant")
    print("   ce qu'on protege.")

    print("\n4. CE QU'ON N'ISOLE PAS\n")
    print("   Du code qu'on a ecrit, revu et versionne n'a pas besoin d'un")
    print("   bac a sable : il a besoin de tests. Isoler tout par principe")
    print("   produit un systeme lent que personne ne comprend, et dont les")
    print("   bacs a sable finissent desactives « le temps de deboguer ».")


if __name__ == "__main__":
    main()
