"""Qdrant, POUR DE VRAI — et sans Docker.

Le cours montre `QdrantClient("localhost", port=6333)`. Peu de gens ont un
Qdrant qui tourne en lisant un cours, et l'exemple reste donc lettre morte.

`QdrantClient(":memory:")` change tout : c'est le MEME client, la MEME API,
les memes objets `models.*`, en memoire. Tout ce qui suit est donc du vrai
code Qdrant, executable immediatement — seule la ligne de connexion change
quand vous passez a un serveur.
"""

from __future__ import annotations

from qdrant_client import QdrantClient, models

from .corpus import corpus
from .vecteurs import DIMENSION, vectoriser

COLLECTION = "offres"


def client_prepare() -> QdrantClient:
    """Cree la collection et y verse le corpus."""
    client = QdrantClient(":memory:")
    client.create_collection(
        COLLECTION,
        vectors_config=models.VectorParams(size=DIMENSION,
                                           distance=models.Distance.COSINE),
    )
    offres = corpus()
    client.upsert(COLLECTION, points=[
        models.PointStruct(id=o["id"], vector=vectoriser(o["titre"]), payload=o)
        for o in offres
    ])
    return client


def chercher(client: QdrantClient, texte: str, limite: int = 5,
             ville: str | None = None, senior: bool | None = None) -> list[dict]:
    """Recherche, avec filtrage optionnel sur la charge utile.

    LE POINT IMPORTANT DU CHAPITRE : ce filtre n'est pas un `WHERE` applique
    apres coup. Qdrant le pousse DANS le parcours de l'index — sinon, sur un
    filtre selectif, l'index remonterait ses k meilleurs, le filtre en
    eliminerait la quasi-totalite, et l'on rendrait deux resultats au lieu de
    cinq. C'est le piege classique du « post-filtrage » : il ne plante pas,
    il rend simplement moins de resultats que demande, en silence.
    """
    conditions = []
    if ville is not None:
        conditions.append(models.FieldCondition(key="ville",
                                                match=models.MatchValue(value=ville)))
    if senior is not None:
        conditions.append(models.FieldCondition(key="senior",
                                                match=models.MatchValue(value=senior)))

    reponse = client.query_points(
        COLLECTION,
        query=vectoriser(texte),
        query_filter=models.Filter(must=conditions) if conditions else None,
        limit=limite,
    )
    return [{"score": p.score, **p.payload} for p in reponse.points]
