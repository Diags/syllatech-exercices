"""Les données du portail, chez le client de la mission.

Le modèle des offres reprend celui de l'application JobPortal (dépôt
job-portal-ui) : titre, entreprise, catégorie, ville, contrat, mode de travail
et fourchette de salaire, plus une courte description — c'est elle que le RAG
cherche. Vingt-quatre offres : assez pour qu'une recherche ait à choisir, et
pour qu'un modèle sans données se trompe de façon visible.
"""


def _offre(n, titre, entreprise, categorie, ville, contrat, mode, smin, smax, description):
    return {"reference": f"OFF-{n}", "titre": titre, "entreprise": entreprise, "categorie": categorie,
            "ville": ville, "contrat": contrat, "mode": mode, "salaire_min": smin, "salaire_max": smax,
            "description": description}


OFFRES = [
    _offre(101, "Développeur Java senior", "Nordeau", "Technologie", "Lyon", "CDI", "hybride", 52000, 62000,
           "Spring Boot, microservices et Kafka pour la facturation d'un fournisseur d'énergie."),
    _offre(102, "Ingénieur DevOps", "Cumulus", "Technologie", "Paris", "CDI", "à distance", 55000, 68000,
           "Kubernetes, Terraform et GitLab CI pour une plateforme d'hébergement."),
    _offre(103, "Ingénieur IA", "Lumen", "Technologie", "Lyon", "CDI", "sur site", 58000, 72000,
           "Modèles de langage, RAG et évaluation pour un assistant de recherche documentaire."),
    _offre(104, "Designer UX/UI", "Atelier Vif", "Design", "Nantes", "Freelance", "à distance", 40000, 50000,
           "Refonte de parcours mobiles, Figma et tests utilisateurs."),
    _offre(105, "Développeur full stack Java et React", "Nordeau", "Technologie", "Grenoble", "CDD", "hybride",
           45000, 54000, "Java, React et PostgreSQL pour un outil interne de planification."),
    _offre(106, "Analyste financier", "Banque Rhône", "Finance", "Lyon", "CDI", "sur site", 48000, 58000,
           "Analyse de crédits aux entreprises, modélisation sous Excel et Python."),
    _offre(107, "Data engineer", "Cumulus", "Données", "Paris", "CDI", "à distance", 54000, 66000,
           "Pipelines Spark et dbt, entrepôt de données sur Snowflake."),
    _offre(108, "Data scientist", "Lumen", "Données", "Strasbourg", "CDI", "à distance", 60000, 70000,
           "Prévision de la demande, séries temporelles et apprentissage automatique."),
    _offre(109, "Développeur Python", "Galène", "Technologie", "Toulouse", "CDI", "hybride", 44000, 54000,
           "API FastAPI et traitement de données pour l'aéronautique."),
    _offre(110, "Alternant développeur web", "Halo", "Technologie", "Bordeaux", "Alternance", "hybride",
           15000, 18000, "JavaScript, Vue.js et accessibilité, en rythme trois semaines et une semaine."),
    _offre(111, "Stagiaire data analyst", "Iris", "Données", "Toulouse", "Stage", "sur site", 14400, 14400,
           "Tableaux de bord Power BI et SQL pour une direction commerciale."),
    _offre(112, "Architecte cloud", "Fjord", "Technologie", "Lille", "Freelance", "à distance", 85000, 95000,
           "Migration vers AWS, architecture de référence et sécurité des comptes."),
    _offre(113, "Product owner", "Jade", "Produit", "Marseille", "CDI", "sur site", 50000, 60000,
           "Pilotage d'une application de réservation, backlog et ateliers utilisateurs."),
    _offre(114, "Ingénieur QA", "Écume", "Technologie", "Rennes", "CDD", "hybride", 38000, 44000,
           "Tests automatisés Playwright et JUnit, campagne de non-régression."),
    _offre(115, "Développeur Java", "Boréal", "Technologie", "Lyon", "CDD", "à distance", 42000, 50000,
           "Java 21 et Spring pour une application de gestion des stocks."),
    _offre(116, "Chef de projet digital", "Dune", "Produit", "Nantes", "CDI", "hybride", 46000, 56000,
           "Lancement de sites e-commerce, coordination des équipes et des prestataires."),
    _offre(117, "Administrateur système Linux", "Cobalt", "Technologie", "Grenoble", "CDI", "sur site",
           40000, 48000, "Serveurs Linux, supervision et automatisation avec Ansible."),
    _offre(118, "Alternant data analyst", "Arcadie", "Données", "Lyon", "Alternance", "sur site",
           14000, 17000, "SQL, Python et visualisation pour une équipe marketing."),
    _offre(119, "Comptable", "Banque Rhône", "Finance", "Marseille", "CDI", "hybride", 36000, 42000,
           "Comptabilité générale, clôtures mensuelles et déclarations fiscales."),
    _offre(120, "Ingénieur sécurité", "Fjord", "Technologie", "Paris", "CDI", "hybride", 62000, 76000,
           "Tests d'intrusion, durcissement et réponse aux incidents."),
    _offre(121, "Développeur mobile", "Halo", "Technologie", "Bordeaux", "CDI", "hybride", 45000, 55000,
           "Applications Kotlin et Swift, publication sur les magasins d'applications."),
    _offre(122, "Consultant SAP", "Galène", "Conseil", "Toulouse", "Freelance", "sur site", 70000, 85000,
           "Déploiement SAP S/4HANA, module finance, chez un industriel."),
    _offre(123, "Responsable marketing", "Jade", "Marketing", "Marseille", "CDI", "hybride", 52000, 64000,
           "Stratégie d'acquisition, campagnes payantes et marketing de contenu."),
    _offre(124, "Stagiaire développeur Java", "Boréal", "Technologie", "Lyon", "Stage", "hybride", 13200, 13200,
           "Stage de six mois sur une application Spring Boot, encadré par un développeur senior."),
]

CANDIDATURES = {
    "OFF-101": 12, "OFF-102": 7, "OFF-103": 21, "OFF-104": 4, "OFF-105": 9, "OFF-106": 3,
    "OFF-107": 15, "OFF-108": 18, "OFF-109": 6, "OFF-110": 11, "OFF-111": 8, "OFF-112": 2,
    "OFF-113": 5, "OFF-114": 4, "OFF-115": 10, "OFF-116": 6, "OFF-117": 3, "OFF-118": 9,
    "OFF-119": 2, "OFF-120": 13, "OFF-121": 7, "OFF-122": 1, "OFF-123": 5, "OFF-124": 14,
}

PAR_REFERENCE = {o["reference"]: o for o in OFFRES}
