"""L'observabilité — le VRAI mécanisme de rappel de litellm.

Le cours montre la configuration :

    litellm_settings:
      success_callback: ["prometheus", "langfuse"]

Derrière ce nom, litellm instancie un `CustomLogger` et appelle sa méthode
`async_log_success_event` après chaque appel réussi. Ce module en écrit un —
le même point d'entrée, sans serveur — pour qu'on voie ce que Prometheus et
Langfuse reçoivent.

⚠️ LA SIGNATURE DOIT ÊTRE EXACTE

    async def async_log_success_event(self, kwargs, response_obj,
                                      start_time, end_time)

litellm appelle ces quatre-là **par mot-clé**. Une signature qui les nomme
autrement lève un TypeError… que litellm rattrape et journalise en
« [Non-Blocking] Exception occurred while success logging ». La sonde ne voit
alors plus rien, le tableau de bord reste à zéro, et l'application continue de
fonctionner parfaitement. C'est la panne la plus discrète du chapitre 6, et
elle a été rencontrée en écrivant ce fichier.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

try:
    from litellm.integrations.custom_logger import CustomLogger
except Exception:                                # noqa: BLE001
    CustomLogger = object                        # type: ignore[assignment]


@dataclass
class Mesure:
    modele: str
    cout: float
    jetons: int
    latence_ms: float
    identifiant: str


class Sonde(CustomLogger):                       # type: ignore[misc]
    """Ce que `success_callback: ["prometheus"]` fait, en visible."""

    def __init__(self) -> None:
        super().__init__()
        self.mesures: list[Mesure] = []

    async def async_log_success_event(self, kwargs, response_obj,
                                      start_time, end_time):
        usage = getattr(response_obj, "usage", None)
        self.mesures.append(Mesure(
            modele=kwargs.get("model") or "",
            cout=float(kwargs.get("response_cost") or 0.0),
            jetons=int(getattr(usage, "total_tokens", 0) or 0),
            latence_ms=(end_time - start_time).total_seconds() * 1000,
            identifiant=kwargs.get("litellm_call_id") or "",
        ))

    # -- ce qu'un tableau de bord en tire ---------------------------

    def par_modele(self) -> dict[str, dict]:
        resume: dict[str, dict] = defaultdict(
            lambda: {"appels": 0, "cout": 0.0, "jetons": 0})
        for mesure in self.mesures:
            ligne = resume[mesure.modele]
            ligne["appels"] += 1
            ligne["cout"] += mesure.cout
            ligne["jetons"] += mesure.jetons
        return dict(resume)

    @property
    def cout_total(self) -> float:
        return sum(m.cout for m in self.mesures)

    def gratuits(self) -> list[str]:
        """Les modeles factures a 0,00 $ — et c'est un signal, pas un cadeau.

        Un modèle absent de la table de prix de litellm ne lève rien : il
        coûte zéro. Le tableau de bord est alors exact pour tous les autres
        et faux pour celui-là, sans qu'aucune ligne ne l'indique. C'est la
        façon dont un coût disparaît d'un budget.
        """
        return sorted({m.modele for m in self.mesures
                       if m.cout == 0.0 and m.jetons > 0})


LISTES_DERIVEES = ("_async_success_callback", "success_callback",
                   "_async_failure_callback", "failure_callback")


def brancher(sonde: Sonde) -> Sonde:
    """Enregistre la sonde auprès de litellm — et débranche les précédentes.

    ⚠️ LE PIÈGE, MESURÉ

    Réassigner `litellm.callbacks = [nouvelle]` après le premier appel
    journalisé ne fait **rien**. litellm dérive de `callbacks` une liste
    interne, `_async_success_callback`, et ne la reconstruit pas : l'ancienne
    sonde continue de tout recevoir, la nouvelle ne reçoit jamais rien.

    `outils/mesurer_doublon.py` le mesure dans un processus neuf, deux appels
    et deux branchements naïfs :

        sondes reellement appelees  1
        la PREMIERE sonde           2 mesures
        la SECONDE  sonde           0 mesure

    C'est pire qu'un doublon : on remplace son exportateur, on déploie, le
    nouveau tableau de bord reste vide — et l'ancien, parfois un bouchon de
    test, continue de tourner. Les deux moitiés du problème sont muettes.

    On purge donc les listes dérivées de nos propres sondes, en laissant
    intacts les rappels internes de litellm.
    """
    import litellm

    # TODO : enregistrer la sonde ET debrancher les precedentes. Reassigner litellm.callbacks ne suffit pas : litellm en derive des listes internes qu'il ne reconstruit pas, donc l'ancienne sonde continue de tout recevoir. Purger LISTES_DERIVEES de nos propres Sonde, sans toucher aux rappels internes de litellm. Un test le verifie, et outils/mesurer_doublon.py le mesure.
    litellm.callbacks = [sonde]; return sonde


def sondes_branchees() -> int:
    """Combien de nos sondes litellm appelle-t-il pour un seul appel ?

    ⚠️ La liste dérivée se remplit au PREMIER appel journalisé : interroger
    cette fonction avant d'avoir appelé quoi que ce soit rend toujours zéro,
    ce qui ne prouve rien.
    """
    import litellm

    derivee = getattr(litellm, "_async_success_callback", []) or []
    return sum(1 for c in derivee if isinstance(c, Sonde))


@dataclass
class TableauDeBord:
    """La vue par équipe, celle qui sert aux refacturations.

    litellm ne la connaît pas : il ne voit que des modèles. L'équipe est une
    notion de la PASSERELLE, portée par la clé virtuelle. Recoller les deux
    est exactement le travail que fait le proxy réel avec sa base PostgreSQL.
    """

    journal: list = field(default_factory=list)

    def par_equipe(self) -> dict[str, dict]:
        resume: dict[str, dict] = {}
        for trace in self.journal:
            ligne = resume.setdefault(trace.equipe, {
                "appels": 0, "refus": 0, "cout": 0.0, "jetons": 0,
                "bascules": 0, "latence_ms": 0.0})
            if trace.code != 200:
                ligne["refus"] += 1
                continue
            ligne["appels"] += 1
            ligne["cout"] += trace.cout
            ligne["jetons"] += trace.jetons
            ligne["bascules"] += int(trace.bascule)
            ligne["latence_ms"] += trace.latence_ms
        for ligne in resume.values():
            ligne["latence_moyenne_ms"] = (
                ligne["latence_ms"] / ligne["appels"] if ligne["appels"] else 0.0)
        return resume
