"""La base du job portal — le `db` que les extraits du cours appellent.

Les vidéos ecrivent `db.query(mot_cle)` sans jamais montrer `db`. Le voici :
SQLite en memoire, deterministe, avec un vrai schema.
"""

from __future__ import annotations

import json
import random
import sqlite3

SCHEMA = """
CREATE TABLE offres (
    id TEXT PRIMARY KEY, titre TEXT, ville TEXT, contrat TEXT,
    salaire INTEGER, competences TEXT
);
"""

METIERS = {
    "Developpeur Python": ["Python", "FastAPI", "PostgreSQL"],
    "Ingenieur DevOps": ["Kubernetes", "Terraform", "CI/CD"],
    "Architecte cloud": ["AWS", "Terraform", "reseau"],
    "Developpeur Java": ["Java", "Spring", "JPA"],
    "Data scientist": ["Python", "pandas", "statistiques"],
    "Ingenieur MLOps": ["MLflow", "Kubernetes", "Python"],
}
VILLES = ["Lyon", "Paris", "Nantes", "Bordeaux", "Lille", "Toulouse"]


def ouvrir(graine: int = 4) -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:", check_same_thread=False)
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA)
    alea = random.Random(graine)
    lignes = []
    for n in range(120):
        metier = alea.choice(list(METIERS))
        ville = alea.choice(VILLES)
        lignes.append((f"off-{n:03d}", f"{metier} — {ville}", ville,
                       alea.choice(["CDI", "CDD", "Freelance"]),
                       alea.choice([38, 42, 45, 52, 58, 65]) * 1000,
                       ", ".join(METIERS[metier])))
    cx.executemany("INSERT INTO offres VALUES (?,?,?,?,?,?)", lignes)
    cx.commit()
    return cx


BASE = ouvrir()


def query(mot_cle: str, ville: str = "") -> list[dict]:
    sql = "SELECT * FROM offres WHERE (titre LIKE ? OR competences LIKE ?)"
    params = [f"%{mot_cle}%", f"%{mot_cle}%"]
    if ville:
        sql += " AND ville = ?"
        params.append(ville)
    return [dict(r) for r in BASE.execute(sql + " LIMIT 12", params)]


def salaire_median(mot_cle: str) -> int:
    salaires = sorted(o["salaire"] for o in query(mot_cle))
    return salaires[len(salaires) // 2] if salaires else 0


# --------------------------------------------------- les outils de l'agent
# Un outil Agno est une FONCTION ANNOTEE. La docstring devient la description
# envoyee au modele, les annotations deviennent le schema des arguments.

def rechercher_offres(mot_cle: str) -> str:
    """Recherche les offres d'emploi du job portal par mot-cle.

    Args:
        mot_cle: le metier ou la competence cherchee, par exemple « DevOps ».
    """
    return json.dumps([f"{o['titre']} — {o['contrat']}, {o['salaire'] // 1000}k"
                       for o in query(mot_cle)], ensure_ascii=False)


def salaire_du_marche(mot_cle: str) -> str:
    """Rend le salaire median constate pour un metier ou une competence.

    Args:
        mot_cle: le metier ou la competence, par exemple « Python ».
    """
    median = salaire_median(mot_cle)
    return (f"salaire median pour {mot_cle} : {median // 1000}k EUR"
            if median else f"aucune offre pour {mot_cle}")
