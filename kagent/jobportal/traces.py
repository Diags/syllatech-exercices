"""Des spans OpenTelemetry, ecrits a la main pour pouvoir les regarder.

CE QU'UNE TRACE APPORTE A UN AGENT
----------------------------------
Un agent est une machine a decisions : quel outil appeler, avec quels
arguments, pour quel resultat. Sans traces, un comportement erratique reste
indebogable — on voit une reponse, jamais le chemin qui y mene.

CE QUE CE MODULE MODELISE
-------------------------
Le strict necessaire du modele de donnees OTEL : un `trace_id` partage par
tous les spans d'une meme operation, un `parent` qui les relie, un nom, une
duree et des attributs. Les noms d'attributs suivent la convention
`gen_ai.*` des semantic conventions.

⚠️ LE PIEGE QUE LE CHAPITRE 5 MESURE. Deux spans n'appartiennent a la meme
trace que si le CONTEXTE a ete propage entre eux. Quand un agent en invoque
un autre sans transmettre son contexte, le second ouvre une trace NEUVE :
les deux moities de l'incident existent, elles sont correctes, et aucun
ecran ne les montre ensemble. C'est la panne d'observabilite la plus
courante, et la plus longue a diagnostiquer — parce que rien n'est casse.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from typing import Any, Iterator

_COMPTEUR = itertools.count(1)


def _identifiant(prefixe: str) -> str:
    return f"{prefixe}-{next(_COMPTEUR):04d}"


@dataclass
class Span:
    nom: str
    trace: str
    identifiant: str
    parent: str | None = None
    millisecondes: float = 0.0
    attributs: dict[str, Any] = field(default_factory=dict)

    @property
    def racine(self) -> bool:
        return self.parent is None


class Collecteur:
    """Ce qu'un exportateur OTLP recevrait."""

    def __init__(self) -> None:
        self.spans: list[Span] = []

    def ouvrir(self, nom: str, parent: Span | None = None,
               trace: str | None = None, **attributs: Any) -> Span:
        """⚠️ Sans `parent` NI `trace`, un span ouvre une trace neuve."""
        # TODO : heriter de la trace du parent, ou en ouvrir une neuve
        identifiant_trace = _identifiant("trace")
        span = Span(nom, identifiant_trace, _identifiant("span"),
                    parent.identifiant if parent else None,
                    attributs=dict(attributs))
        self.spans.append(span)
        return span

    # -- consultation ---------------------------------------------------

    @property
    def traces(self) -> list[str]:
        vues: list[str] = []
        for span in self.spans:
            if span.trace not in vues:
                vues.append(span.trace)
        return vues

    def de_la_trace(self, trace: str) -> list[Span]:
        return [span for span in self.spans if span.trace == trace]

    def enfants(self, span: Span) -> list[Span]:
        return [autre for autre in self.spans
                if autre.parent == span.identifiant]

    def total(self, attribut: str) -> float:
        return sum(float(span.attributs.get(attribut, 0))
                   for span in self.spans)

    def par_nom(self, nom: str) -> list[Span]:
        return [span for span in self.spans if span.nom == nom]

    def arbre(self, trace: str) -> Iterator[tuple[int, Span]]:
        """Parcours en profondeur, avec la profondeur de chaque span."""
        racines = [s for s in self.de_la_trace(trace) if s.racine]

        def descendre(span: Span, niveau: int) -> Iterator[tuple[int, Span]]:
            yield niveau, span
            for enfant in self.enfants(span):
                yield from descendre(enfant, niveau + 1)

        for racine in racines:
            yield from descendre(racine, 0)


def rendre(collecteur: Collecteur, trace: str | None = None) -> list[str]:
    """L'arbre des spans, tel qu'un explorateur de traces le montrerait."""
    lignes: list[str] = []
    traces = [trace] if trace else collecteur.traces
    for identifiant in traces:
        lignes.append(f"trace {identifiant}")
        for niveau, span in collecteur.arbre(identifiant):
            interessants = {cle: valeur for cle, valeur in span.attributs.items()
                            if cle.startswith("gen_ai.") or cle in
                            ("agent.nom", "outil.nom", "a2a.delegue",
                             "erreur")}
            details = "  ".join(f"{cle}={valeur}"
                                for cle, valeur in sorted(interessants.items()))
            lignes.append(f"  {'  ' * niveau}└ {span.nom:<34} "
                          f"{span.millisecondes:>6.0f} ms  {details}")
    return lignes
