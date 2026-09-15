"""Mesurer un index approche : le rappel, et ce qu'il a coute."""

from __future__ import annotations

from dataclasses import dataclass

from .hnsw import PetitMondeNavigable, exact


@dataclass
class Mesure:
    rappel: float
    comparaisons: float     # nombre moyen de vecteurs examines par requete
    total: int              # taille du corpus, pour situer


def rappel(index: PetitMondeNavigable, vecteurs: list[list[float]], charges: list[dict],
           requetes: list[list[float]], k: int = 5, ef: int = 32) -> Mesure:
    """Compare l'index approche a la verite exacte, requete par requete.

    Le rappel a k : parmi les k vrais plus proches, combien l'index a-t-il
    retrouves ? C'est LA metrique d'un index vectoriel — pas la latence, qui
    ne veut rien dire si l'on rend les mauvais resultats vite.
    """
    index.visites = 0
    trouves = attendus = 0
    for q in requetes:
        vrais = {c["id"] for _, c in exact(vecteurs, charges, q, k)}
        obtenus = {c["id"] for _, c in index.chercher(q, k, ef)}
        trouves += len(vrais & obtenus)
        attendus += len(vrais)
    return Mesure(rappel=trouves / attendus if attendus else 0.0,
                  comparaisons=index.visites / len(requetes),
                  total=len(vecteurs))
