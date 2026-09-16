"""Chapitre 4 — Les métriques, et le score agrégé qui ment.

    uv run python chapitres/chapitre_4_metriques.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.agent import agent                      # noqa: E402
from jobportal.evaluation import evaluer               # noqa: E402


def main() -> None:
    console.utf8()
    print("Trois versions de l'agent, le même jeu de test :\n")
    print(f"   {'':4} {'global':>7} {'nominal':>9} {'limite':>8} {'advers.':>9}")
    rapports = [evaluer(agent(v)) for v in ("v1", "v2", "v3")]
    for r in rapports:
        p = r.par_type()
        print(f"   {r.version:4} {r.score:>7.0%} {p['nominal']:>9.0%} "
              f"{p['limite']:>8.0%} {p['adversarial']:>9.0%}")

    print("\n   v1 → v2 : l'agent apprend à dire « je ne sais pas ».")
    print("   v2 → v3 : il apprend à refuser ce qui sort de son rôle.")
    print("   Le nominal ne bouge pas d'un pouce — et c'est le seul que")
    print("   regarderait une évaluation mal construite.")

    print("\nLES POIDS SONT UN CHOIX, PAS UNE VÉRITÉ :")
    print("   exactitude 0,5   ancrage 0,3   latence 0,2")
    print("   Ici l'exactitude domine, parce qu'une réponse fausse mais bien")
    print("   ancrée reste fausse. Sur un assistant juridique, l'ancrage")
    print("   passerait devant. Écrivez vos poids quelque part, et datez-les :")
    print("   comparer deux scores calculés avec des poids différents n'a")
    print("   aucun sens, et c'est une erreur silencieuse.")

    echecs = rapports[-1].echecs()
    if echecs:
        print(f"\nIL RESTE {len(echecs)} ÉCHEC EN v3 — et il est instructif :\n")
        for cas, _ in echecs:
            print(f"   « {cas['entree']} » → attendu : {cas['attendu']}")
        print("\n   L'agent trouve une offre là où il n'aurait pas dû. Pourquoi ?")
        print("   La question contient « ont » (dans « ont postulé »), et la")
        print("   recherche travaille par SOUS-CHAÎNE : « ont » se trouve dans")
        print("   « fr-ont » de « Développeur front React ».")
        print("\n   Personne n'aurait trouvé ça en relisant le code. C'est")
        print("   l'évaluation qui l'a sorti — et c'est exactement à cela")
        print("   qu'elle sert. Correction : comparer des MOTS, pas des")
        print("   sous-chaînes. C'est l'exercice laissé au lecteur.")


if __name__ == "__main__":
    main()
