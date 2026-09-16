"""Memory et Identity — la forme réelle de l'API, en mémoire.

Le cours écrit :

    from bedrock_agentcore.memory import MemoryClient

    client.create_event(memory_id=…, actor_id=…, session_id=…, messages=[…])
    souvenirs = client.retrieve_memories(memory_id=…, actor_id=…,
                                         search_criteria={"searchQuery": "…"})

`MemoryClient` existe dans le SDK installé, avec ses stratégies
(`add_user_preference_strategy`, `add_semantic_strategy`,
`add_summary_strategy`). Il parle à AWS : sans compte, rien ne s'exécute.

CE QUI EST SUBSTITUÉ

Le stockage et l'extraction. Les stratégies sont ici des règles écrites à la
main ; la vraie extraction utilise un modèle. Ce qui est conservé — et c'est
ce que le cours enseigne — est la STRUCTURE : court terme par session, long
terme par `actor_id`, extraction par stratégie, récupération par requête.

LA LIGNE QU'ON RATE

Le court terme est indexé par **session**, le long terme par **acteur**. Un
nouvel entretien repart d'un historique vide et de la même mémoire. Confondre
les deux fait soit tout oublier à chaque session, soit tout rejouer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone


def maintenant() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Message:
    role: str                       # "USER" ou "ASSISTANT"
    texte: str
    quand: datetime = field(default_factory=maintenant)


@dataclass
class Souvenir:
    """Ce qu'une stratégie a extrait — pas le message d'origine."""

    strategie: str                  # "preference", "fait" ou "resume"
    contenu: str
    quand: datetime = field(default_factory=maintenant)

    def __str__(self) -> str:
        return f"[{self.strategie}] {self.contenu}"


# ------------------------------------------------------ les stratégies

PREFERENCES = [
    (r"\b(je (?:pr[ée]f[èe]re|veux|cherche))\b.{0,60}", "preference"),
    (r"\b(pas de|jamais de|surtout pas)\b.{0,40}", "preference"),
]
FAITS = [
    (r"\b(\d+)\s*ans? d'?exp[ée]rience\b", "experience"),
    (r"\b(\d{2})\s*k\b", "salaire vise"),
    (r"\b(lyon|paris|nantes|bordeaux|lille|toulouse)\b", "ville"),
    (r"\b(cdi|cdd|freelance|alternance)\b", "contrat"),
]


def extraire(message: Message, strategies: set[str]) -> list[Souvenir]:
    """Ce qu'une stratégie retient d'un message.

    ⚠️ Seuls les messages de l'UTILISATEUR nourrissent la mémoire. Extraire
    les mots de l'assistant lui ferait croire qu'il a APPRIS ce qu'il vient
    de dire — au bout de trois tours, il défend une préférence qu'il a
    inventée lui-même.
    """
    # TODO : extraire les souvenirs d'un message. Seuls les messages de l'UTILISATEUR comptent : extraire les mots de l'assistant lui ferait croire qu'il a APPRIS ce qu'il vient de dire, et au troisieme tour il defend une preference qu'il a inventee. Appliquer PREFERENCES si « preference » est active, FAITS si « fait » l'est. Quatre tests le verifient.
    return []


# -------------------------------------------------------- le client

class Memoire:
    """La forme de `MemoryClient`, en mémoire vive."""

    def __init__(self) -> None:
        self.strategies: set[str] = set()
        self.court_terme: dict[str, list[Message]] = {}     # par session
        self.long_terme: dict[str, list[Souvenir]] = {}     # par acteur
        self.memory_id = "mem-jobportal"

    # -- les stratégies, comme dans le SDK --------------------------

    def add_user_preference_strategy(self) -> "Memoire":
        self.strategies.add("preference")
        return self

    def add_semantic_strategy(self) -> "Memoire":
        self.strategies.add("fait")
        return self

    def add_summary_strategy(self) -> "Memoire":
        self.strategies.add("resume")
        return self

    # -- écriture ---------------------------------------------------

    def create_event(self, actor_id: str, session_id: str,
                     messages: list[Message]) -> list[Souvenir]:
        """Un tour de conversation. Court terme TOUJOURS, long terme si une
        stratégie s'applique."""
        fil = self.court_terme.setdefault(session_id, [])
        extraits: list[Souvenir] = []
        for message in messages:
            fil.append(message)
            for souvenir in extraire(message, self.strategies):
                self._retenir(actor_id, souvenir)
                extraits.append(souvenir)

        if "resume" in self.strategies and len(fil) >= 4:
            resume = Souvenir("resume",
                              f"{len(fil)} echanges dans la session "
                              f"{session_id}")
            self._retenir(actor_id, resume, remplace=True)
            extraits.append(resume)
        return extraits

    def _retenir(self, actor_id: str, souvenir: Souvenir,
                 remplace: bool = False) -> None:
        souvenirs = self.long_terme.setdefault(actor_id, [])
        if remplace:
            souvenirs[:] = [s for s in souvenirs
                            if s.strategie != souvenir.strategie]
        elif any(s.contenu == souvenir.contenu for s in souvenirs):
            # Répéter une préférence ne l'ajoute pas deux fois : sinon la
            # mémoire grossit à chaque session sans rien apprendre.
            return
        souvenirs.append(souvenir)

    # -- lecture ----------------------------------------------------

    def list_events(self, session_id: str) -> list[Message]:
        """Le COURT terme : l'historique de cette session, et rien d'autre."""
        return list(self.court_terme.get(session_id, []))

    def retrieve_memories(self, actor_id: str, search_criteria: dict,
                          max_results: int = 5) -> list[Souvenir]:
        """Le LONG terme : ce qu'on sait de cet acteur, toutes sessions."""
        requete = (search_criteria or {}).get("searchQuery", "")
        mots = {m for m in re.findall(r"\w{3,}", requete.lower())}
        notes = []
        for souvenir in self.long_terme.get(actor_id, []):
            cible = set(re.findall(r"\w{3,}", souvenir.contenu.lower()))
            note = len(mots & cible)
            if note:
                notes.append((note, souvenir))
        notes.sort(key=lambda x: -x[0])
        return [s for _, s in notes[:max_results]]

    def tout(self, actor_id: str) -> list[Souvenir]:
        return list(self.long_terme.get(actor_id, []))


