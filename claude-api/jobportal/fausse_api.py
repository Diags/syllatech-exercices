"""Une API Claude simulée, branchée SOUS le SDK officiel.

Le SDK `anthropic` construit ses vraies requêtes, les envoie, lit les vraies
réponses, gère les erreurs et les nouvelles tentatives : rien de tout cela
n'est imité. Seul le transport HTTP est remplacé (httpx2.MockTransport), et
les réponses de Claude sont écrites à l'avance. C'est ce qui permet au cours
de MESURER le comportement du SDK — ce qu'il envoie, combien de fois il
réessaie — sans clé d'API, sans réseau et sans rien payer.

    api = FausseAPI()
    api.repondre(texte("Bonjour"))
    client = api.client()          # un vrai anthropic.Anthropic
    client.messages.create(...)    # → la réponse écrite plus haut
    api.requetes[0].corps          # → ce que le SDK a réellement envoyé
"""

import json
from dataclasses import dataclass, field

import anthropic
import httpx2
from anthropic import DefaultHttpxClient


def texte(contenu: str) -> dict:
    return {"type": "text", "text": contenu}


def reflexion() -> dict:
    """Un bloc de réflexion vide : c'est ce que rend Opus 5.5 par défaut (display « omitted »)."""
    return {"type": "thinking", "thinking": "", "signature": "simulee"}


def appel_outil(identifiant: str, nom: str, entree: dict) -> dict:
    return {"type": "tool_use", "id": identifiant, "name": nom, "input": entree}


@dataclass
class Requete:
    methode: str
    chemin: str
    entetes: dict
    corps: dict


@dataclass
class FausseAPI:
    reponses: list = field(default_factory=list)
    requetes: list = field(default_factory=list)

    # -- ce que « Claude » répondra, dans l'ordre ---------------------------

    def repondre(self, *contenu, stop="end_turn", usage=None, stop_details=None):
        message = {
            "id": f"msg_{len(self.reponses) + 1:03d}", "type": "message", "role": "assistant",
            "model": "claude-opus-5-5", "content": list(contenu), "stop_reason": stop,
            "stop_sequence": None, "stop_details": stop_details,
            "usage": {"input_tokens": 100, "output_tokens": 20, **(usage or {})},
        }
        self.reponses.append((200, message, {}))

    def repondre_brut(self, donnees: dict):
        """Une réponse JSON quelconque (un lot de la Batches API, par exemple)."""
        self.reponses.append((200, donnees, {}))

    def echouer(self, statut: int, type_erreur: str, retry_after: str = "0"):
        erreur = {"type": "error", "error": {"type": type_erreur, "message": "simulée"}}
        self.reponses.append((statut, erreur, {"retry-after": retry_after}))

    # -- le client : le vrai SDK, sur notre transport ------------------------

    def client(self, **options) -> anthropic.Anthropic:
        return anthropic.Anthropic(
            api_key="cle-de-test",
            http_client=DefaultHttpxClient(transport=httpx2.MockTransport(self._gerer)),
            **options,
        )

    def _gerer(self, requete: httpx2.Request) -> httpx2.Response:
        corps = json.loads(requete.content or b"{}")
        self.requetes.append(Requete(requete.method, requete.url.path, dict(requete.headers), corps))
        if not self.reponses:
            raise AssertionError(f"aucune réponse prévue pour la requête n°{len(self.requetes)}")
        statut, donnees, entetes = self.reponses.pop(0)
        if statut == 200 and corps.get("stream"):
            return httpx2.Response(200, text=_en_flux(donnees),
                                   headers={"content-type": "text/event-stream"})
        return httpx2.Response(statut, json=donnees, headers=entetes)


def _en_flux(message: dict) -> str:
    """Le même message, découpé en événements Server-Sent Events comme l'API."""
    debut = {**message, "content": [], "stop_reason": None}

    def evenement(nom, donnees):
        return f"event: {nom}\ndata: {json.dumps(donnees, ensure_ascii=False)}\n\n"

    sortie = [evenement("message_start", {"type": "message_start", "message": debut})]
    for i, bloc in enumerate(message["content"]):
        if bloc["type"] != "text":
            raise ValueError("la fausse API ne diffuse que des blocs de texte")
        sortie.append(evenement("content_block_start", {"type": "content_block_start", "index": i,
                                                         "content_block": {"type": "text", "text": ""}}))
        mots = bloc["text"].split(" ")
        for j, mot in enumerate(mots):
            morceau = mot if j == len(mots) - 1 else mot + " "
            sortie.append(evenement("content_block_delta", {"type": "content_block_delta", "index": i,
                                                             "delta": {"type": "text_delta", "text": morceau}}))
        sortie.append(evenement("content_block_stop", {"type": "content_block_stop", "index": i}))
    sortie.append(evenement("message_delta", {"type": "message_delta",
                                               "delta": {"stop_reason": message["stop_reason"], "stop_sequence": None},
                                               "usage": {"output_tokens": message["usage"]["output_tokens"]}}))
    sortie.append(evenement("message_stop", {"type": "message_stop"}))
    return "".join(sortie)
