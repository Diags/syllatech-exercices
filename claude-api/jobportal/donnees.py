"""Les offres du portail.

Le modèle reprend celui de l'application JobPortal (dépôt job-portal-ui) :
un titre, une entreprise, une catégorie, une ville, un type de contrat, un
mode de travail et une fourchette de salaire. Ici en mémoire, pour que le
cours tourne sans base de données.
"""

OFFRES = [
    {"reference": "OFF-101", "titre": "Développeur Java senior", "entreprise": "Nordeau",
     "categorie": "Technologie", "ville": "Lyon", "contrat": "CDI", "mode": "hybride",
     "salaire_min": 52000, "salaire_max": 62000},
    {"reference": "OFF-102", "titre": "Ingénieur DevOps", "entreprise": "Cumulus",
     "categorie": "Technologie", "ville": "Paris", "contrat": "CDI", "mode": "à distance",
     "salaire_min": 55000, "salaire_max": 68000},
    {"reference": "OFF-103", "titre": "Ingénieur IA", "entreprise": "Lumen",
     "categorie": "Technologie", "ville": "Lyon", "contrat": "CDI", "mode": "sur site",
     "salaire_min": 58000, "salaire_max": 72000},
    {"reference": "OFF-104", "titre": "Designer UX/UI", "entreprise": "Atelier Vif",
     "categorie": "Design", "ville": "Nantes", "contrat": "Freelance", "mode": "à distance",
     "salaire_min": 40000, "salaire_max": 50000},
    {"reference": "OFF-105", "titre": "Développeur full stack Java et React", "entreprise": "Nordeau",
     "categorie": "Technologie", "ville": "Grenoble", "contrat": "CDD", "mode": "hybride",
     "salaire_min": 45000, "salaire_max": 54000},
    {"reference": "OFF-106", "titre": "Analyste financier", "entreprise": "Banque Rhône",
     "categorie": "Finance", "ville": "Lyon", "contrat": "CDI", "mode": "sur site",
     "salaire_min": 48000, "salaire_max": 58000},
]

CANDIDATURES = {"OFF-101": 12, "OFF-102": 7, "OFF-103": 21, "OFF-104": 4, "OFF-105": 9, "OFF-106": 3}


def rechercher(mot_cle: str) -> list[dict]:
    """Les offres dont le titre, l'entreprise ou la ville contient le mot-clé."""
    mot = mot_cle.lower()
    return [
        {cle: offre[cle] for cle in ("reference", "titre", "ville", "contrat")}
        for offre in OFFRES
        if mot in offre["titre"].lower() or mot in offre["entreprise"].lower() or mot in offre["ville"].lower()
    ]


def compter_candidatures(reference: str) -> int:
    """Le nombre de candidatures d'une offre ; KeyError si la référence n'existe pas."""
    if reference not in CANDIDATURES:
        raise KeyError(f"aucune offre {reference}")
    return CANDIDATURES[reference]
