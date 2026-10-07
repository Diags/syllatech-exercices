"""L'examen de certification : le mot qui tranche, rendu calculable.

CE QU'UN EXAMEN CLOUD EVALUE
----------------------------
Pas votre memoire : votre jugement. Les questions sont des mises en
situation ou **plusieurs reponses fonctionnent** et une seule est la
meilleure — selon un critere que l'enonce nomme, et qu'on lit trop vite :
« le plus economique », « le plus disponible », « le moins
d'administration », « le plus securise ».

CE QUE CE MODULE EN FAIT
------------------------
Il ne stocke pas « la bonne reponse ». Il decrit chaque option sur quatre
axes, et **calcule** la meilleure pour le critere demande. Consequence
directe, et c'est la mesure du chapitre 6 : la MEME situation, avec les
MEMES options, change de bonne reponse quand on change le mot qui tranche.

Un enonce qui ne contient aucun de ces mots n'a pas de meilleure reponse :
`detecter()` leve plutot que de deviner. C'est aussi vrai a l'examen —
quand rien ne tranche, c'est qu'on a mal lu.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

AXES = ("cout", "disponibilite", "securite", "administration")

# Le critere, l'axe qu'il optimise, et le sens de l'optimisation.
#
# ⚠️ « cout » et « administration » se MINIMISENT, « disponibilite » et
# « securite » se MAXIMISENT. C'est exactement ce que veut dire « le plus
# economique » contre « le plus disponible » — et c'est pourquoi les deux
# ne designent presque jamais la meme reponse.
CRITERES: dict[str, tuple[str, int]] = {
    "le plus economique": ("cout", -1),
    "le moins cher": ("cout", -1),
    "le plus disponible": ("disponibilite", +1),
    "le plus resilient": ("disponibilite", +1),
    "le plus securise": ("securite", +1),
    "le moins d'administration": ("administration", -1),
    "le moins de maintenance": ("administration", -1),
}


class ErreurExamen(Exception):
    """Un enonce sans mot qui tranche, un critere inconnu, une egalite."""


@dataclass(frozen=True)
class Option:
    """Une reponse possible — decrite, jamais jugee d'avance."""

    lettre: str
    texte: str
    cout: float                 # 0 = gratuit, 10 = tres cher
    disponibilite: float        # 0 = fragile, 10 = multi-region
    securite: float             # 0 = ouvert, 10 = verrouille
    administration: float       # 0 = rien a gerer, 10 = tout a gerer
    pourquoi: str = ""

    def note(self, axe: str) -> float:
        if axe not in AXES:
            raise ErreurExamen(f"axe inconnu : « {axe} »")
        return float(getattr(self, axe))


@dataclass
class Question:
    """Une situation, des options, et AUCUNE bonne reponse stockee."""

    domaine: str
    situation: str
    options: list[Option] = field(default_factory=list)

    def bonne_reponse(self, critere: str) -> Option:
        # TODO : classer les options sur l'axe du critere, et refuser une egalite
        return self.options[0]

    def classement(self, critere: str) -> list[Option]:
        axe, sens = _critere(critere)
        return sorted(self.options, key=lambda o: sens * o.note(axe),
                      reverse=True)

    def pourquoi_pas(self, critere: str) -> list[tuple[Option, str]]:
        """Pour chaque distracteur, ce qui le disqualifie SUR CE CRITERE."""
        axe, sens = _critere(critere)
        bonne = self.bonne_reponse(critere)
        raisons = []
        for option in self.options:
            if option is bonne:
                continue
            ecart = (option.note(axe) - bonne.note(axe)) * sens
            mot = "moins bien" if ecart < 0 else "a egalite"
            raisons.append((option, f"{axe} : {option.note(axe):g} contre "
                                    f"{bonne.note(axe):g} — {mot}"))
        return raisons


def _critere(critere: str) -> tuple[str, int]:
    if critere not in CRITERES:
        raise ErreurExamen(
            f"critere inconnu : « {critere} » — connus : {sorted(CRITERES)}")
    return CRITERES[critere]


