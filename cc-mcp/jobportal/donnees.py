"""La base du job portal — le chaînon que les extraits du cours appellent.

Les vidéos écrivent `db.query("select * from offres where ...")`. `db` n'est
jamais montré, et sans lui rien ne s'exécute. Le voici : une base en mémoire,
avec un vrai schéma interrogeable, un jeu de données déterministe, et des
requêtes qui ressemblent à du SQL parce que c'est ce que le cours enseigne.

Aucun PostgreSQL à installer. Le jour où vous en branchez un, seules les trois
fonctions du bas changent — la forme des outils MCP, elle, ne bouge pas.
"""

from __future__ import annotations

import random
import sqlite3

SCHEMA = """
CREATE TABLE offres (
    id          TEXT PRIMARY KEY,
    titre       TEXT NOT NULL,
    ville       TEXT NOT NULL,
    contrat     TEXT NOT NULL,
    salaire_min INTEGER,
    publiee_le  TEXT NOT NULL
);
CREATE TABLE candidatures (
    id        TEXT PRIMARY KEY,
    offre_id  TEXT NOT NULL REFERENCES offres(id),
    candidat  TEXT NOT NULL,
    statut    TEXT NOT NULL,
    deposee_le TEXT NOT NULL
);
"""

METIERS = ["Developpeur Python", "Ingenieur donnees", "Architecte cloud",
           "Developpeur Java", "SRE", "Data scientist", "Developpeur front",
           "Ingenieur MLOps", "Administrateur Kubernetes", "Analyste securite"]
VILLES = ["Lyon", "Paris", "Nantes", "Bordeaux", "Lille", "Toulouse"]
CONTRATS = ["CDI", "CDD", "Freelance"]
STATUTS = ["recue", "en_cours", "entretien", "refusee", "acceptee"]

# Assez d'offres pour qu'une requete filtree rende des lignes : une
# demonstration qui rend un tableau vide passe pour cassee.
NB_OFFRES = 200
NB_CANDIDATURES = 700


def ouvrir(graine: int = 5) -> sqlite3.Connection:
    """Une base neuve, peuplée à l'identique à chaque appel.

    Déterministe : sinon les chiffres de ce projet changeraient d'une machine
    à l'autre, et aucune mesure ne serait vérifiable.
    """
    cx = sqlite3.connect(":memory:")
    cx.row_factory = sqlite3.Row
    cx.executescript(SCHEMA)
    alea = random.Random(graine)

    offres = []
    for n in range(NB_OFFRES):
        # La ville du titre est celle de la colonne : une base incoherente
        # apprend a douter des donnees plutot que du code.
        ville = alea.choice(VILLES)
        offres.append((
            f"off-{n:03d}",
            f"{alea.choice(METIERS)} — {ville}",
            ville,
            alea.choice(CONTRATS),
            alea.choice([38, 42, 45, 48, 52, 58, 65]) * 1000,
            f"2026-0{alea.randint(1, 9)}-{alea.randint(10, 28)}",
        ))
    cx.executemany("INSERT INTO offres VALUES (?, ?, ?, ?, ?, ?)", offres)

    candidatures = []
    for n in range(NB_CANDIDATURES):
        candidatures.append((
            f"cand-{n:03d}",
            f"off-{alea.randrange(NB_OFFRES):03d}",
            f"candidat{alea.randrange(60):02d}@exemple.fr",
            alea.choice(STATUTS),
            f"2026-0{alea.randint(1, 9)}-{alea.randint(10, 28)}",
        ))
    cx.executemany("INSERT INTO candidatures VALUES (?, ?, ?, ?, ?)", candidatures)
    cx.commit()
    return cx


BASE = ouvrir()


def query(sql: str, *parametres) -> list[dict]:
    return [dict(r) for r in BASE.execute(sql, parametres).fetchall()]


def query_one(sql: str, *parametres) -> dict | None:
    lignes = query(sql, *parametres)
    return lignes[0] if lignes else None


def executer(sql: str, *parametres) -> int:
    """Les écritures. Séparées des lectures VOLONTAIREMENT : c'est cette
    séparation qui rend la règle de permission du chapitre 4 possible."""
    curseur = BASE.execute(sql, parametres)
    BASE.commit()
    return curseur.rowcount


def schema_texte() -> str:
    lignes = []
    for table in ("offres", "candidatures"):
        lignes.append(f"{table} :")
        for col in BASE.execute(f"PRAGMA table_info({table})"):
            obligatoire = " NOT NULL" if col["notnull"] else ""
            lignes.append(f"  {col['name']:<12} {col['type']}{obligatoire}")
    return "\n".join(lignes)
