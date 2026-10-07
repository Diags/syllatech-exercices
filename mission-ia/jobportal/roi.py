"""Le retour sur investissement : un calcul sur les hypothèses du client.

Rien ici n'est une mesure, sauf ce qui est marqué comme tel : le taux de
questions traitées vient du banc, le coût de fonctionnement des traces. Le
reste — volume, temps passé, coût horaire — appartient au client, et le
calcul refuse de tourner sans eux.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Hypotheses:
    questions_par_mois: int          # hypothèse du client
    minutes_par_question: float      # hypothèse du client
    cout_horaire_eur: float          # hypothèse du client, chargé
    part_traitee: float              # mesurée : cas justes du banc / total
    cout_mensuel_eur: float          # mesuré : machine amortie, ou jetons d'une API


def gain_mensuel(h: Hypotheses) -> float:
    """Le temps de support économisé, en euros, moins ce que coûte l'assistant."""
    if not 0 <= h.part_traitee <= 1:
        raise ValueError("part_traitee est une proportion, entre 0 et 1")
    heures = h.questions_par_mois * h.part_traitee * h.minutes_par_question / 60
    return round(heures * h.cout_horaire_eur - h.cout_mensuel_eur, 2)


def mois_pour_rembourser(h: Hypotheses, investissement_eur: float) -> float | None:
    """Combien de mois pour rembourser la mise en place ; None si le gain est nul ou négatif."""
    gain = gain_mensuel(h)
    return round(investissement_eur / gain, 1) if gain > 0 else None
