"""Exercer le runtime sans AWS, et sans ouvrir de port.

`BedrockAgentCoreApp` hérite de Starlette. Son `TestClient` appelle donc
l'application **en direct**, sans serveur ni socket : les réponses sont
exactement celles que le runtime renverrait, et les tests ne dépendent ni
d'un port libre ni d'un délai de démarrage.

C'est ce qui rend ce cours vérifiable ici : le contrat d'entrée/sortie est le
vrai, seul le déploiement manque.
"""

from __future__ import annotations

from dataclasses import dataclass

ENTETE_SESSION = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"


@dataclass
class Reponse:
    code: int
    texte: str
    json: object = None
    flux: bool = False

    def __str__(self) -> str:
        return f"{self.code}  {self.texte[:90]}"


def appeler(app, charge: dict | None = None, *, session: str | None = None,
            chemin: str = "/invocations", methode: str = "POST") -> Reponse:
    """Un appel au runtime, comme AgentCore le ferait."""
    import warnings

    with warnings.catch_warnings():
        # Starlette signale que son TestClient preferera httpx2. Cela ne
        # change rien a ce que ce projet mesure, et l'avertissement se
        # repeterait a chaque appel de chaque chapitre.
        warnings.simplefilter("ignore")
        from starlette.testclient import TestClient

    entetes = {ENTETE_SESSION: session} if session else {}
    with TestClient(app, raise_server_exceptions=False) as client:
        brute = client.request(methode, chemin, json=charge, headers=entetes)
        try:
            charge_utile = brute.json()
        except Exception:                    # noqa: BLE001
            charge_utile = None
        return Reponse(brute.status_code, brute.text, charge_utile,
                       flux=brute.text.startswith("data: "))


def morceaux(reponse: Reponse) -> list[str]:
    """Découpe une réponse SSE en ses événements.

    Un entrypoint qui **rend un générateur** bascule le runtime en
    `text/event-stream` : même décorateur, même route, transport différent.
    C'est le type de retour qui décide, et rien ne le déclare.
    """
    return [ligne.removeprefix("data: ")
            for ligne in reponse.texte.splitlines() if ligne.startswith("data: ")]


def sante(app) -> str:
    return appeler(app, chemin="/ping", methode="GET").json["status"]
