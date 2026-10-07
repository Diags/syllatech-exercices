"""Le service HTTP de l'assistant : ce qui est livré au client.

    uv run uvicorn jobportal.api:app --port 8000

- POST /question  {"question": "..."}  → la réponse, ses sources, sa trace ;
- GET  /sante                          → le service répond-il ? (sans Ollama)
- GET  /metriques                      → le résumé des dernières requêtes
Chaque requête laisse une ligne JSON dans le journal (JOURNAL, sinon la sortie standard).

La configuration passe par l'environnement : OLLAMA_HOST (le serveur Ollama),
MODELE (le modèle). L'index des offres se construit à la première question :
le service démarre même si Ollama n'est pas encore prêt.
"""

import os
from dataclasses import asdict

import ollama
from fastapi import FastAPI
from pydantic import BaseModel, Field

from jobportal import agent, securite
from jobportal.donnees import OFFRES
from jobportal.observabilite import Journal, resumer
from jobportal.recherche import Index


class Question(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class Reponse(BaseModel):
    reponse: str
    sources: list[str]
    trace: dict


def creer_application(client: ollama.Client | None = None, modele: str | None = None,
                      journal: Journal | None = None, index_pret: Index | None = None) -> FastAPI:
    client = client or ollama.Client(host=os.environ.get("OLLAMA_HOST"))
    modele = modele or os.environ.get("MODELE", agent.MODELE)
    journal = journal or Journal(os.environ.get("JOURNAL"))  # JOURNAL : un fichier ; sinon la sortie standard
    app = FastAPI(title="Assistant du portail d'emploi")
    etat = {"index": index_pret} if index_pret else {}

    def index() -> Index:
        if "index" not in etat:
            etat["index"] = Index(client, OFFRES)
        return etat["index"]

    @app.get("/sante")
    def sante() -> dict:
        return {"statut": "ok", "modele": modele}

    @app.post("/question", response_model=Reponse)
    def poser(q: Question) -> Reponse:
        texte, trace = securite.repondre_securise(client, index(), q.question, modele)
        journal.ecrire(trace, texte)
        publique = {k: v for k, v in asdict(trace).items() if not k.startswith("_")}
        return Reponse(reponse=texte, sources=trace.sources, trace=publique)

    @app.get("/metriques")
    def metriques() -> dict:
        return resumer(journal.recentes)

    return app


app = creer_application()
