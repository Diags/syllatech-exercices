"""Le métier du job portal — ce qui n'a rien à voir avec AgentCore.

Il est ici pour que l'agent réponde quelque chose. Le cours écrit
`agent = Agent(model="claude-sonnet-5")` ; remplacer `repondre` par cet appel
ne change rien au reste du projet, et c'est bien le sujet : **AgentCore
emballe l'entrypoint, pas le modèle.**
"""

from __future__ import annotations

from dataclasses import dataclass

CATALOGUE = [
    ("DevOps Senior", "Lyon", "CDI", 62),
    ("Developpeur Java", "Paris", "CDI", 55),
    ("Data Engineer", "Lyon", "CDI", 58),
    ("Developpeur Python", "Nantes", "freelance", 70),
    ("SRE", "Paris", "CDI", 65),
    ("Developpeur Java", "Lyon", "alternance", 24),
]


@dataclass
class Offre:
    titre: str
    ville: str
    contrat: str
    salaire_k: int

    def __str__(self) -> str:
        return (f"{self.titre} — {self.ville} ({self.contrat}, "
                f"{self.salaire_k} k EUR)")


def chercher(question: str) -> list[Offre]:
    mots = {m.lower() for m in question.replace(",", " ").split()}
    trouvees = [Offre(*ligne) for ligne in CATALOGUE
                if {ligne[1].lower(), ligne[2].lower()} & mots
                or any(m in ligne[0].lower() for m in mots)]
    return trouvees or [Offre(*ligne) for ligne in CATALOGUE[:2]]


def repondre(question: str) -> str:
    offres = chercher(question)
    return (f"{len(offres)} offre(s) pour « {question} » : "
            + " · ".join(str(o) for o in offres))
