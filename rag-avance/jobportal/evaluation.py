"""Evaluer la RECUPERATION — la partie qu'on peut mesurer sans modele.

Le cours cite ragas et ses quatre metriques. Deux d'entre elles portent sur la
recuperation et se calculent EXACTEMENT, sans juge :

  rappel du contexte      les passages attendus sont-ils dans ce qu'on a
                          recupere ? Ce qui manque ici est definitivement
                          perdu : aucun modele ne repondra avec un document
                          qu'on ne lui a pas donne.
  precision du contexte   la proportion de bruit dans ce qu'on a recupere.

Les deux autres — fidelite, pertinence de la reponse — portent sur le texte
genere, et demandent un juge. Le projet eval-llm du catalogue s'en occupe.

Commencez toujours par celles-ci : un RAG qui echoue echoue presque toujours
a la recuperation, et le mesurer coute zero.
"""

from __future__ import annotations

from dataclasses import dataclass

from .rag import Rag

# Chaque cas dit quels DOCUMENTS doivent etre remontes. C'est la verite de
# terrain, et elle s'ecrit a la main : c'est le vrai cout d'une evaluation.
JEU: list[dict] = [
    {"question": "Un poste Kubernetes a Lyon ?", "attendus": {"jp-005"},
     "pourquoi": "une seule offre coche les deux criteres"},
    {"question": "Qui travaille avec Kafka ?", "attendus": {"jp-001"},
     "pourquoi": "terme rare, une seule occurrence"},
    {"question": "Une offre en teletravail complet ?", "attendus": {"jp-002"},
     "pourquoi": "modalite, pas competence"},
    {"question": "Quel poste demande de l'astreinte ?", "attendus": {"jp-003", "jp-005"},
     "pourquoi": "DEUX documents corrects : le rappel doit les trouver tous les deux"},
    {"question": "Accessibilite des interfaces", "attendus": {"jp-004"},
     "pourquoi": "vocabulaire propre a une seule fiche"},
    {"question": "Un CDD ?", "attendus": {"jp-003"},
     "pourquoi": "type de contrat, mentionne une fois"},
]


@dataclass
class Mesure:
    rappel: float
    precision: float

    @property
    def f1(self) -> float:
        s = self.rappel + self.precision
        return 2 * self.rappel * self.precision / s if s else 0.0


def mesurer(rag: Rag, cas: dict, k: int = 3) -> Mesure:
    sources = {m.metadonnees["source"] for m in rag.recuperer(cas["question"], k)}
    attendus = cas["attendus"]
    trouves = sources & attendus
    return Mesure(rappel=len(trouves) / len(attendus) if attendus else 0.0,
                  precision=len(trouves) / len(sources) if sources else 0.0)


def evaluer(rag: Rag, k: int = 3) -> dict:
    mesures = [mesurer(rag, cas, k) for cas in JEU]
    n = len(mesures)
    return {"rappel": sum(m.rappel for m in mesures) / n,
            "precision": sum(m.precision for m in mesures) / n,
            "f1": sum(m.f1 for m in mesures) / n,
            "detail": list(zip(JEU, mesures))}
