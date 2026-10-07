"""La recherche sémantique sur les offres : des embeddings calculés en local.

Chaque offre devient un texte (titre, entreprise, lieu, contrat, mode et
description), puis un vecteur, avec bge-m3 servi par Ollama. Une question
devient un vecteur à son tour ; les offres les plus proches, au sens du
cosinus, sont celles qu'on donne au modèle.
"""

import math

import ollama

EMBEDDINGS = "bge-m3"


def texte_offre(o: dict) -> str:
    return (f"{o['titre']} chez {o['entreprise']}, {o['categorie']}, {o['contrat']} à {o['ville']}, "
            f"{o['mode']}. {o['description']}")


def cosinus(a: list[float], b: list[float]) -> float:
    produit = sum(x * y for x, y in zip(a, b))
    return produit / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


class Index:
    def __init__(self, client: ollama.Client, offres: list[dict]):
        self.client, self.offres = client, offres
        self.vecteurs = client.embed(model=EMBEDDINGS, input=[texte_offre(o) for o in offres]).embeddings

    def chercher(self, requete: str, k: int = 5) -> list[dict]:
        vecteur = self.client.embed(model=EMBEDDINGS, input=requete).embeddings[0]
        scores = [cosinus(vecteur, v) for v in self.vecteurs]
        ordre = sorted(range(len(self.offres)), key=lambda i: scores[i], reverse=True)
        return [self.offres[i] for i in ordre[:k]]
