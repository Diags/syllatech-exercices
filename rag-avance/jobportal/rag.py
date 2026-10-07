"""Le pipeline complet — naif contre avance, pour voir la difference.

La reponse est composee sans modele : on cite les passages retrouves. C'est
volontaire. Ce que le cours enseigne, c'est la RECUPERATION ; la generation
n'est que la derniere etape, et elle ne peut pas rattraper un contexte qui ne
contient pas la reponse.
"""

from __future__ import annotations

from dataclasses import dataclass

from .decoupe import decouper
from .recherche import Index, Morceau, hybride
from .rerank import reclasser


@dataclass
class Reponse:
    texte: str
    passages: list[Morceau]
    sources: list[str]


class Rag:
    def __init__(self, mode: str = "avance") -> None:
        self.mode = mode
        self.index = Index(decouper())

    def recuperer(self, question: str, k: int = 5) -> list[Morceau]:
        if self.mode == "naif":
            # Naif : un seul moteur, pas de fusion, pas de reclassement.
            return self.index.vectorielle(question, k)
        # Avance : on recupere large, on fusionne, puis on trie fin.
        candidats = hybride(self.index, question, 10)
        return reclasser(question, candidats, k)

    def repondre(self, question: str, k: int = 5) -> Reponse:
        passages = self.recuperer(question, k)
        if not passages:
            return Reponse("Information non disponible.", [], [])
        sources = sorted({m.metadonnees["source"] for m in passages})
        texte = "\n".join(f"[{m.id}] {m.texte.strip().splitlines()[0]}" for m in passages[:3])
        return Reponse(texte, passages, sources)
