"""Chapitre 6 — RAG ou fine-tuning ?

Lancez : uv run python chapitres/chapitre_6_rag_ou_finetuning.py
Il faut Ollama qui tourne, et : ollama pull qwen2.5:1.5b-instruct-q4_K_M ; ollama pull bge-m3
Le fine-tuning se rejoue à part (une vingtaine de minutes sur processeur) :
    uv run --extra finetune python finetuning/entrainer.py
    uv run --extra finetune python finetuning/evaluer.py
"""

import json
import pathlib

import ollama

from jobportal import assistant
from jobportal.console import ligne, titre
from jobportal.donnees import OFFRES

client = ollama.Client()

titre(1, "RAG : donner au modèle les bonnes offres, au moment de la question")
index = assistant.indexer(client, OFFRES)
question = "Je cherche un poste de développeur Java expérimenté dans la région lyonnaise"
ligne("offres trouvées", [o["reference"] for o in assistant.rechercher(client, question, OFFRES, index)])
print("  ", assistant.repondre_avec_rag(client, question, OFFRES, index))

titre(2, "Fine-tuning : apprendre au modèle une tâche, une fois pour toutes")
racine = pathlib.Path(__file__).parents[1] / "finetuning"
journal = json.loads((racine / "adaptateur" / "journal.json").read_text(encoding="utf-8"))
resultats = json.loads((racine / "resultats.json").read_text(encoding="utf-8"))
ligne("modèle de base", journal["base"])
ligne("exemples d'entraînement", journal["exemples"])
ligne("paramètres entraînés", f"{journal['parametres_entraines']:,} sur {journal['parametres_total']:,}"
      .replace(",", " "))
ligne("durée, sur processeur", f"{journal['duree_s'] // 60} min {journal['duree_s'] % 60:02d} s")
ligne("taille de l'adaptateur", f"{journal['taille_adaptateur_mo']} Mo")
for etape in ("avant", "apres"):
    r = resultats[etape]
    ligne(f"banc, {etape} fine-tuning", f"{r['champs_justes']}/{r['champs_total']} champs justes, "
          f"{r['json_invalides']} JSON invalide(s)")
