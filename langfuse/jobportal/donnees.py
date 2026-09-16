"""La base du job portal, et un modele factice — pour que tout tourne sans cle."""

from __future__ import annotations

import random
import re
import sqlite3

METIERS = {
    "Developpeur Python": ["Python", "FastAPI", "PostgreSQL"],
    "Ingenieur DevOps": ["Kubernetes", "Terraform", "CI/CD"],
    "Architecte cloud": ["AWS", "Terraform", "reseau"],
    "Developpeur Java": ["Java", "Spring", "JPA"],
    "Data scientist": ["Python", "pandas", "statistiques"],
}
VILLES = ["Lyon", "Paris", "Nantes", "Bordeaux", "Lille", "Toulouse"]

# Le cout par million de tokens, en euros. Des ordres de grandeur : ils
# bougent, le rapport entre modeles beaucoup moins.
TARIFS = {
    "haiku": (0.25, 1.25),
    "sonnet": (3.00, 15.00),
    "opus": (15.00, 75.00),
}


def _base() -> sqlite3.Connection:
    cx = sqlite3.connect(":memory:", check_same_thread=False)
    cx.row_factory = sqlite3.Row
    cx.execute("CREATE TABLE offres (id TEXT, titre TEXT, ville TEXT, "
               "salaire INTEGER, competences TEXT)")
    alea = random.Random(31)
    lignes = []
    for n in range(120):
        metier, ville = alea.choice(list(METIERS)), alea.choice(VILLES)
        lignes.append((f"off-{n:03d}", f"{metier} — {ville}", ville,
                       alea.choice([38, 42, 45, 52, 58, 65]) * 1000,
                       ", ".join(METIERS[metier])))
    cx.executemany("INSERT INTO offres VALUES (?,?,?,?,?)", lignes)
    cx.commit()
    return cx


BASE = _base()


def query(mot_cle: str, combien: int = 4) -> list[str]:
    lignes = BASE.execute(
        "SELECT titre, salaire FROM offres WHERE titre LIKE ? OR competences LIKE ? "
        "LIMIT ?", (f"%{mot_cle}%", f"%{mot_cle}%", combien)).fetchall()
    return [f"{l['titre']} — {l['salaire'] // 1000}k" for l in lignes]


def mot_cle(texte: str) -> str:
    m = re.search(r"\b(DevOps|Python|Java|cloud|data|Kubernetes|AWS)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else "emploi"


def tokens(texte: str) -> int:
    return max(1, len(texte) // 4)


def cout(modele: str, entree: int, sortie: int) -> float:
    """Le cout d'un appel, en euros. C'est ce que Langfuse calcule cote serveur
    a partir de l'usage et de sa table de tarifs — ici, on le fait nous-memes
    pour que le chiffre soit verifiable."""
    e, s = TARIFS.get(modele, TARIFS["sonnet"])
    return (entree * e + sortie * s) / 1_000_000
