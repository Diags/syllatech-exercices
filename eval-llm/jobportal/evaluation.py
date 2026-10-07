"""Le harnais : faire tourner tout le jeu, et rendre un chiffre comparable."""

from __future__ import annotations

from dataclasses import dataclass, field

from .agent import Agent
from .jeu import JEU
from .metriques import Mesure, mesurer


@dataclass
class Rapport:
    version: str
    mesures: list[tuple[dict, Mesure]] = field(default_factory=list)

    @property
    def score(self) -> float:
        return sum(m.score for _, m in self.mesures) / len(self.mesures) if self.mesures else 0.0

    def par_type(self) -> dict[str, float]:
        """Le score global masque TOUJOURS quelque chose. Un agent qui
        cartonne en nominal et s'effondre en adversarial peut afficher un
        score honorable — et être inutilisable en production."""
        types: dict[str, list[float]] = {}
        for cas, m in self.mesures:
            types.setdefault(cas["type"], []).append(m.score)
        return {t: sum(v) / len(v) for t, v in types.items()}

    def echecs(self) -> list[tuple[dict, Mesure]]:
        return [(c, m) for c, m in self.mesures if not m.exactitude]


def evaluer(agent: Agent, jeu: list[dict] | None = None) -> Rapport:
    rapport = Rapport(agent.version)
    for cas in (jeu or JEU):
        sortie = agent.repondre(cas["entree"])
        sources = [_source(i) for i in sortie.sources]
        rapport.mesures.append((cas, mesurer(cas, sortie, sources)))
    return rapport


def _source(offre_id: str) -> str:
    from . import donnees
    return donnees.get_offre(offre_id)
