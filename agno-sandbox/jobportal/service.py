"""Le service d'évaluation — la frontière entre le job portal et l'agent.

Le cours montre une route FastAPI. Ce module écrit la même frontière sans
FastAPI : ce qui compte n'est pas le framework, c'est **ce qui traverse**.

    file d'attente  →  évaluation  →  verdict stocké  →  revue humaine ?

CE QUE LA FRONTIÈRE DOIT TENIR

  · un plafond sur la TAILLE de la soumission, avant de l'écrire sur disque ;
  · une évaluation qui ne peut pas durer indéfiniment, même si tout le reste
    échoue ;
  · un verdict typé, donc insérable sans analyse de texte ;
  · une file de revue humaine — parce que `comportement_suspect` n'est utile
    que si quelqu'un le regarde.

⚠️ Ce n'est pas un serveur : rien n'écoute sur un port. Le chapitre 5 exerce
les mêmes étapes en mémoire, et dit ce qui manque pour en faire un service.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .evaluateur import Evaluateur, Evaluation
from .soumissions import Soumission
from .verdict import Verdict

TAILLE_MAX = 20_000        # signes de code accepté par soumission


class Refuse(Exception):
    """Refus AVANT toute exécution — le moins cher des refus."""


@dataclass
class Depot:
    """Ce que le job portal garde de chaque évaluation."""

    verdicts: dict[str, Verdict] = field(default_factory=dict)
    a_relire: list[str] = field(default_factory=list)
    refuses: dict[str, str] = field(default_factory=dict)

    def enregistrer(self, evaluation: Evaluation) -> None:
        self.verdicts[evaluation.soumission] = evaluation.verdict
        if evaluation.verdict.comportement_suspect:
            self.a_relire.append(evaluation.soumission)

    def refuser(self, nom: str, pourquoi: str) -> None:
        self.refuses[nom] = pourquoi

    def resume(self) -> dict[str, int]:
        return {"evaluees": len(self.verdicts),
                "a_relire": len(self.a_relire),
                "refusees": len(self.refuses)}


@dataclass
class Service:
    evaluateur: Evaluateur
    depot: Depot = field(default_factory=Depot)
    taille_max: int = TAILLE_MAX

    def recevoir(self, soumission: Soumission) -> Evaluation | None:
        """Le trajet complet d'une soumission, dans l'ordre du moins cher.

        Le contrôle de taille passe AVANT tout le reste : refuser après
        avoir démarré un sous-processus coûte un sous-processus.
        """
        # TODO : refuser AVANT d'executer quoi que ce soit si le code depasse le plafond, journaliser le refus, et rendre None. Refuser apres avoir demarre un sous-processus coute un sous-processus — sur 400 candidatures, c'est la difference entre un refus gratuit et 80 secondes de machine. Deux tests le verifient.
        pass

    def lot(self, soumissions: list[Soumission]) -> list[Evaluation]:
        """Un lot, sans qu'une soumission puisse en empêcher une autre.

        ⚠️ Sans le `try`, une seule soumission qui lève arrête la campagne
        d'évaluation — et c'est le candidat fautif qui décide lesquels de ses
        concurrents seront notés.
        """
        faites = []
        for soumission in soumissions:
            try:
                evaluation = self.recevoir(soumission)
            except Exception as souci:               # noqa: BLE001
                self.depot.refuser(soumission.nom,
                                   f"{type(souci).__name__}: {souci}")
                continue
            if evaluation is not None:
                faites.append(evaluation)
        return faites
