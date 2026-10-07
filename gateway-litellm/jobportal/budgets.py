"""Clés virtuelles et budgets — la couche que le proxy LiteLLM tient en base.

Le vrai proxy garde ces objets dans PostgreSQL et les expose par
`POST /key/generate`. Ici, ils sont en mémoire : même forme, même règle
d'imputation, inspectable ligne à ligne.

CE QU'UNE CLÉ VIRTUELLE EST, ET N'EST PAS

Ce n'est pas un alias de la clé du fournisseur. C'est une **identité** :
révocable seule, budgétée seule, et qui ne donne accès à rien d'autre qu'au
proxy. Une application qui la perd fait perdre son budget à son équipe, pas
la clé Anthropic de l'entreprise.

LA RÈGLE QU'ON RATE

Le budget se vérifie **avant** l'appel et s'impute **après**. Entre les deux,
le coût n'est pas encore connu — un appel peut donc dépasser le plafond de
son propre coût. C'est un choix, pas un bug : refuser sur une estimation
refuserait des appels légitimes. `depassement_possible()` chiffre l'écart.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


class BudgetDepasse(Exception):
    pass


class CleInconnue(Exception):
    pass


class ModeleInterdit(Exception):
    """Distinct de BudgetDepasse, et ce n'est pas un detail.

    Un modele absent de la liste d'une cle ne sera JAMAIS autorise : c'est un
    403. Un budget epuise le sera a la prochaine periode : c'est un 429, avec
    ce que cela implique cote client — reessayer plus tard a un sens dans un
    cas, aucun dans l'autre.
    """


@dataclass
class CleVirtuelle:
    """La forme de ce que rend `POST /key/generate`."""

    cle: str
    equipe: str
    budget_max: float                 # en dollars, comme LiteLLM
    duree_budget: int = 30 * 86_400   # « budget_duration: 30d »
    modeles: tuple[str, ...] = ()     # vide = tous les alias du proxy
    rpm: int | None = None
    depense: float = 0.0
    appels: int = 0
    debut_periode: float = field(default_factory=time.time)
    horodatages: list[float] = field(default_factory=list)
    revoquee: bool = False

    @property
    def reste(self) -> float:
        return max(0.0, self.budget_max - self.depense)


class Registre:
    """Les clés du proxy, et l'imputation."""

    def __init__(self, maintenant=time.time) -> None:
        self.cles: dict[str, CleVirtuelle] = {}
        self._maintenant = maintenant

    # -- administration (la clé maître) -----------------------------

    def generer(self, equipe: str, budget_max: float, **options) -> CleVirtuelle:
        cle = CleVirtuelle(cle=f"sk-{equipe}-{len(self.cles) + 1:03d}",
                           equipe=equipe, budget_max=budget_max, **options)
        cle.debut_periode = self._maintenant()
        self.cles[cle.cle] = cle
        return cle

    def revoquer(self, cle: str) -> None:
        self.cles[cle].revoquee = True

    # -- le chemin d'un appel ---------------------------------------

    def autoriser(self, cle: str, alias: str) -> CleVirtuelle:
        """AVANT l'appel. Lève si quoi que ce soit s'y oppose."""
        # TODO : refuser (1) une cle inconnue ou revoquee — CleInconnue ; (2) un alias hors de la liste de la cle — ModeleInterdit, qui rendra 403 car il ne passera JAMAIS ; (3) un budget epuise — BudgetDepasse, qui rendra 429 car il repassera a la periode suivante ; (4) un depassement de rpm sur la minute glissante. Ne rien imputer ici : le cout n'est pas encore connu. Sept tests le verifient.
        return self.cles[cle]

    def imputer(self, cle: str, cout: float) -> CleVirtuelle:
        """APRÈS l'appel, quand le coût est connu."""
        virtuelle = self.cles[cle]
        virtuelle.depense += cout
        virtuelle.appels += 1
        virtuelle.horodatages.append(self._maintenant())
        return virtuelle

    # -- interne ----------------------------------------------------

    def _peut_etre_nouvelle_periode(self, cle: CleVirtuelle) -> None:
        if self._maintenant() - cle.debut_periode >= cle.duree_budget:
            cle.depense = 0.0
            cle.debut_periode = self._maintenant()

    def _dans_la_minute(self, cle: CleVirtuelle) -> int:
        limite = self._maintenant() - 60
        cle.horodatages = [h for h in cle.horodatages if h > limite]
        return len(cle.horodatages)

    # -- ce que le tableau de bord lit ------------------------------

    def par_equipe(self) -> dict[str, dict]:
        resume: dict[str, dict] = {}
        for cle in self.cles.values():
            ligne = resume.setdefault(cle.equipe,
                                      {"depense": 0.0, "budget": 0.0,
                                       "appels": 0, "cles": 0})
            ligne["depense"] += cle.depense
            ligne["budget"] += cle.budget_max
            ligne["appels"] += cle.appels
            ligne["cles"] += 1
        return resume


def depassement_possible(cle: CleVirtuelle, cout_max_par_appel: float) -> float:
    """De combien un budget peut etre depasse, au pire.

    Le contrôle est fait avant l'appel, l'imputation après : le dernier appel
    autorisé peut coûter n'importe quoi. Le dépassement maximal est donc le
    coût du plus cher des appels possibles — pas zéro, et pas l'infini.
    """
    return cout_max_par_appel if cle.reste > 0 else 0.0
