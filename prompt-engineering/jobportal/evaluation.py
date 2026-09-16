"""Le harnais : mesurer un prompt au lieu d'en discuter.

Trois lignes de principe, et tout le chapitre 6 tient dedans :
  1. un jeu de cas, avec la sortie attendue ;
  2. une fonction de validation, explicite ;
  3. un score, comparable d'une version à l'autre.

Ce qu'on gagne : on peut REGRESSER. Sans score, une « amélioration » de
prompt est une opinion ; avec, c'est un chiffre qui monte ou qui descend.
"""

from __future__ import annotations

from dataclasses import dataclass

from .modele import ModeleJouet


@dataclass
class Resultat:
    version: str
    reussis: int
    total: int
    echecs: list[tuple[str, str, str]]      # (entrée, attendu, obtenu)

    @property
    def taux(self) -> float:
        return self.reussis / self.total if self.total else 0.0


def evaluer(modele: ModeleJouet, version: str, gabarit: str,
            jeu: list[dict[str, str]]) -> Resultat:
    # >>> depart: soumettre chaque cas du jeu au gabarit, compter les réussites, et GARDER les échecs — un score sans la liste de ce qui a raté ne dit pas quoi corriger.
    #     reussis, echecs = 0, []
    #     return Resultat(version, reussis, len(jeu), echecs)
    reussis, echecs = 0, []
    for cas in jeu:
        obtenu = modele.repondre(gabarit.format(entree=cas["entree"]), cas["entree"]).texte
        if obtenu == cas["attendu"]:
            reussis += 1
        else:
            echecs.append((cas["entree"], cas["attendu"], obtenu))
    return Resultat(version, reussis, len(jeu), echecs)
    # <<<


def comparer(modele: ModeleJouet, versions: dict[str, str],
             jeu: list[dict[str, str]]) -> list[Resultat]:
    return [evaluer(modele, nom, gabarit, jeu) for nom, gabarit in versions.items()]
