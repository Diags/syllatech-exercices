"""Chapitre 3 — Les outils : la boucle agentique.

Lancez : uv run python chapitres/chapitre_3_boucle_agentique.py
"""

from jobportal import assistant
from jobportal.console import json_court, ligne, titre
from jobportal.fausse_api import FausseAPI, appel_outil, texte

api = FausseAPI()

titre(1, "Deux outils demandés dans le même tour")
api.repondre(appel_outil("t1", "rechercher_offres", {"mot_cle": "java"}),
             appel_outil("t2", "compter_candidatures", {"reference": "OFF-101"}), stop="tool_use")
api.repondre(texte("Deux offres Java ; OFF-101 a reçu 12 candidatures."))
print("  ", assistant.boucle_agentique(api.client(), "Offres Java, et combien de candidatures pour la première ?"))
ligne("appels à l'API", len(api.requetes))
dernier = api.requetes[1].corps["messages"][-1]
ligne("dernier message renvoyé", f"rôle {dernier['role']}, {len(dernier['content'])} tool_result")
ligne("contenu", json_court(dernier["content"], 300))

titre(2, "Un outil qui échoue")
api.requetes.clear()
api.repondre(appel_outil("t1", "compter_candidatures", {"reference": "OFF-999"}), stop="tool_use")
api.repondre(texte("Je ne trouve pas d'offre OFF-999 sur le portail."))
print("  ", assistant.boucle_agentique(api.client(), "Candidatures pour OFF-999 ?"))
ligne("résultat renvoyé au modèle", json_court(api.requetes[1].corps["messages"][-1]["content"][0]))
print("\n   L'erreur repart au modèle en is_error : il peut corriger, au lieu que tout plante.")
