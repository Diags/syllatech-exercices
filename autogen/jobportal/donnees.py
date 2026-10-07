"""La base du job portal — le `db` que les extraits du cours appellent.

Les vidéos ecrivent `await db.query(mot_cle, ville)` sans jamais montrer `db`.
Le voici, et en ASYNCHRONE : c'est ainsi que le cours l'appelle, et AutoGen
est asynchrone de bout en bout.
"""

from __future__ import annotations

import asyncio
import json
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
LATENCE = 0.001     # sans elle, « async » ne se distingue pas de « sync »


def _base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:", check_same_thread=False)
    cx.row_factory = sqlite3.Row
    cx.execute("CREATE TABLE offres (id TEXT, titre TEXT, ville TEXT, "
               "contrat TEXT, salaire INTEGER, competences TEXT)")
    alea = random.Random(13)
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


async def query(mot_cle: str, ville: str = "") -> list[dict]:
    await asyncio.sleep(LATENCE)
    sql = "SELECT * FROM offres WHERE (titre LIKE ? OR competences LIKE ?)"
    params = [f"%{mot_cle}%", f"%{mot_cle}%"]
    if ville:
        sql += " AND ville = ?"
        params.append(ville)
    return [dict(r) for r in BASE.execute(sql + " LIMIT 12", params)]


# --------------------------------------------------------------- les outils
# Un outil AutoGen est une fonction ANNOTEE, rien de plus. La docstring devient
# la description envoyee au modele, les annotations deviennent le schema.

async def rechercher_offres(mot_cle: str, ville: str = "") -> str:
    """Recherche les offres du portail syllatech par mot-cle, et par ville."""
    offres = await query(mot_cle, ville)
    return json.dumps([f"{o['titre']} — {o['contrat']}, {o['salaire'] // 1000}k"
                       for o in offres], ensure_ascii=False)


async def salaire_du_marche(mot_cle: str) -> str:
    """Rend le salaire median constate pour un metier ou une competence."""
    offres = await query(mot_cle)
    salaires = sorted(o["salaire"] for o in offres)
    if not salaires:
        return f"aucune offre pour {mot_cle}"
    return f"salaire median {mot_cle} : {salaires[len(salaires) // 2] // 1000}k EUR"
