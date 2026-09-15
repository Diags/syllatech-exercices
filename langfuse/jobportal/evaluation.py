"""Scores et datasets — la forme réelle, et l'équivalent local.

`create_score` et `get_dataset` interrogent l'API : il faut un serveur. Ce
module implémente le même contrat en local, pour que la NON-RÉGRESSION soit
mesurable — c'est elle qui compte, pas l'outil.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Score:
    trace: str
    nom: str
    valeur: float
    type_donnee: str = "NUMERIC"    # NUMERIC, BOOLEAN, CATEGORICAL
    commentaire: str = ""


@dataclass
class Cas:
    entree: str
    attendu: str          # ce que la réponse doit contenir


@dataclass
class Execution:
    nom: str
    scores: list[float] = field(default_factory=list)

    @property
    def moyenne(self) -> float:
        return sum(self.scores) / len(self.scores) if self.scores else 0.0


class Registre:
    """Les scores, tels que Langfuse les accumule."""

    def __init__(self) -> None:
        self.scores: list[Score] = []

    def create_score(self, trace_id: str, name: str, value: float,
                     data_type: str = "NUMERIC", comment: str = "") -> Score:
        score = Score(trace_id, name, value, data_type, comment)
        self.scores.append(score)
        return score

    def moyenne(self, nom: str) -> float:
        valeurs = [s.valeur for s in self.scores if s.nom == nom]
        return sum(valeurs) / len(valeurs) if valeurs else 0.0


# --------------------------------------------- les trois sortes de score

def score_utilisateur(pouce_haut: bool) -> float:
    """Le plus fiable et le plus rare.

    Un pouce est un avis humain sur un cas réel. Sa limite n'est pas la
    qualité : c'est le taux de réponse. On en obtient sur 1 à 3 % des
    réponses, et ce sont rarement les cas moyens — on note ce qui a très bien
    ou très mal marché.
    """
    return 1.0 if pouce_haut else 0.0


def score_regle(reponse: str, attendu: str) -> float:
    """Déterministe, gratuit, et limité.

    Il ne juge pas la qualité : il vérifie une propriété. C'est ce qui le rend
    utilisable en non-régression — il donne le même verdict aujourd'hui et
    dans six mois, ce qu'aucun juge LLM ne garantit.
    """
    return 1.0 if attendu.lower() in reponse.lower() else 0.0


def score_juge(reponse: str, question: str) -> float:
    """Le juge LLM, ici SIMULÉ par des heuristiques vérifiables.

    ⚠️ Un vrai juge est un modèle : il coûte, il varie d'une exécution à
    l'autre, et il faut le calibrer contre des notes humaines avant de lui
    faire confiance. Les heuristiques ci-dessous ne sont PAS un juge — elles
    tiennent sa place pour que la mécanique (échantillonnage, moyenne, seuil
    d'alerte) soit mesurable sans clé.

    Ce que le chapitre doit retenir : un juge non calibré donne un chiffre
    rassurant et faux, et un chiffre faux est pire que pas de chiffre.
    """
    note = 0.0
    if len(reponse) > 20:
        note += 0.3                                    # pas une non-réponse
    if re.search(r"\d", reponse):
        note += 0.3                                    # cite un chiffre
    mots = {m.lower() for m in re.findall(r"\w{4,}", question)}
    if mots & {m.lower() for m in re.findall(r"\w{4,}", reponse)}:
        note += 0.4                                    # parle du sujet
    return round(min(1.0, note), 2)


# ------------------------------------------------------------ le dataset

JEU_METIER = [
    Cas("Quelles offres DevOps ?", "DevOps"),
    Cas("Quelles offres Python ?", "Python"),
    Cas("Quelles offres Java ?", "Java"),
    Cas("Quelles offres cloud ?", "cloud"),
    Cas("Quelles offres en soudure sous-marine ?", "Aucune"),
]


def executer(nom: str, assistant, cas=None) -> Execution:
    """Rejoue le jeu de cas et rend la moyenne — la non-régression.

    C'est la boucle qui compte : on ne compare pas une réponse à une autre, on
    compare une MOYENNE à la précédente. Une réponse peut empirer sans que la
    moyenne bouge ; c'est la moyenne qui décide si l'on déploie.
    """
    execution = Execution(nom)
    for un_cas in (cas or JEU_METIER):
        reponse = assistant(un_cas.entree)
        execution.scores.append(score_regle(reponse, un_cas.attendu))
    return execution
