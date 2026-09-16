"""Le juge — et pourquoi celui-ci ne triche pas.

Le cours présente le « LLM-as-a-judge » : un second modèle note la réponse du
premier. Le principe est juste, mais il masque une question plus importante :
**que note-t-on, exactement ?**

Ce module implémente la partie qui n'a PAS besoin d'un LLM, et qui est
précisément la plus utile : l'**ancrage**. Une réponse est ancrée si ce
qu'elle affirme se retrouve dans les sources. C'est vérifiable mot à mot, donc
gratuit, instantané et reproductible — trois qualités qu'un juge LLM n'a pas.

La règle pratique que ce module incarne : **n'appelez un juge LLM que pour ce
qu'aucune règle ne sait juger.** Confier à un modèle la vérification d'une
égalité de chaînes coûte de l'argent et introduit du bruit.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


def mots(texte: str) -> set[str]:
    sans = unicodedata.normalize("NFD", texte)
    sans = "".join(c for c in sans if unicodedata.category(c) != "Mn").lower()
    return set(re.findall(r"[a-z0-9]{3,}", sans))


# Les mots de liaison se retrouvent partout : les compter gonflerait
# artificiellement le score d'ancrage de n'importe quelle phrase.
VIDES = mots("le la les un une des du de et ou mais donc dans sur pour par "
             "avec sans est sont cette ces qui que quoi competences poste offre")


@dataclass
class Verdict:
    note: int                # de 1 à 5, comme la grille du cours
    raison: str
    ancrage: float           # part des affirmations retrouvées dans les sources


def juger_ancrage(reponse: str, sources: list[str]) -> Verdict:
    """Note l'ancrage d'une réponse dans ses sources.

    La grille est celle du cours :
        5 = exacte, complète, fidèle aux sources
        3 = correcte mais incomplète
        1 = fausse ou hors-sujet
    """
    contenu = mots(reponse) - VIDES
    if not contenu:
        return Verdict(3, "réponse vide de contenu propre", 1.0)

    appui = set()
    for s in sources:
        appui |= mots(s)
    if not appui:
        # Pas de source : une réponse qui affirme quelque chose n'est donc
        # ancrée nulle part. Sauf si elle n'affirme rien — un refus.
        return Verdict(1, "aucune source pour appuyer la réponse", 0.0)

    ancrage = len(contenu & appui) / len(contenu)
    if ancrage >= 0.8:
        return Verdict(5, "chaque élément de la réponse figure dans les sources", ancrage)
    if ancrage >= 0.5:
        return Verdict(3, "une partie de la réponse ne vient pas des sources", ancrage)
    return Verdict(1, "l'essentiel de la réponse ne vient pas des sources", ancrage)


def est_un_refus(reponse: str) -> bool:
    """Un refus n'a pas à être ancré : il n'affirme rien sur le monde.
    Ne pas le distinguer ferait chuter le score de l'agent le plus honnête —
    l'exact contraire de ce qu'on veut encourager."""
    return bool(re.match(r"(information non disponible|je ne peux pas)", reponse.strip(),
                         re.IGNORECASE))
