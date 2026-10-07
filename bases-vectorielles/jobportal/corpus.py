"""Un corpus assez grand pour que l'approximation ait un sens.

Cinq documents ne montrent rien : un index approche les trouve tous. Il en
faut assez pour qu'un parcours glouton puisse se tromper — d'ou ces offres
generees, variees sur trois axes (metier, ville, technologie).
"""

from __future__ import annotations

import itertools

METIERS = ["Developpeur", "Ingenieur", "Architecte", "Consultant", "Lead",
           "Expert", "Technicien", "Analyste"]
TECHNOS = ["Java Spring", "Python data", "Kubernetes", "React TypeScript",
           "Terraform cloud", "Kafka streaming", "PostgreSQL", "machine learning",
           "securite applicative", "observabilite"]
VILLES = ["Lyon", "Nantes", "Bordeaux", "Paris", "Lille", "teletravail"]


def corpus() -> list[dict]:
    """480 offres, deterministes : meme corpus a chaque execution."""
    offres = []
    for n, (m, t, v) in enumerate(itertools.product(METIERS, TECHNOS, VILLES)):
        offres.append({
            "id": n,
            "titre": f"{m} {t} — {v}",
            "ville": v,
            "techno": t,
            "senior": m in ("Architecte", "Lead", "Expert"),
        })
    return offres
