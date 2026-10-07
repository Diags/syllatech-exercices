"""Le service HTTP, mesuré sans Ollama : FastAPI, les vrais clients, un serveur simulé."""

import pytest
from fastapi.testclient import TestClient

from jobportal.api import creer_application
from jobportal.donnees import OFFRES
from jobportal.fausse_ollama import FausseOllama


@pytest.fixture
def serveur():
    return FausseOllama()


def test_la_sante_repond_sans_toucher_a_ollama(serveur):
    reponse = TestClient(creer_application(serveur.client())).get("/sante")
    assert reponse.status_code == 200 and reponse.json()["statut"] == "ok"
    assert serveur.requetes == []  # l'index n'est pas encore construit


def test_une_question_rend_la_reponse_ses_sources_et_sa_trace(serveur):
    serveur.vecteurs(*[[1.0, 0.0]] * len(OFFRES))  # l'index, à la première question
    serveur.repondre("L'offre Ingénieur IA a reçu 21 candidatures.", prompt_eval_count=700, eval_count=18)
    api = TestClient(creer_application(serveur.client()))
    corps = api.post("/question", json={"question": "Combien pour OFF-103 ?"}).json()
    assert corps["reponse"] == "L'offre Ingénieur IA (OFF-103) a reçu 21 candidatures."
    assert corps["sources"] == ["OFF-103"]
    assert corps["trace"]["jetons_entree"] == 700 and corps["trace"]["appels_modele"] == 1
    assert "_debut" not in corps["trace"]


def test_une_question_vide_ou_trop_longue_est_refusee_avant_le_modele(serveur):
    api = TestClient(creer_application(serveur.client()))
    assert api.post("/question", json={"question": ""}).status_code == 422
    assert api.post("/question", json={"question": "x" * 501}).status_code == 422
    assert serveur.requetes == []
