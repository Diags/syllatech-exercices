"""Les vecteurs, et les trois distances — les vraies mathématiques.

⚠️ D'OU VIENNENT LES VECTEURS DE CE PROJET

Pas d'un modèle : il faudrait le télécharger. Ils sont produits par le
**hachage de trigrammes**, une technique réelle (le « hashing trick ») : on
découpe le texte en trigrammes de caractères, on hache chacun vers une
dimension, et on incrémente. Le résultat est un vrai vecteur dense, stable,
reproductible.

Ce n'est **pas** de la sémantique : « poste » et « emploi » restent éloignés.
Mais toute la géométrie de ce cours est authentique — la normalisation, les
trois distances, leurs relations, et le comportement d'un index approché. Un
vrai embedding se branche à la place sans qu'une ligne d'index ne change.
"""

from __future__ import annotations

import hashlib
import math
import re
import unicodedata

DIMENSION = 128


def plat(texte: str) -> str:
    sans = unicodedata.normalize("NFD", texte)
    sans = "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()
    return " ".join(re.findall(r"[a-z0-9]{2,}", sans))


def vectoriser(texte: str, dim: int = DIMENSION) -> list[float]:
    """Hachage de trigrammes vers un vecteur dense, puis normalisation.

    Le hachage est fait avec blake2b et non hash() : la fonction native de
    Python est randomisée d'une exécution à l'autre, et les vecteurs ne
    seraient pas reproductibles — un index construit hier ne correspondrait
    plus aux requêtes d'aujourd'hui. C'est le genre de bug qu'on met une
    semaine à comprendre.
    """
    v = [0.0] * dim
    t = plat(texte)
    for i in range(max(len(t) - 2, 0)):
        tri = t[i:i + 3]
        h = int.from_bytes(hashlib.blake2b(tri.encode(), digest_size=4).digest(), "big")
        v[h % dim] += 1.0
    return normaliser(v)


def normaliser(v: list[float]) -> list[float]:
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v] if n else v


# ---------------------------------------------------------------- distances

def produit_scalaire(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def cosinus(a: list[float], b: list[float]) -> float:
    """Similarité cosinus : l'angle, pas la longueur.

    C'est le choix par défaut pour du texte, et la raison est concrète : un
    document long a des composantes plus grandes qu'un document court sur le
    même sujet. Une distance sensible à la longueur classerait donc les
    documents par taille autant que par sujet.
    """
    # TODO : ecrire la similarite cosinus. Un test verifie l'identite ||a-b|| au carre = 2 - 2 cos sur des vecteurs normalises.
    return 0.0


def euclidienne(a: list[float], b: list[float]) -> float:
    """Distance L2. Attention : ici PLUS PETIT est meilleur, à l'inverse des
    deux autres. Confondre les deux sens est l'erreur classique — et elle ne
    plante pas, elle rend simplement les pires résultats en premier."""
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def relation_cosinus_l2(a: list[float], b: list[float]) -> tuple[float, float]:
    """Sur des vecteurs NORMALISÉS, cosinus et L2 disent la même chose.

        ||a - b||² = 2 - 2·cos(a, b)

    Conséquence pratique, et elle compte : si vos vecteurs sont normalisés,
    choisir entre `<=>` et `<->` dans pgvector ne change pas le classement.
    Le débat sur la métrique n'a de sens que sur des vecteurs qui ne le sont
    pas — et la plupart des modèles d'embedding en rendent des normalisés.
    """
    c = cosinus(a, b)
    return c, math.sqrt(max(0.0, 2 - 2 * c))
