"""Garde-fous d'entrée et de sortie.

Deux barrières, et elles ne protègent pas de la même chose :

  ENTREE  ce qu'on refuse de traiter — injections, hors-sujet. Bloque AVANT
          de payer un appel au modèle. C'est aussi une économie.
  SORTIE  ce qu'on refuse de renvoyer — données personnelles, affirmations
          non ancrées. Bloque après, quand le mal est déjà fait côté modèle
          mais pas encore côté utilisateur.

Aucune des deux ne suffit seule : une injection passée en entrée peut produire
une sortie parfaitement propre, et une sortie fuitant un e-mail peut venir
d'une question anodine.
"""

from __future__ import annotations

import re

from .juge import juger_ancrage

INJECTIONS = [
    r"ignore\s+(tes|les)\s+instructions",
    r"oublie\s+(tes|les)\s+(consignes|instructions|règles)",
    r"system\s+prompt",
    r"agis\s+comme\s+si",
    r"réponds?\s+sans\s+(aucune\s+)?restriction",
]

# Volontairement simples et lisibles : un garde-fou qu'on ne sait pas relire
# est un garde-fou qu'on n'ose plus modifier.
# >>> depart: ecrire les motifs de donnees personnelles a bloquer en sortie. Les tests attendent au moins l'e-mail et le telephone francais.
#     PII = [
#         # (motif, nom lisible)
#     ]
PII = [
    (r"[\w.+-]+@[\w-]+\.[a-z]{2,}", "adresse e-mail"),
    (r"\b0[1-9](?:[ .-]?\d{2}){4}\b", "numéro de téléphone"),
    (r"\b\d{13}\b", "numéro de sécurité sociale"),
]
# <<<


def detecter_injection(entree: str) -> str:
    for motif in INJECTIONS:
        if re.search(motif, entree, re.IGNORECASE):
            return motif
    return ""


def detecter_pii(sortie: str) -> list[str]:
    return [nom for motif, nom in PII if re.search(motif, sortie)]


def non_ancre(sortie: str, sources: list[str], seuil: float = 0.5) -> bool:
    return juger_ancrage(sortie, sources).ancrage < seuil
