"""Chapitre 2 — Streaming, erreurs et nouvelles tentatives.

Lancez : uv run python chapitres/chapitre_2_flux_et_erreurs.py
"""

import anthropic

from jobportal import assistant
from jobportal.console import ligne, titre
from jobportal.fausse_api import FausseAPI, texte

api = FausseAPI()

titre(1, "Le flux, morceau par morceau")
api.repondre(texte("Trois offres correspondent : OFF-101, OFF-103 et OFF-106."))
print("   ", end="")
final = assistant.demander_en_flux(api.client(), "Offres à Lyon ?", afficher=lambda m: print(m, end="|", flush=True))
print()
ligne("message final reconstitué", repr(assistant.texte_de(final)))

titre(2, "Ce que le SDK réessaie tout seul")
for _ in range(3):
    api.echouer(429, "rate_limit_error")
api.requetes.clear()
try:
    assistant.demander(api.client(), "x")
except anthropic.RateLimitError:
    ligne("429 persistant : requêtes envoyées", len(api.requetes))

api.requetes.clear()
api.echouer(429, "rate_limit_error")
api.repondre(texte("ok"))
ligne("429 puis succès : réponse obtenue", repr(assistant.demander(api.client(), "x")))
ligne("requêtes envoyées", len(api.requetes))

api.requetes.clear()
api.echouer(400, "invalid_request_error")
try:
    assistant.demander(api.client(), "x")
except anthropic.BadRequestError:
    ligne("400 : requêtes envoyées", len(api.requetes))

titre(3, "Un gros max_tokens exige le flux")
api.requetes.clear()
try:
    api.client().messages.create(model=assistant.MODELE, max_tokens=128000,
                                 messages=[{"role": "user", "content": "x"}])
except ValueError as erreur:
    ligne("max_tokens=128000 sans flux", f"ValueError, {len(api.requetes)} requête envoyée")
    print("  ", str(erreur)[:110], "…")
