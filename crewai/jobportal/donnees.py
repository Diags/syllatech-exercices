"""La base du job portal, et les outils CrewAI qui l'interrogent.

Les extraits du cours ecrivent `db.query(mot_cle)` sans jamais montrer `db`.
Le voici — et surtout, voici ce que `@tool` en fait.
"""

from __future__ import annotations

import json
import random
import sqlite3

from crewai.tools import tool

METIERS = {
    "Developpeur Python": ["Python", "FastAPI", "PostgreSQL"],
    "Ingenieur DevOps": ["Kubernetes", "Terraform", "CI/CD"],
    "Architecte cloud": ["AWS", "Terraform", "reseau"],
    "Developpeur Java": ["Java", "Spring", "JPA"],
    "Data scientist": ["Python", "pandas", "statistiques"],
    "Ingenieur MLOps": ["MLflow", "Kubernetes", "Python"],
}
VILLES = ["Lyon", "Paris", "Nantes", "Bordeaux", "Lille", "Toulouse"]


def _base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:", check_same_thread=False)
    cx.row_factory = sqlite3.Row
    cx.execute("CREATE TABLE offres (id TEXT, titre TEXT, ville TEXT, "
               "contrat TEXT, salaire INTEGER, competences TEXT)")
    alea = random.Random(9)
    lignes = []
    for n in range(150):
        metier, ville = alea.choice(list(METIERS)), alea.choice(VILLES)
        lignes.append((f"off-{n:03d}", f"{metier} — {ville}", ville,
                       alea.choice(["CDI", "CDD", "Freelance"]),
                       alea.choice([38, 42, 45, 52, 58, 65]) * 1000,
                       ", ".join(METIERS[metier])))
    cx.executemany("INSERT INTO offres VALUES (?,?,?,?,?,?)", lignes)
    cx.commit()
    return cx


BASE = _base()


def query(mot_cle: str) -> list[dict]:
    return [dict(r) for r in BASE.execute(
        "SELECT * FROM offres WHERE titre LIKE ? OR competences LIKE ? LIMIT 12",
        (f"%{mot_cle}%", f"%{mot_cle}%"))]


def salaire_median(mot_cle: str) -> int:
    salaires = sorted(o["salaire"] for o in query(mot_cle))
    return salaires[len(salaires) // 2] if salaires else 0


# --------------------------------------------------------------- les outils
# Un outil CrewAI est une fonction decoree. Le nom passe a @tool et la
# DOCSTRING sont ce que l'agent lit pour decider de l'appeler : ce sont les
# deux seuls elements qui remontent au modele.

@tool("Recherche d'offres internes")
def rechercher_offres(mot_cle: str) -> str:
    """Recherche les offres du portail par mot-cle ou par competence."""
    return json.dumps([f"{o['titre']} — {o['contrat']}, {o['salaire'] // 1000}k"
                       for o in query(mot_cle)], ensure_ascii=False)


@tool("Salaire median du marche")
def salaire_du_marche(mot_cle: str) -> str:
    """Rend le salaire median constate pour un metier ou une competence."""
    median = salaire_median(mot_cle)
    return (f"salaire median {mot_cle} : {median // 1000}k EUR" if median
            else f"aucune offre pour {mot_cle}")
