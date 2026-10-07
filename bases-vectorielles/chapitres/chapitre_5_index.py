"""Chapitre 5 — Index et performance : le compromis, mesure.

Le cours cite m, ef_construct et ef en disant qu'ils pilotent le compromis
rappel / vitesse. Ce chapitre les fait varier et affiche le resultat.

    uv run python chapitres/chapitre_5_index.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.corpus import corpus                    # noqa: E402
from jobportal.hnsw import PetitMondeNavigable         # noqa: E402
from jobportal.mesures import rappel                   # noqa: E402
from jobportal.vecteurs import vectoriser              # noqa: E402

REQUETES = ["Kubernetes a Lyon", "poste senior Kafka", "React a Bordeaux",
            "machine learning teletravail", "securite applicative Paris",
            "architecte PostgreSQL", "observabilite Lille"]


def main() -> None:
    console.utf8()
    offres = corpus()
    vs = [vectoriser(o["titre"]) for o in offres]
    qs = [vectoriser(t) for t in REQUETES]

    print(f"Corpus : {len(offres)} vecteurs. Recherche exacte = "
          f"{len(offres)} comparaisons par requete.\n")
    print(f"   {'m':>3} {'ef_c':>5} {'ef':>4} {'rappel':>8} {'comparaisons':>13} {'du corpus':>10}")
    for m, efc, ef in ((4, 16, 8), (4, 32, 32), (8, 32, 16),
                       (8, 32, 64), (16, 64, 64), (16, 64, 128)):
        index = PetitMondeNavigable(m=m, ef_construct=efc)
        for v, o in zip(vs, offres):
            index.ajouter(v, o)
        r = rappel(index, vs, offres, qs, k=5, ef=ef)
        print(f"   {m:>3} {efc:>5} {ef:>4} {r.rappel:>8.0%} {r.comparaisons:>13.0f} "
              f"{r.comparaisons / r.total:>10.0%}")

    print("\nCE QUE CE TABLEAU DIT :\n")
    print("   1. Un index approche RATE des resultats. Ce n'est pas un bug,")
    print("      c'est le contrat : on echange du rappel contre du temps.")
    print("      La seule question est de savoir combien, et la reponse")
    print("      s'appelle le rappel — mesurez-le, ne le supposez pas.")
    print("\n   2. ef, regle A LA RECHERCHE, est le levier le moins cher :")
    print("      on l'augmente pour une requete importante, on le baisse pour")
    print("      une suggestion de saisie. Aucune reconstruction.")
    print("\n   3. m et ef_construct se paient A LA CONSTRUCTION. Un graphe")
    print("      bati a la va-vite garde de mauvais voisins, et AUCUNE valeur")
    print("      de ef ne le rattrapera ensuite.")
    print("\n   4. Le rendement decroit. Passer de m=8 a m=16 coute des")
    print("      comparaisons en plus pour un rappel deja a 100 % : on paie")
    print("      pour rien. C'est exactement ce qu'on fait quand on regle ces")
    print("      parametres « au cas ou ».")

    print("\n⚠️ Cet index est un petit monde navigable, pas un vrai HNSW : il")
    print("   lui manque les couches hierarchiques. Le compromis qu'il expose")
    print("   est en revanche celui d'un index de production.")


if __name__ == "__main__":
    main()
