"""Chapitre 4 — Tool Runner et sorties structurées.

Lancez : uv run python chapitres/chapitre_4_tool_runner.py
"""

from jobportal import assistant
from jobportal.console import json_court, ligne, titre
from jobportal.fausse_api import FausseAPI, appel_outil, texte

api = FausseAPI()

titre(1, "Le schéma, tiré de la signature et de la docstring")
api.repondre(appel_outil("t1", "compter_candidatures", {"reference": "OFF-103"}), stop="tool_use")
api.repondre(texte("OFF-103 a reçu 21 candidatures."))
print("  ", assistant.avec_tool_runner(api.client(), "Combien de candidatures pour OFF-103 ?"))
ligne("appels à l'API, boucle comprise", len(api.requetes))
outil = api.requetes[0].corps["tools"][1]
ligne("outil envoyé", json_court(outil, 300))

titre(2, "Une sortie typée, validée par Pydantic")
api.requetes.clear()
api.repondre(texte('{"titre": "Ingénieur IA", "ville": "Lyon", "contrat": "CDI", '
                   '"competences": ["Python", "RAG"], "teletravail": false}'))
fiche = assistant.extraire_fiche(api.client(), "Ingénieur IA à Lyon, en CDI. Python et RAG. Sur site.")
ligne("objet obtenu", repr(fiche))
ligne("format envoyé", json_court(api.requetes[0].corps["output_config"], 200))
