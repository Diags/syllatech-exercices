"""Trois versions du même prompt, et un jeu de test pour les départager.

C'est le cœur du chapitre 6 : **un prompt se mesure**. Tant qu'on l'évalue
« au doigt mouillé », on tourne en rond ; avec un jeu de test et un score, on
sait si la version 3 vaut mieux que la 2, ou si on a seulement changé d'avis.

Les trois versions ne sont pas trois écritures au hasard. Chacune ajoute
exactement une des techniques du cours, pour que l'écart de score soit
attribuable.
"""

from __future__ import annotations

# ---------------------------------------------------------------- v1 : nu

V1 = """Classe le sentiment du feedback candidat.

Feedback: "{entree}"
Sentiment:"""


# ------------------------------------------------- v2 : v1 + exemples (ch. 2)

V2 = """Classe le sentiment du feedback candidat.

Exemples :
Feedback: "Process trop long mais recruteur au top"
Sentiment: MITIGÉ

Feedback: "Aucun retour après 3 semaines, décevant"
Sentiment: NÉGATIF

Feedback: "Entretien clair, offre reçue en 2 jours !"
Sentiment: POSITIF

Feedback: "{entree}"
Sentiment:"""


# --------------------------- v3 : v2 + exemples couvrants + raisonnement (ch. 3)

V3 = """Classe le sentiment du feedback candidat.

Exemples :
Feedback: "Process trop long mais recruteur au top"
Sentiment: MITIGÉ

Feedback: "Aucun retour après 3 semaines, décevant"
Sentiment: NÉGATIF

Feedback: "Entretien clair, offre reçue en 2 jours !"
Sentiment: POSITIF

Feedback: "Salaire correct, ambiance froide"
Sentiment: MITIGÉ

Feedback: "Recruteur injoignable, aucune explication au refus"
Sentiment: NÉGATIF

Feedback: "Équipe accueillante, mission passionnante, très content"
Sentiment: POSITIF

Raisonne étape par étape, puis conclus.

Feedback: "{entree}"
Sentiment:"""


VERSIONS = {"v1": V1, "v2": V2, "v3": V3}


# ------------------------------------------------------ le prompt ancré (ch. 6)

ANCRE = """Réponds UNIQUEMENT à partir du CONTEXTE.
Si le contexte ne contient pas la réponse, réponds
exactement : "Information non disponible."

CONTEXTE :
{contexte}

QUESTION : {entree}"""


# --------------------------------------------------------------- jeu de test

# Un jeu de test se relit : chaque cas dit ce qu'on attend et pourquoi il est
# là. Un jeu sans intention est un jeu qu'on n'ose plus modifier.
JEU_DE_TEST: list[dict[str, str]] = [
    {"entree": "Recruteur au top, process clair", "attendu": "POSITIF",
     "pourquoi": "vocabulaire directement présent dans les exemples"},
    {"entree": "Aucun retour, décevant", "attendu": "NÉGATIF",
     "pourquoi": "idem, côté négatif"},
    {"entree": "Ambiance froide mais salaire correct", "attendu": "MITIGÉ",
     "pourquoi": "deux signaux opposés — v2 ne le couvre pas, v3 si"},
    {"entree": "Équipe accueillante, mission passionnante", "attendu": "POSITIF",
     "pourquoi": "formulation absente de v2, présente dans v3"},
    {"entree": "Recruteur injoignable, aucune explication", "attendu": "NÉGATIF",
     "pourquoi": "idem"},
    {"entree": "Offre reçue en 2 jours, entretien clair", "attendu": "POSITIF",
     "pourquoi": "reformulation d'un exemple : doit passer dès v2"},
]
