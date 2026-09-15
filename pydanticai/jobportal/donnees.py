"""La base du job portal — le `DatabaseConn` que le cours appelle sans le montrer.

Les extraits ecrivent `ctx.deps.db.offres(...)` et `ctx.deps.db.nom(...)`.
`DatabaseConn` n'est jamais defini, et sans lui rien ne s'execute. Le voici,
avec les memes methodes, et en **asynchrone** — parce que c'est ainsi que le
cours les appelle (`await ctx.deps.db.offres(...)`).
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass

METIERS = ["Developpeur Python", "Ingenieur DevOps", "Architecte cloud",
           "Developpeur Java", "Data scientist", "Ingenieur MLOps"]
VILLES = ["Lyon", "Paris", "Nantes", "Bordeaux", "Lille", "Toulouse"]


@dataclass
class Offre:
    id: int
    titre: str
    ville: str
    salaire: int
    active: bool

    def __str__(self) -> str:
        etat = "" if self.active else " (close)"
        return f"{self.titre} — {self.ville}, {self.salaire // 1000}k{etat}"


class DatabaseConn:
    """Une base en memoire, deterministe, avec une latence simulee.

    La latence n'est pas decorative : sans elle, `async` ne se distingue pas
    de `sync` et le chapitre 2 n'enseigne rien. Elle est volontairement
    minuscule (1 ms) pour ne pas ralentir les tests.
    """

    LATENCE = 0.001

    def __init__(self, graine: int = 3) -> None:
        alea = random.Random(graine)
        self.noms = {n: f"Candidat{n:02d}" for n in range(1, 21)}
        self._offres: dict[int, list[Offre]] = {}
        for candidat in self.noms:
            # De 1 a 6 : il FAUT des candidats peu actifs, sinon la branche
            # « renoncer » du graphe (chapitre 5) ne s'emprunte jamais et
            # le projet ne demontre pas ce qu'il annonce.
            combien = alea.randint(1, 6)
            self._offres[candidat] = [
                Offre(id=candidat * 100 + i,
                      titre=alea.choice(METIERS),
                      ville=alea.choice(VILLES),
                      salaire=alea.choice([38, 42, 45, 52, 58, 65]) * 1000,
                      active=alea.random() > 0.3)
                for i in range(combien)
            ]

    async def nom(self, candidat_id: int) -> str:
        await asyncio.sleep(self.LATENCE)
        if candidat_id not in self.noms:
            raise KeyError(f"aucun candidat {candidat_id}")
        return self.noms[candidat_id]

    async def offres(self, candidat_id: int, seulement_actives: bool = False) -> list[str]:
        await asyncio.sleep(self.LATENCE)
        offres = self._offres.get(candidat_id, [])
        if seulement_actives:
            offres = [o for o in offres if o.active]
        return [str(o) for o in offres]

    async def salaire_median(self, ville: str) -> int:
        await asyncio.sleep(self.LATENCE)
        salaires = sorted(o.salaire for liste in self._offres.values()
                          for o in liste if o.ville == ville)
        return salaires[len(salaires) // 2] if salaires else 0
