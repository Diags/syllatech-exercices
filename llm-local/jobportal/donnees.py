"""Les données du portail, et le banc d'annonces du cours.

Le modèle des offres reprend celui de l'application JobPortal (dépôt
job-portal-ui) : titre, entreprise, catégorie, ville, contrat, mode de travail
et fourchette de salaire.

ANNONCES est le banc de qualité : des annonces rédigées librement, comme un
recruteur les colle dans le portail, chacune avec la fiche qu'un modèle doit
en extraire. Les formulations varient exprès (« 52 à 62 k€ », « télétravail
complet », « mission en indépendant ») : c'est ce qui sépare un modèle d'un
autre, et une quantization d'une autre.
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

CONTRATS = ["CDI", "CDD", "Freelance", "Stage", "Alternance"]
MODES = ["sur site", "hybride", "à distance"]
CHAMPS = ["ville", "contrat", "mode", "salaire_min", "salaire_max"]


def _annonce(texte, ville, contrat, mode, salaire_min, salaire_max):
    return {"texte": texte, "attendu": {"ville": ville, "contrat": contrat, "mode": mode,
                                        "salaire_min": salaire_min, "salaire_max": salaire_max}}


ANNONCES = [
    _annonce("Nordeau recrute un développeur Java senior en CDI à Lyon. Deux jours de "
             "télétravail par semaine. Salaire : 52 000 à 62 000 € brut annuel.",
             "Lyon", "CDI", "hybride", 52000, 62000),
    _annonce("Poste d'ingénieur DevOps chez Cumulus, siège à Paris mais 100 % télétravail. "
             "Contrat à durée indéterminée, rémunération entre 55 et 68 k€.",
             "Paris", "CDI", "à distance", 55000, 68000),
    _annonce("Lumen cherche son ingénieur IA pour son laboratoire de Lyon, présence sur "
             "place obligatoire. CDI. Fourchette : 58-72 K€ bruts/an.",
             "Lyon", "CDI", "sur site", 58000, 72000),
    _annonce("Mission en indépendant pour un designer UX/UI, à réaliser entièrement à "
             "distance pour l'Atelier Vif (Nantes). Budget annuel équivalent 40 000 – 50 000 €.",
             "Nantes", "Freelance", "à distance", 40000, 50000),
    _annonce("CDD de 12 mois à Grenoble : développeur full stack Java et React. Organisation "
             "hybride, 3 jours au bureau. Entre 45 000 et 54 000 euros par an.",
             "Grenoble", "CDD", "hybride", 45000, 54000),
    _annonce("La Banque Rhône ouvre un poste d'analyste financier en contrat à durée "
             "indéterminée, au siège lyonnais, sans télétravail. 48 à 58 k€ brut.",
             "Lyon", "CDI", "sur site", 48000, 58000),
    _annonce("Stage de 6 mois en data engineering à Toulouse, sur site. Gratification "
             "mensuelle de 1 200 €, soit 14 400 € sur un an.",
             "Toulouse", "Stage", "sur site", 14400, 14400),
    _annonce("Alternance développeur web à Bordeaux (rythme 3 semaines entreprise / 1 semaine "
             "école), télétravail un jour par semaine. Rémunération annuelle de 15 000 à 18 000 €.",
             "Bordeaux", "Alternance", "hybride", 15000, 18000),
    _annonce("Freelance : architecte cloud pour une mission longue, client basé à Lille, "
             "travail 100 % remote. Équivalent annuel 85 000 – 95 000 €.",
             "Lille", "Freelance", "à distance", 85000, 95000),
    _annonce("Marseille — Product owner en CDI, présentiel complet dans nos locaux du Vieux-Port. "
             "Package de 50 k€ à 60 k€ par an.",
             "Marseille", "CDI", "sur site", 50000, 60000),
    _annonce("Rejoignez-nous à Rennes comme ingénieur QA en CDD (18 mois). Mode hybride, deux "
             "jours sur site. Salaire brut annuel entre 38 000 et 44 000 €.",
             "Rennes", "CDD", "hybride", 38000, 44000),
    _annonce("Strasbourg : data scientist en contrat à durée indéterminée, poste entièrement "
             "télétravaillable. 60 000 à 70 000 € par an selon expérience.",
             "Strasbourg", "CDI", "à distance", 60000, 70000),
]
