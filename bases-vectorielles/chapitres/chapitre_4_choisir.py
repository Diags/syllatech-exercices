"""Chapitre 4 — Choisir : pgvector, Qdrant, Weaviate, Milvus.

Il n'y a pas de meilleure base vectorielle. Il y a des contraintes, et une
base qui leur correspond. Ce chapitre transforme les reperes du cours en
questions auxquelles VOUS pouvez repondre.

    uv run python chapitres/chapitre_4_choisir.py
    uv run python chapitres/chapitre_4_choisir.py 500000 oui non
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402

REPERES = [
    ("pgvector", "vous avez deja PostgreSQL, moins d'un million de vecteurs",
     "une base de moins a exploiter ; JOINTURE avec vos autres tables",
     "pas de filtrage vectoriel avance ; l'index vit dans la RAM de Postgres"),
    ("Qdrant", "choix par defaut en production, filtrage riche",
     "filtres pousses DANS le parcours de l'index ; mode memoire pour les tests",
     "un composant de plus a exploiter, sauvegarder, surveiller"),
    ("Weaviate", "vous voulez que la base vectorise elle-meme",
     "vectorisation integree, hybride natif",
     "un couplage fort au modele choisi ; changer de modele = tout reindexer"),
    ("Milvus", "plus de cent millions de vecteurs, en cluster",
     "passage a l'echelle horizontal",
     "complexite d'exploitation sans commune mesure — a ne payer que si l'on doit"),
]


def recommander(vecteurs: int, postgres: bool, filtres: bool) -> tuple[str, str]:
    if vecteurs > 50_000_000:
        return "Milvus", "au-dela de cinquante millions, la question du cluster se pose"
    if postgres and vecteurs < 1_000_000 and not filtres:
        return "pgvector", "vous avez deja la base : n'en ajoutez pas une seconde"
    return "Qdrant", "volume ou filtrage justifient une base dediee"


def main() -> None:
    console.utf8()
    for nom, quand, pour, contre in REPERES:
        print(f"\n   {nom}")
        print(f"      quand  : {quand}")
        print(f"      pour   : {pour}")
        print(f"      contre : {contre}")

    print("\n\nLA QUESTION QU'ON OUBLIE DE POSER :\n")
    print("   « Combien de composants d'infrastructure suis-je pret a")
    print("     exploiter ? »")
    print("\n   Une base vectorielle dediee, c'est un service de plus a")
    print("   deployer, sauvegarder, surveiller, mettre a jour, et dont il")
    print("   faut connaitre les modes de panne. Sur un projet a deux")
    print("   personnes, cela pese plus lourd que dix pour cent de latence.")

    args = sys.argv[1:]
    if len(args) == 3:
        n = int(args[0])
        choix, raison = recommander(n, args[1].lower() in ("oui", "y"),
                                    args[2].lower() in ("oui", "y"))
        print(f"\n\nPOUR VOTRE CAS ({n:,} vecteurs) : {choix}".replace(",", " "))
        print(f"   {raison}")
    else:
        print("\n\n   Pour une recommandation : ajoutez trois arguments —")
        print("   nombre de vecteurs, « avez-vous deja Postgres », « filtres riches ».")
        print("   exemple :  ... chapitre_4_choisir.py 500000 oui non")


if __name__ == "__main__":
    main()
