"""Chapitre 1 — Embeddings et similarite : ce que mesurent les trois distances.

    uv run python chapitres/chapitre_1_similarite.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                          # noqa: E402
from jobportal.vecteurs import (cosinus, euclidienne, normaliser,      # noqa: E402
                                produit_scalaire, relation_cosinus_l2,
                                vectoriser)

TEXTES = [
    "Lead Kubernetes — Lyon",
    "Expert Kubernetes — Lyon",
    "Lead Kubernetes — Nantes",
    "Developpeur React TypeScript — Bordeaux",
]


def main() -> None:
    console.utf8()
    base = vectoriser(TEXTES[0])
    print(f"Reference : « {TEXTES[0] } »\n")
    print(f"   {'texte':<44} {'cosinus':>8} {'L2':>7}")
    for t in TEXTES[1:]:
        v = vectoriser(t)
        print(f"   {t:<44} {cosinus(base, v):>8.3f} {euclidienne(base, v):>7.3f}")

    print("\n   Le cosinus MONTE avec la ressemblance, la L2 DESCEND.")
    print("   Confondre les deux sens ne plante pas : cela rend simplement")
    print("   les pires resultats en premier. C'est l'erreur la plus courante")
    print("   et la plus difficile a voir.")

    print("\nSUR DES VECTEURS NORMALISES, LES DEUX DISENT LA MEME CHOSE :\n")
    print("   ||a - b||² = 2 - 2·cos(a, b)\n")
    print(f"   {'texte':<44} {'cosinus':>8} {'L2 calculee':>12} {'L2 mesuree':>11}")
    for t in TEXTES[1:]:
        v = vectoriser(t)
        c, l2_theorique = relation_cosinus_l2(base, v)
        print(f"   {t:<44} {c:>8.3f} {l2_theorique:>12.3f} {euclidienne(base, v):>11.3f}")

    print("\n   Les deux dernieres colonnes sont identiques. CONSEQUENCE")
    print("   PRATIQUE : si vos vecteurs sont normalises — et la plupart des")
    print("   modeles en rendent des normalises — choisir entre <=> et <->")
    print("   dans pgvector NE CHANGE PAS LE CLASSEMENT. Le debat sur la")
    print("   metrique n'a de sens que sur des vecteurs qui ne le sont pas.")

    print("\nET LE PRODUIT SCALAIRE ?\n")
    a, b = vectoriser(TEXTES[0]), vectoriser(TEXTES[1])
    print(f"   sur vecteurs normalises : {produit_scalaire(a, b):.3f}"
          f"   (= cosinus : {cosinus(a, b):.3f})")
    gonfle = [x * 5 for x in b]
    print(f"   si l'un est multiplie par 5 : {produit_scalaire(a, gonfle):.3f}"
          f"   (cosinus inchange : {cosinus(a, gonfle):.3f})")
    print("\n   Le produit scalaire recompense la LONGUEUR. Sur du texte, cela")
    print("   revient a classer par taille de document autant que par sujet.")
    print("   Ne l'employez que si vous savez pourquoi.")

    print("\n⚠️ D'OU VIENNENT CES VECTEURS : du hachage de trigrammes, pas d'un")
    print("   modele. La geometrie est reelle, la semantique non — « poste »")
    print("   et « emploi » restent eloignes. Voir jobportal/vecteurs.py.")


if __name__ == "__main__":
    main()
