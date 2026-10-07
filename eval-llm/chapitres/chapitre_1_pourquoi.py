"""Chapitre 1 — Pourquoi évaluer un LLM n'est pas tester du code.

Un test unitaire compare une sortie à une valeur. Une réponse d'assistant est
ouverte : plusieurs formulations sont justes, et une seule chaîne attendue ne
suffit plus. Ce chapitre montre ce qui remplace l'égalité.

    uv run python chapitres/chapitre_1_pourquoi.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                 # noqa: E402
from jobportal.juge import est_un_refus, juger_ancrage  # noqa: E402

SOURCES = [donnees.get_offre("JP-002")]

REPONSES = [
    ("Ingénieur IA — agents LLM chez syllatech, en télétravail.", "reformulation fidèle"),
    ("Le poste JP-002 est un CDI en télétravail.", "vraie, mais incomplète"),
    ("Ce poste est proposé à Marseille avec un salaire de 80 000 €.", "inventée de bout en bout"),
    ("Information non disponible.", "refus honnête"),
]


def main() -> None:
    console.utf8()
    print("Une seule question, quatre réponses — laquelle est « juste » ?\n")
    print(f"SOURCE : {SOURCES[0].splitlines()[0]}\n")

    for texte, commentaire in REPONSES:
        if est_un_refus(texte):
            print(f"   refus     « {texte} »")
            print(f"             {commentaire} — rien à ancrer, et c'est légitime\n")
            continue
        v = juger_ancrage(texte, SOURCES)
        print(f"   note {v.note}/5  « {texte[:56]} »")
        print(f"             ancrage {v.ancrage:.0%} — {v.raison}")
        print(f"             {commentaire}\n")

    print("Aucune de ces réponses n'est égale à une chaîne attendue. Pourtant")
    print("on les classe sans hésiter — parce qu'on ne teste plus l'ÉGALITÉ,")
    print("on teste des PROPRIÉTÉS : est-ce ancré dans les sources ? est-ce")
    print("complet ? est-ce un refus assumé ?")
    print("\nTrois remarques pour la suite :")
    print("  · la troisième réponse est fluide, confiante, et fausse. Aucun")
    print("    test de format ne l'aurait attrapée ;")
    print("  · la quatrième est la meilleure quand l'information manque, et")
    print("    un score naïf la pénaliserait ;")
    print("  · l'ancrage se calcule SANS modèle. Gardez le juge LLM pour ce")
    print("    qu'aucune règle ne sait juger (chapitre 3).")


if __name__ == "__main__":
    main()
