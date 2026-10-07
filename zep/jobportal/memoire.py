"""Le client mémoire — la forme de l'API Zep, sur le graphe local.

    client.user.add(user_id=…)
    client.thread.create(thread_id=…, user_id=…)
    client.thread.add_messages(thread_id, messages=[…])
    contexte = client.thread.get_user_context(thread_id=…).context

Les noms et la forme sont ceux de `zep-cloud`. Ce qui est derrière est le
graphe local, pour que tout s'exécute et s'inspecte.

CE QUE LE BLOC DE CONTEXTE EST, ET N'EST PAS

Ce n'est pas l'historique. C'est une **synthèse des faits encore valides**,
prête à coller dans un prompt système. La différence se voit sur une longue
conversation : l'historique grossit sans fin, le bloc de contexte non — il
remplace un fait par un autre au lieu de les empiler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .graphe import Fait, Graphe, maintenant


@dataclass
class Message:
    """La forme exacte de `zep_cloud.types.Message`."""

    role: str                       # "user" ou "assistant"
    content: str
    name: str = ""
    created_at: datetime = field(default_factory=maintenant)


@dataclass
class Thread:
    thread_id: str
    user_id: str
    messages: list[Message] = field(default_factory=list)


@dataclass
class Contexte:
    context: str
    faits: list[Fait] = field(default_factory=list)


class Memoire:
    """Le client, avec les trois sous-objets de l'API Zep."""

    def __init__(self) -> None:
        self.graphe = Graphe()
        self.utilisateurs: dict[str, dict] = {}
        self.threads: dict[str, Thread] = {}
        self.user = _Utilisateurs(self)
        self.thread = _Threads(self)
        self.graph = _Graphe(self)


class _Utilisateurs:
    def __init__(self, memoire: Memoire) -> None:
        self._m = memoire

    def add(self, user_id: str, first_name: str = "", last_name: str = "") -> dict:
        profil = {"user_id": user_id, "first_name": first_name,
                  "last_name": last_name}
        self._m.utilisateurs[user_id] = profil
        return profil

    def get(self, user_id: str) -> dict:
        return self._m.utilisateurs.get(user_id, {})


class _Threads:
    """Un fil de conversation. Plusieurs fils, un seul utilisateur.

    ⚠️ C'est la distinction qui compte, et celle qu'on rate : les MESSAGES
    appartiennent au fil, les FAITS appartiennent à l'utilisateur. Ouvrir un
    nouveau fil repart d'un historique vide — et de la même mémoire.
    """

    def __init__(self, memoire: Memoire) -> None:
        self._m = memoire

    def create(self, thread_id: str, user_id: str) -> Thread:
        fil = Thread(thread_id=thread_id, user_id=user_id)
        self._m.threads[thread_id] = fil
        return fil

    def add_messages(self, thread_id: str, messages: list[Message]) -> list[Fait]:
        fil = self._m.threads[thread_id]
        nom = self._nom(fil.user_id)
        nouveaux: list[Fait] = []
        for message in messages:
            fil.messages.append(message)
            # Seuls les messages de l'UTILISATEUR nourrissent le graphe. Ceux
            # de l'assistant sont ses propres mots : les extraire ferait
            # croire à l'agent qu'il a appris ce qu'il vient de dire.
            if message.role == "user":
                nouveaux += self._m.graphe.ajouter_message(
                    nom, message.content, message.created_at)
        return nouveaux

    def get_user_context(self, thread_id: str) -> Contexte:
        fil = self._m.threads[thread_id]
        # TODO : construire le bloc a partir des faits VALIDES seulement. Y mettre les faits fermes donnerait au modele deux versions contradictoires sans dire laquelle est actuelle — c'est exactement ce que fait une memoire naive. Trois tests le verifient.
        return Contexte("", [])

    def _nom(self, user_id: str) -> str:
        profil = self._m.utilisateurs.get(user_id, {})
        return (profil.get("first_name") or user_id).strip()


class _Graphe:
    """`client.graph` — les faits métier et la recherche."""

    def __init__(self, memoire: Memoire) -> None:
        self._m = memoire

    def add(self, user_id: str, data: dict, quand: datetime | None = None) -> Fait:
        nom = self._m.thread._nom(user_id)
        return self._m.graphe.ajouter_donnee(nom, data, quand)

    def search(self, user_id: str, query: str, limit: int = 5) -> list[Fait]:
        nom = self._m.thread._nom(user_id)
        return self._m.graphe.chercher(nom, query, limit)


# -------------------------------------------- la mémoire qu'on écrit d'abord

class MemoireNaive:
    """Tout garder, et chercher dedans. C'est ce qu'on fait avant Zep.

    Elle n'a rien d'absurde : elle est simple, elle marche, et elle se dégrade
    sans bruit. Le chapitre 3 la compare au graphe sur le seul cas qui les
    sépare — une préférence qui change.
    """

    def __init__(self) -> None:
        self.messages: list[tuple[str, str]] = []

    def ajouter(self, utilisateur: str, texte: str) -> None:
        self.messages.append((utilisateur, texte))

    def contexte(self, utilisateur: str) -> str:
        lignes = [t for u, t in self.messages if u == utilisateur]
        return "HISTORIQUE :\n" + "\n".join(f"- {l}" for l in lignes)
