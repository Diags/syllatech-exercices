"""Chapitre 1 — Pourquoi en local, et premier modèle.

Lancez : uv run python chapitres/chapitre_1_premier_modele.py
Il faut Ollama qui tourne, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M
"""

import ollama

from jobportal import assistant
from jobportal.console import ligne, titre

client = ollama.Client()

titre(1, "Les modèles présents sur cette machine")
for modele in client.list().models:
    ligne(modele.model, f"{modele.size / 1e6:.0f} Mo sur disque")

titre(2, "Première question, modèle déchargé : le chargement compte")
client.generate(model=assistant.MODELE, prompt="", keep_alive=0)  # décharge le modèle
froid = client.chat(model=assistant.MODELE, messages=[{"role": "user", "content": "Bonjour"}])
chaud = client.chat(model=assistant.MODELE, messages=[{"role": "user", "content": "Bonsoir"}])
ligne("chargement, première requête", f"{froid.load_duration / 1e9:.2f} s")
ligne("chargement, requête suivante", f"{chaud.load_duration / 1e9:.2f} s")

titre(3, "La réponse, et ce qu'elle a coûté")
reponse = client.chat(model=assistant.MODELE, messages=[
    {"role": "system", "content": assistant.SYSTEME},
    {"role": "user", "content": "Quelles questions poser avant de postuler à un CDI ?"}])
print("  ", reponse.message.content)
ligne("jetons générés", reponse.eval_count)
ligne("vitesse de génération", f"{reponse.eval_count / (reponse.eval_duration / 1e9):.1f} jetons/s")
print("\n   Rien n'est sorti de la machine : ni la question, ni la réponse.")
