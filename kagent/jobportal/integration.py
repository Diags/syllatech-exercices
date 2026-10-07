"""Les deux sens de circulation entre une application Spring et un agent.

SENS 1 — SPRING APPELLE L'AGENT
-------------------------------
Le service metier envoie une tache a l'endpoint A2A de kagent, en HTTP, et
recupere une reponse. Ce module modelise le CONTRAT de cet echange : la
forme de la requete, celle de la reponse, et ce qui arrive quand l'une des
deux n'est pas celle qu'on croit.

SENS 2 — L'AGENT APPELLE SPRING
-------------------------------
On expose une partie de l'API metier en serveur MCP, on la declare en
`RemoteMCPServer`, et l'agent s'en sert comme d'un outil. Ce module fournit
l'outil correspondant, branche sur un catalogue d'offres.

⚠️ AUCUN HTTP N'EST FAIT. Il n'y a ni serveur ni socket : les deux cotes
s'appellent en memoire. Ce que le projet mesure est le CONTRAT — quelles
formes passent, lesquelles echouent, et comment l'echec se presente.

⚠️ ET L'ECHEC LE PLUS FREQUENT N'EST PAS UNE ERREUR HTTP. C'est un 200 qui
rend du HTML : une page d'erreur de passerelle, une redirection vers une
mire d'authentification. Le client attend du JSON, le desserialise, et
l'exception qui remonte ne parle ni d'agent ni de reseau. Le chapitre 6 le
mesure.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from . import crd, outils, traces


class ErreurIntegration(Exception):
    """Une charge utile qui ne respecte pas le contrat."""


# ── le contrat A2A ───────────────────────────────────────────────────────
#
# ⚠️ ENTREE DECLAREE : une transcription abregee de l'echange A2A tel que le
# cours le montre. Le protocole reel porte davantage de champs (etats
# intermediaires, artefacts, flux) ; on garde ce dont le chapitre parle.

REQUETE: dict[str, Any] = {
    "type": "object",
    "required": ["task"],
    "properties": {
        "task": {"type": "string"},
        "sessionId": {"type": "string"},
        "metadata": {"type": "object", "properties": {
            "traceparent": {"type": "string"},
        }},
    },
}

REPONSE: dict[str, Any] = {
    "type": "object",
    "required": ["status", "result"],
    "properties": {
        "status": {"type": "string",
                   "enum": ["completed", "failed", "input-required"]},
        "result": {"type": "string"},
        "usage": {"type": "object", "properties": {
            "inputTokens": {"type": "integer"},
            "outputTokens": {"type": "integer"},
        }},
    },
}


@dataclass
class Echange:
    """Ce qu'un appel A2A a echange, et ce qu'il en reste."""

    requete: dict[str, Any]
    corps_brut: str
    reponse: dict[str, Any] | None = None
    erreur: str = ""
    elagues: list[str] = field(default_factory=list)

    @property
    def reussi(self) -> bool:
        return self.reponse is not None and not self.erreur


class PointDEntreeA2A:
    """L'endpoint `/api/a2a/<espace>/<agent>` de kagent, en memoire."""

    def __init__(self, moteur) -> None:
        self.moteur = moteur

    def poster(self, agent: str, charge: dict[str, Any],
               espace: str = "kagent",
               parent: traces.Span | None = None) -> Echange:
        verdict = crd.admettre(REQUETE, charge)
        if not verdict.valide:
            return Echange(charge, "", erreur=str(verdict))

        # ⚠️ LA PROPAGATION DU CONTEXTE tient a UNE en-tete. Sans
        # `traceparent`, l'agent ouvre une trace neuve et l'incident se
        # raconte en deux morceaux qu'aucun ecran ne reunit.
        propager = bool((verdict.objet.get("metadata") or {}).get(
            "traceparent"))
        session = self.moteur.invoquer(
            agent, verdict.objet["task"], espace,
            parent=parent, propager=propager)

        reponse = {
            "status": "completed",
            "result": session.reponse,
            "usage": {"inputTokens": session.jetons_entree,
                      "outputTokens": session.jetons_sortie},
        }
        return Echange(verdict.objet, json.dumps(reponse), reponse,
                       elagues=list(verdict.elagues))


def lire_la_reponse(corps: str, type_de_contenu: str = "application/json"
                    ) -> tuple[dict[str, Any] | None, str]:
    """Ce que fait un client HTTP du corps qu'on lui rend.

    ⚠️ Le cas qui coute une matinee : un code 200, un corps HTML. Une page
    d'erreur de passerelle, une mire d'authentification, une redirection
    suivie. Le client desserialise, echoue, et l'exception ne parle ni
    d'agent ni de reseau.
    """
    # >>> depart: verifier le type de contenu AVANT de desserialiser
    #     return json.loads(corps), ""
    if not type_de_contenu.startswith("application/json"):
        apercu = corps.strip().splitlines()[0][:60] if corps.strip() else ""
        return None, (f"reponse en « {type_de_contenu} » et non en JSON — "
                      f"le corps commence par « {apercu} »")
    try:
        charge = json.loads(corps)
    except json.JSONDecodeError as erreur:
        return None, f"corps illisible : {erreur}"
    verdict = crd.admettre(REPONSE, charge)
    if not verdict.valide:
        return None, str(verdict)
    return verdict.objet, ""
    # <<<


# ── sens 2 : l'agent appelle Spring ──────────────────────────────────────

OFFRES = [
    {"id": 1, "titre": "Ingenieur plateforme", "ville": "Lyon",
     "teletravail": "2 jours"},
    {"id": 2, "titre": "Developpeur Java", "ville": "Nantes",
     "teletravail": "complet"},
    {"id": 3, "titre": "SRE", "ville": "Lyon", "teletravail": "aucun"},
]


class ApiSpring:
    """L'API metier du portail, exposee en MCP.

    Trois methodes, et une seule est en lecture. C'est exactement la
    question du chapitre 3, posee cette fois sur VOTRE API : exposer
    `creer_ticket` en outil, c'est donner a un modele le droit d'ecrire
    dans votre systeme.
    """

    def __init__(self) -> None:
        self.tickets: list[dict[str, Any]] = []
        self.appels: list[str] = []

    def rechercher_offres(self, ville: str = "") -> list[dict[str, Any]]:
        self.appels.append("rechercher_offres")
        if not ville:
            return list(OFFRES)
        return [offre for offre in OFFRES if offre["ville"].lower() == ville.lower()]

    def creer_ticket(self, titre: str = "", corps: str = "") -> dict[str, Any]:
        self.appels.append("creer_ticket")
        ticket = {"id": len(self.tickets) + 1, "titre": titre, "corps": corps}
        self.tickets.append(ticket)
        return ticket


def outils_de_spring(api: ApiSpring) -> dict[str, outils.Outil]:
    """Ce qu'un `RemoteMCPServer` pointant vers Spring rendrait disponible."""
    return {
        "rechercher_offres": outils.Outil(
            "rechercher_offres", outils.LECTURE,
            "cherche des offres du portail, par ville",
            api.rechercher_offres),
        "creer_ticket": outils.Outil(
            "creer_ticket", outils.ACTION,
            "⚠️ cree un ticket d'incident dans le portail",
            api.creer_ticket),
    }
