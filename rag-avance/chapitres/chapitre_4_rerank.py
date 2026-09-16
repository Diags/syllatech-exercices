"""Chapitre 4 — Recuperer large, trier fin.

    uv run python chapitres/chapitre_4_rerank.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.decoupe import decouper                          # noqa: E402
from jobportal.evaluation import evaluer                        # noqa: E402
from jobportal.rag import Rag                                   # noqa: E402
from jobportal.recherche import Index, hybride                  # noqa: E402
from jobportal.rerank import reclasser, score_paire             # noqa: E402

QUESTION = "Un poste senior Kubernetes a Lyon avec de l'astreinte"


def main() -> None:
    console.utf8()
    index = Index(decouper())

    large = hybride(index, QUESTION, 8)
    fin = reclasser(QUESTION, large, 3)

    print(f"Question : « {QUESTION} »\n")
    print(f"1. RECUPERATION LARGE — {len(large)} candidats, classement de la fusion :\n")
    for rang, m in enumerate(large, 1):
        print(f"   {rang}. {m.id:<10} {m.texte.strip().splitlines()[0][:52]}")

    print(f"\n2. RECLASSEMENT — on note chaque paire, on garde {len(fin)} :\n")
    for m in large:
        marque = "  ← gardé" if m in fin else ""
        print(f"   {score_paire(QUESTION, m):.3f}  {m.id:<10}{marque}")

    print("\n   Remarquez que l'ordre change. Le reclasseur voit la requete ET")
    print("   le passage ENSEMBLE ; la recherche, elle, compare un passage a")
    print("   un vecteur de requete, sans jamais les lire cote a cote.")

    print("\nPOURQUOI DEUX ETAPES PLUTOT QU'UNE :")
    print("   La recherche compare la requete a TOUT le corpus : elle doit")
    print("   etre rapide, donc grossiere. Le reclasseur ne voit que huit")
    print("   paires : il peut etre lent, donc fin. Inverser les deux —")
    print("   reclasser tout le corpus — serait juste, et impraticable.")

    print("\nCE QUE CA VAUT, MESURE :\n")
    sans = evaluer(Rag("naif"))
    avec = evaluer(Rag("avance"))
    print(f"   {'':8} {'rappel':>8} {'precision':>11} {'F1':>6}")
    for nom, r in (("naif", sans), ("avance", avec)):
        print(f"   {nom:8} {r['rappel']:>8.0%} {r['precision']:>11.0%} {r['f1']:>6.0%}")

    print("\n   ⚠️ SUBSTITUTION ASSUMEE : un vrai systeme met ici un")
    print("   cross-encoder, un modele qui lit la requete et le passage")
    print("   ensemble. Celui-ci applique trois regles lisibles — couverture,")
    print("   proximite, densite. C'est moins bon, et c'est dit. La MECANIQUE,")
    print("   elle, est identique : recuperer large, trier fin, couper court.")


if __name__ == "__main__":
    main()
