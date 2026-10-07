"""La base documentaire — de vrais documents, pas des phrases.

Un corpus de six phrases ne montre rien : tout tient dans un seul morceau, le
decoupage n'a pas d'effet, et la recherche trouve toujours. Il faut des
documents assez longs pour etre coupes, et assez proches pour se confondre.

D'ou ces fiches : meme structure, vocabulaire partage, et quelques pieges
volontaires — deux villes, deux niveaux de seniorite, un terme qui n'apparait
que dans une seule fiche.
"""

from __future__ import annotations

DOCUMENTS: dict[str, str] = {
    "jp-001": """## Developpeur Java / Spring Boot — Clauger, Lyon

### Le poste
Vous rejoignez l'equipe plateforme industrielle a Lyon, en CDI. Vous concevez
et maintenez les services metier qui pilotent les installations froid de nos
clients industriels. L'equipe compte huit personnes.

### Stack
Java 21, Spring Boot 4, PostgreSQL, Kafka. Deploiement sur Kubernetes interne.
Les tests sont ecrits avant le code, et la couverture est suivie.

### Profil
Trois ans d'experience minimum sur Spring. La connaissance de Kafka est un
plus, elle s'apprend chez nous. Anglais technique lu.

### Remuneration
Non communiquee a ce stade, discutee en premier entretien.
""",

    "jp-002": """## Ingenieur IA — agents LLM, syllatech, teletravail

### Le poste
Vous construisez des agents outilles : serveurs MCP, pipelines RAG, evaluation
systematique. Le poste est en teletravail complet, en CDI.

### Stack
Python 3.13, LangGraph, MCP, Qdrant. Evaluation avec un jeu de test maison,
seuil de non-regression en integration continue.

### Profil
Vous avez deja mis un agent en production, et vous savez pourquoi il a echoue
la premiere fois. La curiosite compte plus que l'anciennete.

### Remuneration
Non communiquee a ce stade.
""",

    "jp-003": """## Data engineer — Soteck, Nantes

### Le poste
En CDD de dix-huit mois, vous industrialisez les pipelines de donnees de la
production a Nantes. Les traitements tournent la nuit et doivent etre finis
avant six heures.

### Stack
Python, SQL, Airflow, dbt. Entrepot sur BigQuery.

### Profil
Deux ans d'experience. Le sens de l'astreinte : quand un pipeline casse a
quatre heures du matin, quelqu'un doit savoir quoi faire.

### Remuneration
Non communiquee a ce stade.
""",

    "jp-004": """## Developpeur front React — Europlast, Bordeaux

### Le poste
Vous reprenez l'interface du portail client, a Bordeaux, en CDI.
L'accessibilite n'est pas une option : le portail est utilise par des agents
en atelier, parfois en gants, sur des ecrans de mauvaise qualite.

### Stack
React, TypeScript, Vite. Tests d'accessibilite automatises sur chaque page.

### Profil
Trois ans de React. Une vraie experience de l'accessibilite, pas seulement
la connaissance du mot.

### Remuneration
Non communiquee a ce stade.
""",

    "jp-005": """## SRE / plateforme Kubernetes — Clauger, Lyon

### Le poste
Vous operez la plateforme interne et son socle d'observabilite, a Lyon, en
CDI. C'est un poste senior : vous serez le recours quand la production tombe.

### Stack
Kubernetes, Terraform, Prometheus, Grafana, OpenTelemetry. Tout est decrit en
code, rien ne se fait a la main dans la console.

### Profil
Cinq ans minimum, dont deux sur Kubernetes en production. L'astreinte est
partagee entre quatre personnes.

### Remuneration
Non communiquee a ce stade.
""",
}

TITRES = {i: d.splitlines()[0].removeprefix("## ") for i, d in DOCUMENTS.items()}
