"""Chapitre 5 — Servir en production : Ollama, et ce que vLLM change.

Lancez : uv run python chapitres/chapitre_5_production.py
Il faut Ollama qui tourne, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M
Les mesures en parallèle viennent de mesures/resultats.json (mesures/mesurer.py).
"""

import datetime
import json
import pathlib

from jobportal import assistant
from jobportal.console import ligne, titre

client = assistant.client_de_production()

titre(1, "keep_alive : combien de temps le modèle reste en mémoire")
assistant.demander_en_production(client, "Bonjour")
charge = next(m for m in client.ps().models if m.model == assistant.MODELE)
reste = charge.expires_at - datetime.datetime.now(charge.expires_at.tzinfo)
ligne(assistant.MODELE, f"reste en mémoire encore {reste.total_seconds() / 60:.0f} min")

titre(2, "Requêtes simultanées : tout dépend d'OLLAMA_NUM_PARALLEL")
resultats = json.loads((pathlib.Path(__file__).parents[1] / "mesures" / "resultats.json")
                       .read_text(encoding="utf-8"))
for reglage, p in resultats["parallele"].items():
    print(f"\n   {reglage}")
    ligne("4 requêtes l'une après l'autre", f"{p['sequentiel_s']} s, {p['sequentiel_jetons_par_s']} jetons/s")
    ligne("4 requêtes en même temps", f"{p['simultane_s']} s, {p['simultane_jetons_par_s']} jetons/s")
    ligne("arrivée de chaque réponse", ", ".join(f"{t} s" for t in p["simultane_arrivees_s"]))
print("\n   Réglé à 1, les réponses arrivent en escalier : elles ont fait la queue.")
