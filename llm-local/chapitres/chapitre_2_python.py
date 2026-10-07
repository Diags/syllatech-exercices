"""Chapitre 2 — Ollama depuis Python : flux, sortie structurée, API compatible OpenAI.

Lancez : uv run python chapitres/chapitre_2_python.py
Il faut Ollama qui tourne, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M
⚠️ Ce script crée un modèle « assistant-portail » dans votre Ollama (quelques
kilooctets : il réutilise les fichiers du modèle de base). Pour le retirer :
ollama rm assistant-portail
"""

import ollama

from jobportal import assistant
from jobportal.console import json_court, ligne, titre
from jobportal.donnees import ANNONCES
from jobportal.fiche import extraire_fiche

client = ollama.Client()

titre(1, "La réponse en flux")
morceaux = []
texte = assistant.demander_en_flux(client, "Donne trois conseils pour un CV, une ligne chacun.",
                                   afficher=morceaux.append)
print("  ", texte)
ligne("morceaux reçus", len(morceaux))

titre(2, "Une sortie structurée : le schéma contraint la réponse")
fiche, reponse = extraire_fiche(client, assistant.MODELE, ANNONCES[1]["texte"])
ligne("annonce", ANNONCES[1]["texte"][:60] + " …")
ligne("fiche extraite", json_court(fiche))
ligne("fiche attendue", json_court(ANNONCES[1]["attendu"]))

titre(3, "Le même modèle, par l'API compatible OpenAI")
print("  ", assistant.demander_via_openai(assistant.client_compatible_openai(), "Qu'est-ce qu'un CDD ?"))

titre(4, "Un modèle à soi, sans entraînement")
assistant.creer_assistant(client)
ligne("modèle créé", "assistant-portail")
detail = client.show("assistant-portail")
for instruction in detail.modelfile.splitlines():  # le Modelfile qu'Ollama a reconstitué
    if instruction.startswith(("FROM", "SYSTEM", "PARAMETER")):
        ligne("Modelfile", instruction[:70])
print("  ", client.chat(model="assistant-portail",
                        messages=[{"role": "user", "content": "Bonjour, que fais-tu ?"}]).message.content)
