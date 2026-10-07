"""Ce que le projet doit garantir.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import pytest

from jobportal.corpus import corpus
from jobportal.hnsw import PetitMondeNavigable, exact
from jobportal.mesures import rappel
from jobportal.qdrant import chercher, client_prepare
from jobportal.vecteurs import (cosinus, euclidienne, normaliser,
                                produit_scalaire, relation_cosinus_l2, vectoriser)

REQUETES = ["Kubernetes a Lyon", "poste senior Kafka", "React a Bordeaux",
            "machine learning teletravail", "securite applicative Paris"]


@pytest.fixture(scope="module")
def base():
    offres = corpus()
    return offres, [vectoriser(o["titre"]) for o in offres]


# ---------------------------------------------------------------- vecteurs

def test_la_vectorisation_est_reproductible():
    """blake2b et non hash() : la fonction native est randomisee d'une
    execution a l'autre, et un index construit hier ne correspondrait plus
    aux requetes d'aujourd'hui."""
    assert vectoriser("Lead Kubernetes — Lyon") == vectoriser("Lead Kubernetes — Lyon")


def test_les_vecteurs_sont_normalises():
    v = vectoriser("Architecte Terraform cloud — Lille")
    assert math.isclose(math.sqrt(sum(x * x for x in v)), 1.0, abs_tol=1e-9)


def test_la_relation_cosinus_l2_tient():
    """||a - b||² = 2 - 2·cos, sur des vecteurs normalises. Si cette identite
    tombe, c'est que les vecteurs ne sont plus normalises — et tout le
    chapitre 1 devient faux."""
    a, b = vectoriser("Lead Kubernetes — Lyon"), vectoriser("Expert Kubernetes — Lyon")
    _, l2_calculee = relation_cosinus_l2(a, b)
    assert math.isclose(l2_calculee, euclidienne(a, b), abs_tol=1e-9)


def test_le_cosinus_ignore_la_longueur_le_produit_scalaire_non():
    a = vectoriser("Lead Kubernetes — Lyon")
    b = vectoriser("Expert Kubernetes — Lyon")
    gonfle = [x * 5 for x in b]
    assert math.isclose(cosinus(a, b), cosinus(a, gonfle), abs_tol=1e-9)
    assert produit_scalaire(a, gonfle) > produit_scalaire(a, b) * 4


def test_le_cosinus_monte_la_l2_descend():
    """Les deux sens opposes : les confondre ne plante pas, cela rend
    simplement les pires resultats en premier."""
    a = vectoriser("Lead Kubernetes — Lyon")
    proche = vectoriser("Expert Kubernetes — Lyon")
    loin = vectoriser("Developpeur React TypeScript — Bordeaux")
    assert cosinus(a, proche) > cosinus(a, loin)
    assert euclidienne(a, proche) < euclidienne(a, loin)


# ------------------------------------------------------------- index approche

def test_l_index_approche_rate_des_resultats(base):
    """Ce n'est pas un bug, c'est le contrat. Si ce test echouait, c'est que
    l'index n'approche rien — et qu'il coute donc autant que l'exact."""
    offres, vs = base
    index = PetitMondeNavigable(m=4, ef_construct=16)
    for v, o in zip(vs, offres):
        index.ajouter(v, o)
    r = rappel(index, vs, offres, [vectoriser(q) for q in REQUETES], k=5, ef=8)
    assert r.rappel < 1.0
    assert r.comparaisons < len(offres) / 2, "il doit etre moins cher que l'exact"


def test_plus_de_ef_donne_plus_de_rappel(base):
    offres, vs = base
    index = PetitMondeNavigable(m=8, ef_construct=32)
    for v, o in zip(vs, offres):
        index.ajouter(v, o)
    qs = [vectoriser(q) for q in REQUETES]
    petit = rappel(index, vs, offres, qs, k=5, ef=8)
    grand = rappel(index, vs, offres, qs, k=5, ef=64)
    assert grand.rappel >= petit.rappel
    assert grand.comparaisons > petit.comparaisons, "le rappel se paie"


def test_la_recherche_exacte_est_la_reference(base):
    offres, vs = base
    q = vectoriser("Lead Kubernetes — Lyon")
    premier = exact(vs, offres, q, 1)[0][1]
    assert premier["titre"] == "Lead Kubernetes — Lyon"


def test_le_graphe_est_bidirectionnel(base):
    """Sans l'arete de retour, un noeud insere tard n'est atteignable depuis
    nulle part. Symptome : un rappel qui s'effondre sur les DERNIERS
    documents inseres, et sur eux seulement."""
    offres, vs = base
    index = PetitMondeNavigable(m=8, ef_construct=32)
    for v, o in zip(vs[:100], offres[:100]):
        index.ajouter(v, o)
    dernier = 99
    assert any(dernier in index.voisins[i] for i in range(99)), \
        "le dernier insere n'est atteignable depuis aucun autre noeud"


# ------------------------------------------------------------------ qdrant

@pytest.fixture(scope="module")
def client():
    return client_prepare()


def test_qdrant_trouve_le_plus_proche(client):
    assert chercher(client, "Kubernetes a Lyon", 1)[0]["titre"] == "Lead Kubernetes — Lyon"


def test_le_filtre_restreint_vraiment_la_population(client):
    for r in chercher(client, "Kubernetes a Lyon", 5, ville="Nantes"):
        assert r["ville"] == "Nantes"


def test_le_filtre_rend_bien_le_nombre_demande(client):
    """Le piege du post-filtrage : l'index remonte ses k meilleurs, le filtre
    en elimine la quasi-totalite, et l'on rend deux resultats au lieu de cinq.
    Qdrant pousse le filtre DANS le parcours — ce test le verifie."""
    assert len(chercher(client, "machine learning", 5, ville="Paris", senior=True)) == 5


def test_deux_filtres_se_combinent(client):
    for r in chercher(client, "machine learning", 5, ville="Paris", senior=True):
        assert r["ville"] == "Paris" and r["senior"] is True
