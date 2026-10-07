"""Un serveur Ollama simulé, branché SOUS les vrais clients.

Les clients `ollama` et `openai` construisent leurs vraies requêtes et lisent
de vraies réponses HTTP : seul le transport est remplacé, et les réponses du
modèle sont écrites à l'avance. Les tests tournent ainsi sans Ollama, sans
modèle et sans réseau, et MESURENT ce que les clients envoient réellement.

    serveur = FausseOllama()
    serveur.repondre("Bonjour")
    client = serveur.client()              # un vrai ollama.Client
    client.chat(model=..., messages=...)   # → « Bonjour »
    serveur.requetes[0].corps              # → ce que le client a envoyé

Les deux clients n'utilisent pas la même bibliothèque HTTP (`ollama` : httpx ;
`openai` 3.x : httpx2) : chacun reçoit le transport simulé de la sienne.
"""

import json
from dataclasses import dataclass, field

import httpx
import httpx2
import ollama
import openai

HOTE = "http://ollama.test:11434"

STATS = {"total_duration": 2_000_000_000, "load_duration": 100_000_000, "prompt_eval_count": 40,
         "prompt_eval_duration": 200_000_000, "eval_count": 20, "eval_duration": 1_000_000_000}


@dataclass
class Requete:
    methode: str
    chemin: str
    corps: dict


@dataclass
class FausseOllama:
    reponses: list = field(default_factory=list)
    requetes: list = field(default_factory=list)

    # -- ce que le serveur répondra, dans l'ordre ----------------------------

    def repondre(self, texte: str, modele: str = "qwen2.5:1.5b-instruct-q4_K_M", **stats):
        """Une réponse de /api/chat (ou de /v1/chat/completions, selon la requête)."""
        self.reponses.append(("chat", {"modele": modele, "texte": texte, "stats": {**STATS, **stats}}))

    def vecteurs(self, *embeddings: list[float]):
        """Une réponse de /api/embed : un vecteur par texte envoyé."""
        self.reponses.append(("brut", {"model": "bge-m3", "embeddings": list(embeddings),
                                       "total_duration": 50_000_000, "load_duration": 0,
                                       "prompt_eval_count": 10}))

    def repondre_brut(self, donnees: dict):
        self.reponses.append(("brut", donnees))

    def echouer(self, statut: int, message: str):
        self.reponses.append(("erreur", (statut, {"error": message})))

    # -- les clients : les vrais, sur notre transport ------------------------

    def client(self, **options) -> ollama.Client:
        return ollama.Client(host=HOTE, transport=httpx.MockTransport(self._ollama), **options)

    def client_openai(self) -> openai.OpenAI:
        return openai.OpenAI(base_url=f"{HOTE}/v1", api_key="ollama",
                             http_client=openai.DefaultHttpxClient(transport=httpx2.MockTransport(self._openai)))

    # -- la mécanique ---------------------------------------------------------

    def _suivante(self, methode: str, chemin: str, contenu: bytes):
        corps = json.loads(contenu or b"{}")
        self.requetes.append(Requete(methode, chemin, corps))
        if not self.reponses:
            raise AssertionError(f"aucune réponse prévue pour la requête n°{len(self.requetes)} ({chemin})")
        return corps, self.reponses.pop(0)

    def _ollama(self, requete: httpx.Request) -> httpx.Response:
        corps, (genre, donnees) = self._suivante(requete.method, requete.url.path, requete.content)
        if genre == "erreur":
            return httpx.Response(donnees[0], json=donnees[1])
        if genre == "brut":
            return httpx.Response(200, json=donnees)
        if corps.get("stream", True):  # Ollama diffuse par défaut ; le client envoie stream=false
            return httpx.Response(200, text=_en_flux(donnees), headers={"content-type": "application/x-ndjson"})
        return httpx.Response(200, json=_message(donnees, donnees["texte"], fini=True))

    def _openai(self, requete: httpx2.Request) -> httpx2.Response:
        corps, (genre, donnees) = self._suivante(requete.method, requete.url.path, requete.content)
        if genre == "erreur":
            return httpx2.Response(donnees[0], json={"error": {"message": donnees[1]["error"]}})
        if genre == "brut":
            return httpx2.Response(200, json=donnees)
        return httpx2.Response(200, json={
            "id": "chatcmpl-simule", "object": "chat.completion", "created": 0, "model": corps["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": donnees["texte"]}}],
            "usage": {"prompt_tokens": donnees["stats"]["prompt_eval_count"],
                      "completion_tokens": donnees["stats"]["eval_count"],
                      "total_tokens": donnees["stats"]["prompt_eval_count"] + donnees["stats"]["eval_count"]},
        })


def _message(donnees: dict, texte: str, fini: bool) -> dict:
    message = {"model": donnees["modele"], "created_at": "2026-10-06T00:00:00Z",
               "message": {"role": "assistant", "content": texte}, "done": fini}
    if fini:
        message.update(done_reason="stop", **donnees["stats"])
    return message


def _en_flux(donnees: dict) -> str:
    """La même réponse, découpée mot à mot en lignes JSON, comme Ollama la diffuse."""
    mots = donnees["texte"].split(" ")
    lignes = [_message(donnees, mot if i == len(mots) - 1 else mot + " ", fini=False)
              for i, mot in enumerate(mots)]
    lignes.append(_message(donnees, "", fini=True))
    return "".join(json.dumps(ligne, ensure_ascii=False) + "\n" for ligne in lignes)
