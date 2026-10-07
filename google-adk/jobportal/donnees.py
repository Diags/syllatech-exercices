"""La base du job portal, et les outils ADK qui l'interrogent.

Un outil ADK est une FONCTION ANNOTEE avec une docstring au format Google. Le
cours insiste sur le `Returns: dict` — ce n'est pas une convention de style :
ADK serialise le retour tel quel vers le modele, et un dict nomme se relit,
la ou une chaine se devine.
"""

from __future__ import annotations

import random
import sqlite3

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
    alea = random.Random(21)
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


def query(mot_cle: str, ville: str = "") -> list[dict]:
    sql = "SELECT * FROM offres WHERE (titre LIKE ? OR competences LIKE ?)"
    params = [f"%{mot_cle}%", f"%{mot_cle}%"]
    if ville:
        sql += " AND ville = ?"
        params.append(ville)
    return [dict(r) for r in BASE.execute(sql + " LIMIT 10", params)]


# --------------------------------------------------------------- les outils

def rechercher_offres(mot_cle: str, ville: str) -> dict:
    """Recherche les offres d'emploi du portail syllatech.

    Args:
        mot_cle: le metier ou la competence recherchee (ex: "DevOps").
        ville: la ville souhaitee (ex: "Lyon").

    Returns:
        dict: « status » vaut « success » ou « error », et « offres » porte
        la liste des intitules trouves.
    """
    offres = query(mot_cle, ville)
    if not offres:
        return {"status": "error",
                "message": f"aucune offre {mot_cle} a {ville}"}
    return {"status": "success",
            "offres": [f"{o['titre']} — {o['contrat']}, {o['salaire'] // 1000}k"
                       for o in offres]}


def salaire_du_marche(mot_cle: str) -> dict:
    """Rend le salaire median constate pour un metier ou une competence.

    Args:
        mot_cle: le metier ou la competence (ex: "Python").

    Returns:
        dict: « status » et « median » en euros annuels.
    """
    salaires = sorted(o["salaire"] for o in query(mot_cle))
    if not salaires:
        return {"status": "error", "message": f"aucune offre pour {mot_cle}"}
    return {"status": "success", "median": salaires[len(salaires) // 2]}
