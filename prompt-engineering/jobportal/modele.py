"""Un modèle-jouet, et pourquoi il n'est pas un trucage.

Le cours affirme qu'un prompt mieux construit donne de meilleurs résultats.
Le démontrer demande un modèle — et donc une clé d'API, que ce projet refuse
d'exiger (voir exemples/README.md).

La solution n'est pas de simuler la conclusion. C'est de construire un
**vrai** classifieur minuscule, dont la qualité dépend réellement du prompt :

  · il LIT les exemples few-shot écrits dans le prompt et s'en sert comme
    base de comparaison. Sans exemples, il n'a rien pour décider et devine ;
  · il HONORE une consigne de raisonnement pas à pas, en exposant les indices
    qu'il a trouvés avant de conclure ;
  · il REFUSE de répondre quand le prompt lui interdit d'inventer et que le
    contexte fourni ne contient rien d'utile.

Le mécanisme est donc authentique, à petite échelle : améliorer le prompt
améliore vraiment le score, parce que le prompt porte vraiment l'information.
Ce que ce modèle NE fait pas : comprendre. Il compare des mots. Les chiffres
de ce projet valent pour la méthode, pas comme mesure d'un vrai LLM.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def plat(texte: str) -> set[str]:
    """Les mots d'un texte, sans accents ni ponctuation, en minuscules."""
    sans = unicodedata.normalize("NFD", texte)
    sans = "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()
    return {m for m in re.findall(r"[a-z]{3,}", sans)}


# Les mots vides ne discriminent rien : les garder noierait le signal.
VIDES = plat("le la les un une des du de et ou mais donc car ni or que qui "
             "pour par avec sans dans sur sous chez est sont ete etre avoir "
             "plus moins tres trop peu apres avant pendant feedback sentiment")


@dataclass
class Reponse:
    texte: str
    # Le raisonnement EXPOSE, et seulement s'il a été demandé (chapitre 3).
    raisonnement: list[str] = field(default_factory=list)
    # Pourquoi le modèle n'a pas su décider. C'est une trace pour VOUS, pas
    # une réponse pour l'utilisateur : confondre les deux donnerait un
    # « raisonnement » qui apparaît alors que personne ne l'a demandé.
    diagnostic: str = ""
    refus: bool = False


class ModeleJouet:
    """Classe un texte d'après les exemples trouvés DANS le prompt."""

    def __init__(self, nom: str = "jouet-1") -> None:
        self.nom = nom
        self.appels = 0

    # ---------------------------------------------------------------- lecture

    @staticmethod
    def exemples_du_prompt(prompt: str) -> list[tuple[str, str]]:
        """Extrait les couples (texte, étiquette) écrits en few-shot.

        Le format reconnu est celui du cours :

            Feedback: "…"
            Sentiment: POSITIF
        """
        couples = []
        motif = re.compile(r'Feedback\s*:\s*"([^"]+)"\s*\n\s*Sentiment\s*:\s*([A-ZÉÈÀÇ]+)')
        for m in motif.finditer(prompt):
            couples.append((m.group(1), m.group(2)))
        return couples

    @staticmethod
    def demande_un_raisonnement(prompt: str) -> bool:
        return bool(re.search(r"étape par étape|pas à pas|raisonne", prompt, re.IGNORECASE))

    @staticmethod
    def interdit_d_inventer(prompt: str) -> tuple[bool, str]:
        """Rend (ancré, phrase de refus) si le prompt impose de s'en tenir au
        contexte. La phrase exacte est extraite du prompt : c'est elle que le
        modèle devra rendre mot pour mot."""
        if not re.search(r"UNIQUEMENT|uniquement à partir", prompt):
            return False, ""
        m = re.search(r'réponds?\s+exactement\s*:?\s*"([^"]+)"', prompt, re.IGNORECASE)
        return True, (m.group(1) if m else "Information non disponible.")

    # ---------------------------------------------------------------- décision

    def repondre(self, prompt: str, entree: str, contexte: str = "") -> Reponse:
        self.appels += 1
        ancre, phrase_refus = self.interdit_d_inventer(prompt)
        if ancre:
            # Ancré : on ne répond que si le contexte porte l'information.
            communs = plat(entree) & plat(contexte) - VIDES
            if not communs:
                return Reponse(texte=phrase_refus, refus=True)

        exemples = self.exemples_du_prompt(prompt)
        if not exemples:
            # Sans exemple, rien ne dit ce qu'on attend : le modèle devine.
            # C'est exactement ce que le chapitre 2 veut faire constater.
            return Reponse(texte="MITIGÉ", diagnostic="aucun exemple dans le prompt")

        mots = plat(entree) - VIDES
        scores: dict[str, float] = {}
        indices: list[str] = []
        for texte, etiquette in exemples:
            partages = mots & (plat(texte) - VIDES)
            if partages:
                scores[etiquette] = scores.get(etiquette, 0) + len(partages)
                indices.append(f"« {texte[:34]}… » → {etiquette} (mots partagés : "
                               f"{', '.join(sorted(partages))})")

        if not scores:
            return Reponse(texte="MITIGÉ", diagnostic="aucun mot commun avec les exemples")

        gagnante = max(scores, key=lambda e: scores[e])
        return Reponse(texte=gagnante,
                       raisonnement=indices if self.demande_un_raisonnement(prompt) else [])


def modele() -> ModeleJouet:
    return ModeleJouet()
