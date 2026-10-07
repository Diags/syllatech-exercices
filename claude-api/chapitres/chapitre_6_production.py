"""Chapitre 6 — En production : repli, effort, limites.

Lancez : uv run python chapitres/chapitre_6_production.py
"""

from jobportal import assistant
from jobportal.console import ligne, titre
from jobportal.fausse_api import FausseAPI, texte

api = FausseAPI()

titre(1, "Ce que la requête de production emporte")
api.repondre(texte("Trois offres à Lyon."))
print("  ", assistant.demander_en_production(api.client(), "Offres à Lyon ?"))
requete = api.requetes[0]
ligne("chemin", requete.chemin)
ligne("en-tête anthropic-beta", requete.entetes["anthropic-beta"])
ligne("fallbacks", requete.corps["fallbacks"])
ligne("output_config", requete.corps["output_config"])

titre(2, "Un refus se traite, il ne se lit pas comme une réponse")
api.repondre(stop="refusal", stop_details={"type": "refusal", "category": "cyber", "explanation": None})
print("  ", assistant.demander_en_production(api.client(), "x"))
