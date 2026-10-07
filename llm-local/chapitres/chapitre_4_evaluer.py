"""Chapitre 4 — Choisir et évaluer un modèle.

Lancez : uv run python chapitres/chapitre_4_evaluer.py
Il faut Ollama qui tourne, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M
"""

import ollama

from jobportal import assistant
from jobportal.console import ligne, titre
from jobportal.donnees import ANNONCES

client = ollama.Client()

titre(1, "Le banc : 12 annonces, 60 champs")
justes, total = assistant.evaluer(client, assistant.MODELE)
ligne(assistant.MODELE, f"{justes}/{total} champs justes")

titre(2, "La fenêtre de contexte : ce qui dépasse est coupé, sans erreur")
long_prompt = "\n\n".join(a["texte"] for a in ANNONCES * 12)  # les 12 annonces, 12 fois
lus = {}
for num_ctx in (None, 8192):
    options = {"num_predict": 1} | ({"num_ctx": num_ctx} if num_ctx else {})
    r = client.chat(model=assistant.MODELE, messages=[{"role": "user", "content": long_prompt}],
                    options=options)
    lus[num_ctx] = r.prompt_eval_count
    ligne(f"num_ctx {num_ctx or 'par défaut'}", f"{r.prompt_eval_count} jetons lus")
if lus[None] < lus[8192]:
    print(f"\n   Par défaut, {lus[8192] - lus[None]} jetons du prompt n'ont pas été lus, sans erreur.")
    print("   Fixez num_ctx d'après vos plus longs prompts.")