def sdk_reel() -> dict:
    from bedrock_agentcore.memory import MemoryClient

    methodes = [m for m in dir(MemoryClient) if not m.startswith("_")]
    return {
        "strategies": sorted(m for m in methodes if "strategy" in m
                             and not m.endswith("_and_wait")),
        "evenements": sorted(m for m in methodes
                             if "event" in m or "memor" in m)[:8],
        "total": len(methodes),
    }


# ------------------------------------------------------------ Identity

@dataclass
class Coffre:
    """`Identity` — un coffre de jetons OAuth, par acteur et par fournisseur.

    Ce que le cours appelle « accès délégué » : l'agent agit AU NOM de
    l'utilisateur, avec un jeton obtenu pour lui, et jamais avec un compte de
    service partagé. La différence se voit le jour de l'audit — et le jour où
    un utilisateur part.
    """

    jetons: dict[tuple[str, str], str] = field(default_factory=dict)

    def deposer(self, actor_id: str, fournisseur: str, jeton: str) -> None:
        self.jetons[(actor_id, fournisseur)] = jeton

    def obtenir(self, actor_id: str, fournisseur: str) -> str | None:
        return self.jetons.get((actor_id, fournisseur))

    def revoquer(self, actor_id: str) -> int:
        avant = len(self.jetons)
        self.jetons = {cle: v for cle, v in self.jetons.items()
                       if cle[0] != actor_id}
        return avant - len(self.jetons)
