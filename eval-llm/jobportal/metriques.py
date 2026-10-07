"""Les métriques — déterministes d'abord, coûteuses ensuite.

Le cours le dit en une ligne et c'est la ligne la plus rentable du chapitre :
« déterministes quand c'est possible ». Une égalité de chaînes coûte zéro,
répond en microsecondes et ne varie jamais. N'appelez un juge que pour ce
qu'aucune règle ne sait juger.
"""

from __future__ import annotations

from dataclasses import dataclass

from .agent import Sortie
from .juge import est_un_refus, juger_ancrage

LATENCE_MAX = 3.0      # secondes


@dataclass
class Mesure:
    exactitude: bool
    latence_ok: bool
    ancrage: float
    note_juge: int
    raison: str

    @property
    def score(self) -> float:
        """Un score agrégé, avec des poids ASSUMÉS.

        Les poids sont un choix de produit, pas une vérité : ici l'exactitude
        pèse le plus, parce qu'une réponse fausse mais bien ancrée reste
        fausse. Écrivez les vôtres — mais écrivez-les quelque part.
        """
        # TODO : écrire le score agrégé. Les poids sont un CHOIX : justifiez le vôtre en commentaire. Les tests exigent que v1 < v2 < v3.
        return 0.0


def mesurer(cas: dict, sortie: Sortie, sources: list[str]) -> Mesure:
    exactitude = cas["attendu"].lower() in sortie.texte.lower()

    if est_un_refus(sortie.texte):
        # Un refus n'affirme rien : l'ancrage n'a pas de sens, et le pénaliser
        # pousserait l'agent à inventer plutôt qu'à se taire.
        ancrage, note, raison = 1.0, 5, "refus, rien à ancrer"
    else:
        v = juger_ancrage(sortie.texte, sources)
        ancrage, note, raison = v.ancrage, v.note, v.raison

    return Mesure(exactitude=exactitude,
                  latence_ok=sortie.duree < LATENCE_MAX,
                  ancrage=ancrage, note_juge=note, raison=raison)
