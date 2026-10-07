"""Chapitre 3 — Deux moteurs, et la fusion qui ne regarde que les rangs.

    uv run python chapitres/chapitre_3_hybride.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.decoupe import decouper                          # noqa: E402
from jobportal.recherche import Index, hybride                  # noqa: E402

REQUETES = [
    "kubernete en production",          # faute de frappe volontaire
    "tests automatise",                 # singulier au lieu du pluriel
    "experience agents IA",
    "accessible aux agents en atelier",
]


def main() -> None:
    console.utf8()
    index = Index(decouper())

    print("Les deux moteurs sur les memes requetes :\n")
    divergences = 0
    for q in REQUETES:
        a = [m.id for m in index.bm25(q, 3)]
        b = [m.id for m in index.vectorielle(q, 3)]
        h = [m.id for m in hybride(index, q, 3)]
        differe = a != b
        divergences += differe
        print(f"   « {q} »" + ("   ← les deux moteurs divergent" if differe else ""))
        print(f"      bm25       {a}")
        print(f"      trigrammes {b}")
        print(f"      fusionne   {h}\n")

    print(f"   {divergences}/{len(REQUETES)} requetes ou les moteurs ne sont pas d'accord.\n")

    print("POURQUOI DES TRIGRAMMES DE CARACTERES, ET PAS DES MOTS :")
    print("   Le premier essai de ce projet mettait un TF-IDF de MOTS en face")
    print("   de BM25. Resultat mesure : deux requetes sur dix seulement se")
    print("   comportaient differemment — deux moteurs de mots classent")
    print("   presque pareil, et la fusion ne fusionnait rien.")
    print("\n   Les trigrammes comparent autre chose : « kubernete » et")
    print("   « kubernetes » partagent presque tous leurs trigrammes, la ou")
    print("   BM25 les tient pour deux termes etrangers. D'ou les faute de")
    print("   frappe et les singuliers rattrapes ci-dessus.")
    print("\n   LA LECON VAUT POUR UN VRAI SYSTEME : deux moteurs qui se")
    print("   ressemblent ne se completent pas. Si votre recherche hybride")
    print("   n'ameliore rien, verifiez d'abord que ses deux jambes")
    print("   travaillent vraiment differemment.")

    print("\nPOURQUOI RRF PLUTOT QU'UNE MOYENNE DES SCORES :")
    print("   BM25 rend des nombres non bornes, le cosinus vit entre 0 et 1.")
    print("   Les additionner n'a aucun sens ; les normaliser demande un")
    print("   reglage, et ce reglage se demode des qu'un moteur change.")
    print("   Les RANGS, eux, sont toujours comparables — c'est tout le")
    print("   principe, et c'est ce qui rend rrf() indifferent a ce qui")
    print("   produit les listes. Remplacez les trigrammes par de vrais")
    print("   embeddings : pas une ligne de rrf() ne bouge.")


if __name__ == "__main__":
    main()
