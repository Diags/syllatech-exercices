"""Chapitre 2 — Few-shot : montrer plutôt qu'expliquer.

Ce chapitre mesure ce que les exemples apportent, et met en évidence un
piège que personne ne mentionne : un exemple peut se retourner contre vous.

    uv run python chapitres/chapitre_2_few_shot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.evaluation import evaluer                        # noqa: E402
from jobportal.modele import modele                             # noqa: E402
from jobportal.prompts import JEU_DE_TEST, V1, V2               # noqa: E402


def main() -> None:
    console.utf8()
    m = modele()
    sans = evaluer(m, "sans exemple", V1, JEU_DE_TEST)
    avec = evaluer(m, "avec 3 exemples", V2, JEU_DE_TEST)

    print("Le même jeu de test, le même modèle, deux prompts :\n")
    for r in (sans, avec):
        print(f"   {r.version:<18} {r.reussis}/{r.total} = {r.taux:.0%}")
    print(f"\n   → les exemples font passer de {sans.taux:.0%} à {avec.taux:.0%}.")

    print("\nCe n'est pas un tour de passe-passe : le modèle de ce projet LIT")
    print("les exemples écrits dans le prompt et s'en sert pour comparer.")
    print("Sans exemple, il n'a rien pour décider — il devine. Le mécanisme")
    print("est le même que pour un vrai LLM, en beaucoup plus simple.")

    print("\nMAIS — et c'est le piège du chapitre — regardez ce qui résiste :\n")
    for entree, attendu, obtenu in avec.echecs:
        print(f"   « {entree} »")
        print(f"      attendu {attendu}, obtenu {obtenu}")

    print("\nL'exemple « Process trop long mais recruteur au top » est étiqueté")
    print("MITIGÉ — à juste titre. Mais il contient « recruteur au top », du")
    print("vocabulaire franchement positif. Il attire donc vers MITIGÉ tout")
    print("feedback qui parle d'un bon recruteur.")
    print("\nRETENEZ CECI : un exemple few-shot doit être DISCRIMINANT, pas")
    print("seulement correct. Un cas ambigu enseigne l'ambiguïté.")


if __name__ == "__main__":
    main()
