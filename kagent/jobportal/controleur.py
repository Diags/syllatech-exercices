"""L'API et le controleur : appliquer, elaguer, reconcilier, publier un statut.

CE QUE `kubectl apply` FAIT, ET NE FAIT PAS
-------------------------------------------
Il fait passer le manifeste par l'admission (validation + elagage), puis il
l'ECRIT. C'est tout. Aucun agent n'existe encore.

C'est ensuite le controleur qui boucle : il lit les objets `Agent`, resout
leurs references (`modelConfig`, serveurs d'outils, agents delegues), et
ecrit un STATUT. Deux conditions, et elles ne disent pas la meme chose :

    Accepted   le manifeste est coherent avec ce qui existe
    Ready      l'agent est reellement invocable

⚠️ LA LECON DU CHAPITRE 1 : un `Agent` qui reference un `ModelConfig`
inexistant est **cree sans erreur**. `kubectl apply` repond « created ».
L'agent n'est jamais pret, et la seule trace est
`kubectl get agent -o yaml`, dans `status.conditions`. C'est exactement le
comportement d'un Service au selecteur fautif — et c'est le prix du
declaratif : l'ordre d'application n'a pas d'importance, donc l'API ne peut
pas refuser une reference qui n'existe pas ENCORE.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import crd, schemas


class ErreurApi(Exception):
    """Un manifeste refuse par l'admission, un genre inconnu."""


@dataclass
class Condition:
    type: str                  # Accepted | Ready
    statut: str                # "True" | "False"
    raison: str
    message: str = ""

    def __str__(self) -> str:
        marque = "✓" if self.statut == "True" else "✗"
        return f"{marque} {self.type}={self.statut} ({self.raison})"


@dataclass
class Objet:
    """Un objet tel que l'API l'a STOCKE — elagage compris."""

    genre: str
    nom: str
    espace: str
    spec: dict[str, Any]
    elagues: list[str] = field(default_factory=list)
    conditions: list[Condition] = field(default_factory=list)

    @property
    def adresse(self) -> str:
        return f"{self.espace}/{self.nom}"

    def condition(self, type_: str) -> Condition | None:
        for condition in self.conditions:
            if condition.type == type_:
                return condition
        return None

    @property
    def pret(self) -> bool:
        condition = self.condition("Ready")
        return condition is not None and condition.statut == "True"


class Api:
    """Le serveur d'API : admission, stockage, et rien d'autre."""

    def __init__(self) -> None:
        self.objets: dict[tuple[str, str], Objet] = {}
        self.evenements: list[str] = []

    def appliquer(self, manifeste: dict[str, Any]) -> crd.Verdict:
        genre = manifeste.get("kind")
        if genre not in schemas.PAR_GENRE:
            raise ErreurApi(
                f"genre inconnu : « {genre} » — aucune CRD ne le declare")
        verdict = crd.admettre(schemas.pour(genre), manifeste)
        if not verdict.valide:
            # ⚠️ Un refus d'admission, lui, EST bruyant : `kubectl apply`
            # affiche l'erreur et ne cree rien.
            return verdict

        objet = verdict.objet
        metadonnees = objet["metadata"]
        stocke = Objet(genre, metadonnees["name"],
                       metadonnees.get("namespace", "kagent"),
                       objet.get("spec", {}), list(verdict.elagues))
        self.objets[(genre, stocke.adresse)] = stocke
        self.evenements.append(
            f"{genre.lower()}/{stocke.nom} configure"
            + (f" ({len(verdict.elagues)} champ(s) elague(s))"
               if verdict.elagues else ""))
        return verdict

    def lire(self, genre: str, nom: str,
             espace: str = "kagent") -> Objet | None:
        return self.objets.get((genre, f"{espace}/{nom}"))

    def lister(self, genre: str) -> list[Objet]:
        return sorted((o for (g, _), o in self.objets.items() if g == genre),
                      key=lambda o: o.nom)

    def supprimer(self, genre: str, nom: str, espace: str = "kagent") -> bool:
        return self.objets.pop((genre, f"{espace}/{nom}"), None) is not None


class Controleur:
    """La boucle de reconciliation : il ne cree rien, il constate."""

    def __init__(self, api: Api, outils_exposes: list[str] | None = None) -> None:
        self.api = api
        self.outils_exposes = outils_exposes or []
        self.passages = 0

    def reconcilier(self) -> None:
        self.passages += 1
        for agent in self.api.lister("Agent"):
            agent.conditions = self._conditions(agent)

    def _conditions(self, agent: Objet) -> list[Condition]:
        specification = agent.spec
        if specification.get("type") != "Declarative":
            return [Condition("Accepted", "True", "TypeSupporte"),
                    Condition("Ready", "False", "NonDeclaratif",
                              "un agent BYO est pret quand son deploiement l'est")]

        # >>> depart: resoudre les references, et publier Accepted puis Ready
        #     return [Condition("Accepted", "True", "ReferencesResolues"),
        #             Condition("Ready", "True", "Invocable")]
        corps = specification.get("declarative") or {}
        manques: list[str] = []

        modele = corps.get("modelConfig")
        if not self.api.lire("ModelConfig", modele or ""):
            manques.append(f"ModelConfig « {modele} » introuvable")

        for outil in corps.get("tools") or []:
            if outil.get("type") == "McpServer":
                serveur = (outil.get("mcpServer") or {}).get("name", "")
                # Le serveur d'outils fourni par kagent existe toujours.
                if serveur != "kagent-tool-server" and \
                        not self.api.lire("RemoteMCPServer", serveur):
                    manques.append(f"RemoteMCPServer « {serveur} » introuvable")
            elif outil.get("type") == "Agent":
                delegue = (outil.get("agent") or {}).get("name", "")
                if not self.api.lire("Agent", delegue):
                    manques.append(f"Agent « {delegue} » introuvable")

        if manques:
            return [
                Condition("Accepted", "False", "ReferencesManquantes",
                          " ; ".join(manques)),
                Condition("Ready", "False", "EnAttenteDeDependances",
                          "l'agent existe et n'est pas invocable"),
            ]
        return [Condition("Accepted", "True", "ReferencesResolues"),
                Condition("Ready", "True", "Invocable")]
        # <<<

    # -- consultation ---------------------------------------------------

    def prets(self) -> list[Objet]:
        return [a for a in self.api.lister("Agent") if a.pret]

    def en_attente(self) -> list[Objet]:
        return [a for a in self.api.lister("Agent") if not a.pret]


def rendre_statut(agents: list[Objet]) -> list[str]:
    """Ce qu'afficherait `kubectl get agents`."""
    lignes = [f"{'NOM':<26} {'ACCEPTED':<10} {'READY':<8} RAISON"]
    for agent in agents:
        accepte = agent.condition("Accepted")
        pret = agent.condition("Ready")
        raison = (accepte.message if accepte and accepte.statut == "False"
                  else (pret.raison if pret else "—"))
        lignes.append(f"{agent.nom:<26} "
                      f"{(accepte.statut if accepte else '?'):<10} "
                      f"{(pret.statut if pret else '?'):<8} {raison}")
    return lignes
