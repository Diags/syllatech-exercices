"""Chapitre 6 — Anti-hallucination et évaluation.

Deux réponses au même problème : faire en sorte que le modèle PUISSE dire
qu'il ne sait pas, et se donner les moyens de MESURER si le prompt s'améliore.

    uv run python chapitres/chapitre_6_fiabilite.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                          # noqa: E402
from jobportal.evaluation import comparer                        # noqa: E402
from jobportal.modele import modele                              # noqa: E402
from jobportal.prompts import ANCRE, JEU_DE_TEST, VERSIONS       # noqa: E402


def main() -> None:
    console.utf8()
    m = modele()

    print("1. ANCRER, et autoriser l'ignorance\n")
    contexte = donnees.get_offre("JP-002")
    for question in ("Quelles compétences pour l'offre JP-002 ?",
                     "Quel est le montant du salaire ?"):
        r = m.repondre(ANCRE.format(contexte=contexte, entree=question), question, contexte)
        etat = "REFUS" if r.refus else "réponse"
        print(f"   {etat:<8} « {question} »")
        print(f"            → {r.texte[:70]}")

    print("\n   La seconde question n'a pas de réponse dans le contexte. Sans")
    print("   consigne, un modèle invente un salaire plausible. Avec la")
    print("   phrase de repli imposée, il rend exactement cette phrase — et")
    print("   un refus reconnaissable est une donnée, pas un échec.")

    print("\n2. MESURER, au lieu de discuter\n")
    resultats = comparer(m, VERSIONS, JEU_DE_TEST)
    for r in resultats:
        barre = "█" * round(r.taux * 24)
        print(f"   {r.version}  {r.reussis}/{r.total}  {r.taux:>4.0%}  {barre}")

    meilleur = max(resultats, key=lambda r: r.taux)
    print(f"\n   La version {meilleur.version} l'emporte. Ce n'est pas une")
    print("   impression : c'est le même jeu de test pour les trois.")

    if meilleur.echecs:
        print(f"\n   Il reste {len(meilleur.echecs)} échec(s) en {meilleur.version} :")
        for entree, attendu, obtenu in meilleur.echecs:
            print(f"      « {entree} » → {obtenu}, attendu {attendu}")
        print("\n   Un prompt à 100 % sur son propre jeu de test doit d'ailleurs")
        print("   inquiéter : c'est souvent le jeu qui a été taillé pour le")
        print("   prompt, et non l'inverse.")

    print("\n3. VERSIONNER\n")
    print("   Gardez v1, v2, v3 côte à côte, avec leurs scores. Le jour où")
    print("   une « amélioration » fait chuter le score, vous le verrez — et")
    print("   vous pourrez revenir en arrière. Sans versions ni score, une")
    print("   régression de prompt est invisible jusqu'à la plainte client.")


if __name__ == "__main__":
    main()
