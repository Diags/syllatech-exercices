"""Chapitre 1 — Premier appel : la Messages API.

Lancez : uv run python chapitres/chapitre_1_premier_appel.py
Aucune clé d'API n'est nécessaire : le vrai SDK parle à une API simulée.
"""

from jobportal import assistant
from jobportal.console import json_court, ligne, titre
from jobportal.fausse_api import FausseAPI, reflexion, texte

api = FausseAPI()

titre(1, "Ce que le SDK envoie vraiment")
api.repondre(reflexion(), texte("Trois offres à Lyon : OFF-101, OFF-103 et OFF-106."))
print("  ", assistant.demander(api.client(), "Quelles offres à Lyon ?"))
ligne("requête", f"POST {api.requetes[0].chemin}")
ligne("corps", json_court(api.requetes[0].corps))

titre(2, "Le premier bloc n'est pas forcément du texte")
api.repondre(reflexion(), texte("Bonjour"))
reponse = api.client().messages.create(model=assistant.MODELE, max_tokens=16000,
                                       messages=[{"role": "user", "content": "Bonjour"}])
ligne("types des blocs reçus", [b.type for b in reponse.content])
try:
    reponse.content[0].text
except AttributeError as erreur:
    ligne("reponse.content[0].text", f"{type(erreur).__name__} : {erreur}")
ligne("texte filtré par type", repr(assistant.texte_de(reponse)))

titre(3, "L'API est sans état")
api.repondre(texte("Enchanté, Awa."))
api.repondre(texte("Vous vous appelez Awa."))
conversation = assistant.Conversation(api.client())
conversation.envoyer("Je m'appelle Awa.")
print("  ", conversation.envoyer("Comment je m'appelle ?"))
ligne("messages envoyés au second tour", len(api.requetes[-1].corps["messages"]))
print("\n   Chaque requête renvoie tout l'historique : c'est vous qui portez la mémoire.")