# Ce qu'on cherche dans un enonce, quelle que soit sa tournure : « la
# solution LA PLUS economique », « le service qui demande LE MOINS
# d'administration », « l'architecture LA PLUS resiliente ».
_MARQUEURS: tuple[tuple[str, str], ...] = (
    # ⚠️ « le MOINS cher » optimise le cout ; « le PLUS cher » ne veut rien
    # dire a l'examen, et n'est donc pas un marqueur.
    (r"\b(?:le|la)\s+moins\s+(?:cher|couteus\w*|onereus\w*)",
     "le plus economique"),
    (r"\b(?:le|la)\s+plus\s+(?:economique|abordable)", "le plus economique"),
    (r"\bmoindre\s+cout", "le plus economique"),
    (r"\b(?:le|la)\s+plus\s+(?:disponible|robuste)", "le plus disponible"),
    (r"\bhaute\w*\s+disponibilit\w*", "le plus disponible"),
    (r"\b(?:le|la)\s+plus\s+resilient\w*", "le plus disponible"),
    (r"\b(?:le|la)\s+plus\s+(?:securis\w*|sur)\b", "le plus securise"),
    (r"\b(?:le|la)\s+moins\s+(?:d'administration|de\s+maintenance|"
     r"d'exploitation|d'operations)", "le moins d'administration"),
    (r"\bsans\s+(?:rien\s+)?administrer", "le moins d'administration"),
)


def detecter(enonce: str) -> str:
    """Le mot qui tranche, trouve dans l'enonce — ou une erreur.

    ⚠️ Un enonce sans mot qui tranche n'a pas de meilleure reponse. A
    l'examen, cela veut toujours dire qu'on a saute une ligne.
    """
    # TODO : trouver le mot qui tranche, et refuser un enonce qui n'en a pas
    return "le plus economique"


# ── passer l'examen ──────────────────────────────────────────────────────

@dataclass
class Reponse:
    question: Question
    critere: str
    choisie: str
    secondes: float = 0.0
    marquee: bool = False

    @property
    def juste(self) -> bool:
        return self.choisie == self.question.bonne_reponse(self.critere).lettre


@dataclass
class Copie:
    """Ce qu'un examen blanc rend — et il ne rend pas qu'une note."""

    reponses: list[Reponse] = field(default_factory=list)
    minutes_autorisees: float = 130.0

    @property
    def note(self) -> float:
        if not self.reponses:
            return 0.0
        return sum(1 for r in self.reponses if r.juste) / len(self.reponses)

    @property
    def secondes_utilisees(self) -> float:
        return sum(r.secondes for r in self.reponses)

    @property
    def secondes_par_question(self) -> float:
        return self.minutes_autorisees * 60 / max(1, len(self.reponses))

    @property
    def dans_les_temps(self) -> bool:
        return self.secondes_utilisees <= self.minutes_autorisees * 60

    def par_domaine(self) -> dict[str, tuple[int, int]]:
        """(justes, total) par domaine — le seul decoupage qui sert a reviser."""
        resultat: dict[str, tuple[int, int]] = {}
        for reponse in self.reponses:
            justes, total = resultat.get(reponse.question.domaine, (0, 0))
            resultat[reponse.question.domaine] = (
                justes + (1 if reponse.juste else 0), total + 1)
        return dict(sorted(resultat.items()))

    def a_revoir(self) -> list[str]:
        """⚠️ Le domaine le plus faible, pas la note globale.

        Une note de 72 % repartie en « 95 % partout sauf 20 % en reseau »
        et une note de 72 % uniforme demandent deux revisions opposees.
        """
        return [domaine for domaine, (justes, total) in self.par_domaine().items()
                if total and justes / total < 0.7]

    def chronophages(self, seuil: float = 2.0) -> list[Reponse]:
        """Les questions qui ont pris plus de `seuil` fois le temps moyen."""
        budget = self.secondes_par_question
        return [r for r in self.reponses if r.secondes > budget * seuil]


def corriger(copie: Copie) -> list[str]:
    """La correction utile : pourquoi la bonne est bonne, ET pourquoi les
    autres sont mauvaises."""
    lignes: list[str] = []
    for rang, reponse in enumerate(copie.reponses, 1):
        bonne = reponse.question.bonne_reponse(reponse.critere)
        marque = "✓" if reponse.juste else "✗"
        lignes.append(f"{marque} Q{rang} [{reponse.question.domaine}] "
                      f"critere : {reponse.critere}")
        lignes.append(f"    repondu {reponse.choisie}, attendu {bonne.lettre} "
                      f"— {bonne.texte}")
        if bonne.pourquoi:
            lignes.append(f"    pourquoi : {bonne.pourquoi}")
        for option, raison in reponse.question.pourquoi_pas(reponse.critere):
            lignes.append(f"    {option.lettre} non : {raison}")
    return lignes
