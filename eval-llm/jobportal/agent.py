"""L'agent qu'on évalue — celui dont on veut mesurer la qualité.

Un projet d'évaluation a besoin de quelque chose à évaluer. Plutôt qu'un vrai
LLM (et donc une clé d'API), voici un agent minuscule et **déterministe** :
il cherche dans les offres, et répond à partir de ce qu'il trouve.

Cela suffit — et c'est même mieux pour apprendre. Un agent déterministe rend
l'évaluation reproductible : quand le score bouge, c'est que le code a bougé,
pas que le modèle a eu une autre idée. On isole ainsi ce que le chapitre
enseigne, la MESURE, de ce qu'il n'enseigne pas, le hasard.

Trois versions sont fournies. Elles ne diffèrent pas par hasard : chacune
corrige un défaut que le jeu de test met en évidence.
"""

from __future__ import annotations

import re
import time
import unicodedata
from dataclasses import dataclass

from . import donnees


def plat(texte: str) -> str:
    sans = unicodedata.normalize("NFD", texte)
    return "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()


REFUS = "Information non disponible."
REFUS_POLI = "Je ne peux pas traiter cette demande."


@dataclass
class Sortie:
    texte: str
    sources: list[str]
    duree: float


class Agent:
    """v1 : répond toujours. v2 : sait dire qu'il ne sait pas.
    v3 : v2 + refuse les demandes hors rôle."""

    def __init__(self, version: str = "v3") -> None:
        self.version = version

    # ------------------------------------------------------------ recherche

    @staticmethod
    def _offres_pertinentes(question: str) -> list[dict]:
        mots = [m for m in re.findall(r"[\w-]{3,}", plat(question))]
        trouvees, vues = [], set()
        for mot in mots:
            for o in donnees.query(mot):
                if o["id"] not in vues:
                    vues.add(o["id"])
                    trouvees.append(o)
        return trouvees

    # -------------------------------------------------------------- réponse

    def repondre(self, question: str) -> Sortie:
        depart = time.perf_counter()
        texte, sources = self._composer(question)
        return Sortie(texte=texte, sources=sources, duree=time.perf_counter() - depart)

    def _composer(self, question: str) -> tuple[str, list[str]]:
        if self.version == "v3" and self._hors_role(question):
            return REFUS_POLI, []

        offres = self._offres_pertinentes(question)
        if not offres:
            if self.version == "v1":
                # Le défaut que le jeu de test doit faire apparaître : plutôt
                # que d'avouer son ignorance, v1 produit une phrase plausible.
                # C'est exactement le comportement qu'on veut détecter.
                return "Je n'ai pas trouvé d'offre, mais le marché est porteur.", []
            return REFUS, []

        principale = offres[0]
        detail = donnees.get_offre(principale["id"])
        return (f"{detail.splitlines()[0]} "
                f"Compétences : {', '.join(principale['competences'])}.",
                [principale["id"]])

    # ------------------------------------------------------------ hors rôle

    MOTIFS_HORS_ROLE = [
        r"ignore\s+(tes|les)\s+instructions",
        r"oublie\s+(tes|les)\s+(consignes|instructions|règles)",
        r"révèle|dis[- ]moi\s+(un|ton)\s+secret",
        r"system\s+prompt",
        r"agis\s+comme\s+si",
    ]

    @classmethod
    def _hors_role(cls, question: str) -> bool:
        q = plat(question)
        return any(re.search(plat(m), q) for m in cls.MOTIFS_HORS_ROLE)


def agent(version: str = "v3") -> Agent:
    return Agent(version)
