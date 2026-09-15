"""Le collecteur local — le VRAI SDK Langfuse, sans serveur ni clé.

CE QUI EST RÉEL ICI, ET C'EST L'ESSENTIEL

Langfuse 3.x est bâti sur OpenTelemetry : `@observe()` ouvre un span OTEL, et
le SDK y écrit ses attributs (`langfuse.observation.input`, `.output`,
`.type`, l'usage, le coût…). Ce qui part vers le serveur Langfuse, ce sont ces
spans, tels quels.

`Langfuse(tracer_provider=...)` permet de fournir son propre `TracerProvider`.
On en construit donc un avec un exportateur **local**, et l'on reçoit
exactement ce que Langfuse recevrait — nom, attributs, durée, parenté.

Le SDK n'est pas simulé. Seule la destination change, et c'est ce qui rend ce
projet exécutable : pas de compte, pas de clé, pas de réseau.

CE QUI NE MARCHE PAS SANS SERVEUR

`get_prompt()`, `get_dataset()`, `create_score()` interrogent l'API : ils ont
besoin d'un vrai Langfuse. Les chapitres 4 et 5 montrent la forme exacte, et
implémentent l'équivalent local pour que le mécanisme soit mesurable — en le
disant clairement à chaque fois.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (SimpleSpanProcessor, SpanExporter,
                                            SpanExportResult)

# Les attributs que Langfuse pose sur un span. Les connaître aide à lire une
# trace — et à comprendre pourquoi un champ manque.
PREFIXE = "langfuse."


@dataclass
class Observation:
    """Un span, tel que Langfuse le recevrait."""

    nom: str
    genre: str                       # "span", "generation", "tool"…
    entree: Any = None
    sortie: Any = None
    duree_ms: float = 0.0
    attributs: dict = field(default_factory=dict)
    id_span: int = 0
    id_parent: int | None = None
    parent: str | None = None

    @property
    def metadonnees(self) -> dict:
        return {c.removeprefix(PREFIXE): v for c, v in self.attributs.items()
                if c.startswith(PREFIXE)}


class Collecteur(SpanExporter):
    """Garde les spans au lieu de les envoyer."""

    def __init__(self) -> None:
        self.observations: list[Observation] = []
        self._par_id: dict[int, str] = {}

    def export(self, spans) -> SpanExportResult:
        for span in spans:
            attributs = dict(span.attributes or {})
            # ⚠️ Un enfant se TERMINE avant son parent, donc il est exporte
            # AVANT lui : au moment ou on le voit, le nom du parent n'est pas
            # encore connu. On garde donc les identifiants, et on resout la
            # parente a la lecture. Resoudre ici donnerait un arbre plat —
            # et un arbre plat a l'air d'une trace sans hierarchie.
            # >>> depart: construire une Observation par span. Garder les IDENTIFIANTS de span et de parent, pas les noms : un enfant se termine — donc s'exporte — AVANT son parent, dont le nom n'est pas encore connu. Trois tests le verifient.
            #     continue
            self.observations.append(Observation(
                nom=span.name,
                genre=attributs.get(f"{PREFIXE}observation.type", "span"),
                entree=attributs.get(f"{PREFIXE}observation.input"),
                sortie=attributs.get(f"{PREFIXE}observation.output"),
                duree_ms=(span.end_time - span.start_time) / 1e6,
                attributs=attributs,
                id_span=span.get_span_context().span_id,
                id_parent=span.parent.span_id if span.parent else None,
            ))
            # <<<
        return SpanExportResult.SUCCESS

    def shutdown(self) -> None:      # noqa: D102
        return None

    def force_flush(self, timeout_millis: int = 30_000) -> bool:  # noqa: D102
        return True

    # ------------------------------------------------------ lecture

    def vider(self) -> None:
        self.observations.clear()

    def par_nom(self, nom: str) -> list[Observation]:
        return [o for o in self.observations if o.nom == nom]

    def generations(self) -> list[Observation]:
        return [o for o in self.observations if o.genre == "generation"]

    @property
    def racines(self) -> list[Observation]:
        connus = {o.id_span for o in self.observations}
        return [o for o in self.observations
                if o.id_parent is None or o.id_parent not in connus]

    def _resoudre(self) -> None:
        noms = {o.id_span: o.nom for o in self.observations}
        for observation in self.observations:
            observation.parent = noms.get(observation.id_parent)

    def arbre(self) -> list[tuple[int, Observation]]:
        """Les observations, avec leur profondeur — pour afficher la trace."""
        self._resoudre()
        par_parent: dict[int | None, list[Observation]] = {}
        connus = {o.id_span for o in self.observations}
        for observation in self.observations:
            # Un parent hors trace (exporte ailleurs) rend l'enfant orphelin :
            # on le rattache a la racine plutot que de le perdre.
            parent = (observation.id_parent
                      if observation.id_parent in connus else None)
            par_parent.setdefault(parent, []).append(observation)

        sortie: list[tuple[int, Observation]] = []

        def descendre(identifiant: int | None, profondeur: int) -> None:
            for enfant in par_parent.get(identifiant, []):
                sortie.append((profondeur, enfant))
                descendre(enfant.id_span, profondeur + 1)

        descendre(None, 0)
        return sortie


_BRANCHEMENT: tuple[Any, Collecteur] | None = None


def brancher(vider: bool = True) -> tuple[Any, Collecteur]:
    """Rend un client Langfuse RÉEL dont les traces atterrissent ici.

    ⚠️ UN SEUL BRANCHEMENT PAR PROCESSUS, et ce n'est pas un raccourci.

    OpenTelemetry refuse de remplacer un `TracerProvider` déjà posé — il
    journalise « Overriding of current TracerProvider is not allowed » et
    garde le premier. Le client Langfuse, lui, est un singleton. Appeler
    `brancher()` deux fois donnerait donc un second collecteur qui ne reçoit
    RIEN, pendant que les spans continuent d'aller vers le premier.

    C'est exactement ce qui se produit dans une suite de tests naïve, et le
    symptôme — « aucune trace » — n'a aucun rapport avec la cause. On mémorise
    donc le branchement et on vide le collecteur à la place.

    ⚠️ `tracing_enabled=True` est indispensable : à False, `@observe()` devient
    un décorateur qui ne fait rien. Aucune erreur, aucune trace — et l'on
    cherche du côté du serveur pendant une heure.

    Les clés sont factices et ne servent à rien : rien ne part sur le réseau,
    puisque l'exportateur est local. Le SDK les exige quand même à la
    construction.
    """
    global _BRANCHEMENT
    if _BRANCHEMENT is not None:
        if vider:
            _BRANCHEMENT[1].vider()
        return _BRANCHEMENT

    import logging

    from langfuse import Langfuse

    # Le SDK construit AUSSI son exportateur reseau, meme quand on lui fournit
    # un TracerProvider. Il echoue a joindre l'hote factice et l'ecrit dans le
    # journal a chaque flush. On tait CE logger-la, et lui seul : masquer tous
    # les journaux du SDK cacherait aussi ce qu'on veut voir.
    logging.getLogger(
        "opentelemetry.exporter.otlp.proto.http.trace_exporter"
    ).setLevel(logging.CRITICAL)

    collecteur = Collecteur()
    fournisseur = TracerProvider()
    fournisseur.add_span_processor(SimpleSpanProcessor(collecteur))

    # On le pose AUSSI comme fournisseur global. C'est ce qu'on fait dans une
    # vraie application : un seul TracerProvider, que Langfuse rejoint. Sans
    # cela, un span ouvert par `trace.get_tracer(...)` — le vôtre, celui d'une
    # bibliothèque, celui d'un client HTTP — part ailleurs et n'apparaît pas
    # dans la trace. C'est la cause la plus fréquente d'une trace incomplète.
    #
    # OTEL refuse de remplacer un fournisseur déjà posé : on ignore l'échec
    # quand quelque chose l'a précédé.
    import opentelemetry.trace as _trace
    try:
        _trace.set_tracer_provider(fournisseur)
    except Exception:      # noqa: BLE001 — deja pose, on garde le sien
        pass

    client = Langfuse(
        public_key="pk-lf-local",
        secret_key="sk-lf-local",
        host="http://collecteur.local",
        tracing_enabled=True,
        tracer_provider=fournisseur,
    )
    _BRANCHEMENT = (client, collecteur)
    return _BRANCHEMENT
