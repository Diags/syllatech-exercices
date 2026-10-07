"""Chapitre 2 — pgvector : le SQL, et ce qu'il implique vraiment.

⚠️ CE CHAPITRE N'EXECUTE PAS DE SQL. Il faudrait un PostgreSQL avec
l'extension vector, et ce projet doit tourner apres un « uv sync ». Le SQL
ci-dessous est celui du cours ; ce qui est EXECUTE, c'est la demonstration de
ce que les operateurs signifient.

    uv run python chapitres/chapitre_2_pgvector.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.corpus import corpus                            # noqa: E402
from jobportal.vecteurs import (cosinus, euclidienne,          # noqa: E402
                                produit_scalaire, vectoriser)

SCHEMA = """CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE docs (
  id        bigserial PRIMARY KEY,
  contenu   text,
  meta      jsonb,
  embedding vector(1536)
);

CREATE INDEX ON docs USING hnsw (embedding vector_cosine_ops);"""

REQUETE = """SELECT contenu FROM docs
WHERE meta->>'ville' = 'Lyon'        -- filtre metadonnee
ORDER BY embedding <=> :q LIMIT 5;"""

OPERATEURS = {
    "<=>": ("distance cosinus", "1 - cosinus : PLUS PETIT est meilleur"),
    "<->": ("distance L2", "PLUS PETIT est meilleur"),
    "<#>": ("produit scalaire NEGATIF", "pgvector le renvoie negatif pour que "
            "PLUS PETIT reste meilleur"),
}


def main() -> None:
    console.utf8()
    print("Le schema du cours :\n")
    for l in SCHEMA.splitlines():
        print("   " + l)
    print("\nLa requete :\n")
    for l in REQUETE.splitlines():
        print("   " + l)

    print("\nLES TROIS OPERATEURS, ET LE PIEGE :\n")
    for op, (nom, sens) in OPERATEURS.items():
        print(f"   {op}   {nom:<26} {sens}")
    print("\n   Ils vont TOUS dans le meme sens : plus petit = meilleur. C'est")
    print("   voulu, pour que « ORDER BY ... LIMIT 5 » fonctionne sans plus.")
    print("   Mais le cosinus, lui, monte avec la ressemblance : d'ou le")
    print("   « 1 - cosinus ». Verifions sur de vrais vecteurs :\n")

    offres = corpus()
    base = vectoriser("Lead Kubernetes — Lyon")
    echantillon = [o for o in offres if o["titre"] in (
        "Expert Kubernetes — Lyon", "Lead Kubernetes — Nantes",
        "Developpeur React TypeScript — Bordeaux")]
    # Triées par <=>, comme le ferait « ORDER BY embedding <=> :q » : c'est
    # ainsi que l'accord des trois colonnes se voit d'un coup d'œil.
    lignes = []
    for o in echantillon:
        v = vectoriser(o["titre"])
        lignes.append((1 - cosinus(base, v), euclidienne(base, v),
                       -produit_scalaire(base, v), o["titre"]))
    print(f"   {'titre (ORDER BY <=>)':<44} {'<=>':>7} {'<->':>7} {'<#>':>8}")
    for d1, d2, d3, titre in sorted(lignes):
        print(f"   {titre:<44} {d1:>7.3f} {d2:>7.3f} {d3:>8.3f}")

    print("\n   Les trois colonnes classent dans le MEME ordre — parce que les")
    print("   vecteurs sont normalises (chapitre 1). Le choix de l'operateur")
    print("   ne devient une decision que s'ils ne le sont pas.")

    print("\nQUAND CHOISIR pgvector :")
    print("   · vous avez deja PostgreSQL, et moins d'un million de vecteurs ;")
    print("   · vos filtres sont des colonnes SQL, et vous voulez JOINDRE le")
    print("     resultat a vos autres tables — ce qu'aucune base vectorielle")
    print("     dediee ne fait bien ;")
    print("   · une seule base a sauvegarder, a surveiller, a mettre a jour.")
    print("\n   Cette derniere ligne pese plus qu'on ne croit : un composant")
    print("   d'infrastructure en moins vaut souvent mieux que dix pour cent")
    print("   de latence en moins.")


if __name__ == "__main__":
    main()
