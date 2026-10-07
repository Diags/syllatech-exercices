"""Chapitre 5 — Prompt caching et coûts.

Lancez : uv run python chapitres/chapitre_5_cache_et_couts.py

Le cache se vérifie sur la vraie API, avec usage.cache_read_input_tokens.
Ici, on mesure ce qui se mesure sans elle : ce qui est envoyé, et si le
préfixe reste identique d'un appel à l'autre. Les coûts sont calculés à
partir des prix publiés d'Opus 5.5.
"""

from types import SimpleNamespace

from jobportal import assistant, donnees
from jobportal.console import ligne, titre
from jobportal.fausse_api import FausseAPI, texte

api = FausseAPI()

titre(1, "Un préfixe stable, ou pas")
api.repondre(texte("a"))
api.repondre(texte("b"))
assistant.demander_avec_cache(api.client(), "Offres à Lyon ?")
assistant.demander_avec_cache(api.client(), "Offres à Paris ?")
ligne("préfixe identique, CONSIGNES seules", api.requetes[0].corps["system"] == api.requetes[1].corps["system"])
api.requetes.clear()
api.repondre(texte("a"))
api.repondre(texte("b"))
assistant.demander_avec_horloge(api.client(), "Offres à Lyon ?")
import time; time.sleep(1.1)
assistant.demander_avec_horloge(api.client(), "Offres à Paris ?")
ligne("préfixe identique, heure en tête", api.requetes[0].corps["system"] == api.requetes[1].corps["system"])
print("   Une seule seconde d'écart change le préfixe : rien ne peut être relu en cache.")

titre(2, "Ce que coûte une question, aux prix d'Opus 5.5")
sans_cache = SimpleNamespace(input_tokens=2050, output_tokens=300,
                             cache_creation_input_tokens=0, cache_read_input_tokens=0)
ecriture = SimpleNamespace(input_tokens=50, output_tokens=300,
                           cache_creation_input_tokens=2000, cache_read_input_tokens=0)
lecture = SimpleNamespace(input_tokens=50, output_tokens=300,
                          cache_creation_input_tokens=0, cache_read_input_tokens=2000)
ligne("2 000 jetons de consignes, sans cache", f"{assistant.cout_en_dollars(sans_cache):.4f} $")
ligne("premier appel, écriture en cache", f"{assistant.cout_en_dollars(ecriture):.4f} $")
ligne("appels suivants, lecture en cache", f"{assistant.cout_en_dollars(lecture):.4f} $")
print("   Les 300 jetons de sortie restent le poste principal : le cache n'y touche pas.")

titre(3, "Un lot de requêtes, à moitié prix")
api.requetes.clear()
api.repondre_brut({"id": "msgbatch_001", "type": "message_batch", "processing_status": "in_progress",
                   "request_counts": {"processing": 6, "succeeded": 0, "errored": 0, "canceled": 0, "expired": 0},
                   "created_at": "2026-10-05T09:00:00Z", "expires_at": "2026-10-06T09:00:00Z",
                   "ended_at": None, "cancel_initiated_at": None, "archived_at": None, "results_url": None})
lot = assistant.resumer_en_lot(api.client(), donnees.OFFRES)
ligne("lot créé", f"{lot.id}, {lot.processing_status}")
ligne("custom_id envoyés", [r["custom_id"] for r in api.requetes[0].corps["requests"]])
