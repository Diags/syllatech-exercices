"""Le client de modèle factice — un `ChatCompletionClient` AutoGen complet.

POURQUOI L'ÉCRIRE

Le cours importe `OpenAIChatCompletionClient` depuis `autogen_ext`, **un
paquet séparé** que `autogen-agentchat` ne tire pas — et qui demande une clé.
`ChatCompletionClient` est l'interface que tous ces clients implémentent :
huit membres abstraits, et les écrire une fois apprend ce qu'AutoGen attend
vraiment d'un modèle.

CE QUE CE CLIENT FAIT

Il **appelle réellement les outils** (un `FunctionCall` dans `content`), lit
leur retour au tour suivant, et construit sa réponse à partir de là. Un client
factice qui répond toujours la même chose vérifie la plomberie et rien
d'autre : un agent qui ignore le retour de ses outils passerait tous les tests.

Il respecte aussi la règle qui fait tourner une équipe : **le mot de fin ne
doit être prononcé que lorsque le travail est fait**. Un modèle qui le dit
toujours termine au premier tour ; un modèle qui ne le dit jamais tourne
jusqu'à la borne. Les deux cas existent en vrai, et le chapitre 4 les montre.
"""

from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence

from autogen_core import FunctionCall
from autogen_core.models import (AssistantMessage, ChatCompletionClient,
                                 CreateResult, FunctionExecutionResultMessage,
                                 LLMMessage, ModelFamily, ModelInfo,
                                 RequestUsage, SystemMessage, UserMessage)

MOT_DE_FIN = "TERMINE"


class ClientFactice(ChatCompletionClient):
    """Déterministe, sans réseau, et qui se sert vraiment de ses outils.

    `tours_avant_fin` est le paramètre du chapitre 4 : au bout de combien de
    prises de parole cet agent prononce-t-il le mot de fin. `None` = jamais —
    et c'est ce cas qui rend une borne `MaxMessageTermination` indispensable.
    """

    def __init__(self, nom: str = "factice", tours_avant_fin: int | None = None,
                 dit_le_mot_de_fin: bool = False) -> None:
        self._nom = nom
        self._tours_avant_fin = tours_avant_fin
        self._dit_le_mot_de_fin = dit_le_mot_de_fin
        self._usage = RequestUsage(prompt_tokens=0, completion_tokens=0)
        self.appels: list[str] = []
        self.tours = 0

    # -------------------------------------------------- l'interface

    async def create(self, messages: Sequence[LLMMessage], *, tools=(),
                     tool_choice="auto", json_output=None, extra_create_args=None,
                     cancellation_token=None, **kwargs) -> CreateResult:
        self.tours += 1
        self._usage = RequestUsage(
            prompt_tokens=self._usage.prompt_tokens + _signes(messages) // 4,
            completion_tokens=self._usage.completion_tokens + 12)

        # >>> depart: si des outils sont disponibles et qu'aucun retour n'est encore arrive, rendre un CreateResult dont le content est une liste de FunctionCall (finish_reason="function_calls"). Sinon, repondre en texte. Quatre tests le verifient.
        #     return CreateResult(finish_reason="stop", content="", usage=self._usage, cached=False)
        if tools and not _retours(messages):
            outil = _choisir(tools, _demande(messages))
            self.appels.append(outil["name"])
            return CreateResult(
                finish_reason="function_calls",
                content=[FunctionCall(id=f"appel-{len(self.appels)}",
                                      name=outil["name"],
                                      arguments=json.dumps(
                                          _arguments(outil, _demande(messages))))],
                usage=self._usage, cached=False)

        return CreateResult(finish_reason="stop", content=self._repondre(messages),
                            usage=self._usage, cached=False)
        # <<<

    async def create_stream(self, messages, **kwargs):
        yield await self.create(messages, **kwargs)

    async def close(self) -> None:
        return None

    def actual_usage(self) -> RequestUsage:
        return self._usage

    def total_usage(self) -> RequestUsage:
        return self._usage

    def count_tokens(self, messages: Sequence[LLMMessage], **kwargs) -> int:
        return _signes(messages) // 4

    def remaining_tokens(self, messages: Sequence[LLMMessage], **kwargs) -> int:
        return 128_000 - self.count_tokens(messages)

    @property
    def capabilities(self) -> ModelInfo:
        return self.model_info

    @property
    def model_info(self) -> ModelInfo:
        # `function_calling=True` n'est pas décoratif : à False, AutoGen refuse
        # de donner des outils à l'agent, et l'agent reste muet sans erreur.
        return ModelInfo(vision=False, function_calling=True, json_output=False,
                         family=ModelFamily.UNKNOWN, structured_output=False,
                         multiple_system_messages=True)

    # -------------------------------------------------- le comportement

    def _repondre(self, messages: Sequence[LLMMessage]) -> str:
        # Le selecteur d'un SelectorGroupChat appelle le MEME client, avec un
        # prompt tres particulier : « select the next role from [...] to play.
        # Only return the role. » Une reponse qui n'est pas exactement un nom
        # de participant fait retomber AutoGen sur l'orateur precedent, avec
        # un avertissement — l'equipe tourne, mal, et l'on croit que le
        # selecteur « prefere » cet agent.
        # >>> depart: si le prompt est celui d'un selecteur, rendre EXACTEMENT un nom de participant. Une autre reponse fait retomber AutoGen sur l'orateur precedent avec un simple avertissement : l'equipe tourne, mal. Trois tests le verifient.
        #     pass
        candidats = _candidats(messages)
        if candidats:
            return self._selectionner(candidats, messages)
        # <<<

        donnees = _retours(messages)
        role = _role(messages) or self._nom
        if donnees:
            corps = (f"[{role}] d'apres les outils : " + " ; ".join(donnees[:3])
                     + (f" (+{len(donnees) - 3})" if len(donnees) > 3 else ""))
        else:
            amont = _dernier_message(messages)
            corps = f"[{role}] a partir de « {amont[:60]} » : synthese factice."
        return corps + (f" {MOT_DE_FIN}" if self._doit_finir() else "")

    def _selectionner(self, candidats: list[str], messages) -> str:
        """Fait tourner les roles, en evitant de redonner la parole au dernier.

        Un selecteur qui redonne toujours la main au meme agent reproduit une
        ronde a un seul participant — et c'est ce que produit un modele qui
        repond mal, sans que rien ne l'indique hors d'un avertissement.
        """
        dernier = _dernier_orateur(messages, candidats)
        restants = [c for c in candidats if c != dernier] or candidats
        return restants[self.tours % len(restants)]

    def _doit_finir(self) -> bool:
        if self._dit_le_mot_de_fin:
            return True
        return (self._tours_avant_fin is not None
                and self.tours >= self._tours_avant_fin)


# ------------------------------------------------------------------ aides

def _joindre(messages: Sequence[LLMMessage]) -> str:
    return "\n".join(str(getattr(m, "content", "")) for m in messages)


def _candidats(messages: Sequence[LLMMessage]) -> list[str]:
    """Les participants proposes par le prompt du selecteur, s'il y en a un."""
    texte = _joindre(messages)
    if "select the next role" not in texte:
        return []
    m = re.search(r"select the next role from \[([^\]]+)\]", texte)
    return re.findall(r"'([^']+)'", m.group(1)) if m else []


def _dernier_orateur(messages: Sequence[LLMMessage], candidats: list[str]) -> str:
    texte = _joindre(messages)
    trouves = [(texte.rfind(f"{c}:"), c) for c in candidats if f"{c}:" in texte]
    return max(trouves)[1] if trouves else ""


def _signes(messages: Sequence[LLMMessage]) -> int:
    return sum(len(str(getattr(m, "content", ""))) for m in messages)


def _demande(messages: Sequence[LLMMessage]) -> str:
    for message in messages:
        if isinstance(message, UserMessage):
            return str(message.content)
    return _dernier_message(messages)


def _dernier_message(messages: Sequence[LLMMessage]) -> str:
    for message in reversed(messages):
        contenu = getattr(message, "content", "")
        if isinstance(contenu, str) and contenu.strip():
            return contenu
    return ""


def _role(messages: Sequence[LLMMessage]) -> str:
    """Le nom de l'agent, lu dans son message système.

    AutoGen n'expose pas l'agent au client : c'est le `system_message` qui
    identifie qui parle. Sans lui, tous les agents d'une équipe rendent la
    même chose — et la démonstration du chapitre 3 devient vide.
    """
    for message in messages:
        if isinstance(message, SystemMessage):
            m = re.search(r"Tu es (?:le |la |l')?([\w\- ]+)", str(message.content))
            if m:
                return m.group(1).strip()
    return ""


def _retours(messages: Sequence[LLMMessage]) -> list[str]:
    donnees: list[str] = []
    for message in messages:
        if not isinstance(message, FunctionExecutionResultMessage):
            continue
        for resultat in message.content:
            brut = str(resultat.content)
            try:
                charge = json.loads(brut)
            except ValueError:
                donnees.append(brut[:90])
                continue
            donnees += ([str(x) for x in charge] if isinstance(charge, list)
                        else [str(charge)])
    return donnees


def _schema(outil) -> dict:
    """AutoGen passe soit un `Tool`, soit un `ToolSchema` (un dict).

    Les deux formes arrivent selon le chemin d'appel. Ne gérer que l'une des
    deux donne un agent qui marche en test et pas en équipe.
    """
    if isinstance(outil, Mapping):
        return dict(outil)
    return {"name": getattr(outil, "name", "?"),
            "description": getattr(outil, "description", ""),
            "parameters": (outil.schema.get("parameters", {})
                           if hasattr(outil, "schema") else {})}


def _choisir(tools, demande: str) -> dict:
    schemas = [_schema(o) for o in tools]
    for schema in schemas:
        if "salaire" in schema["name"].lower() and "salaire" in demande.lower():
            return schema
    return schemas[0]


def _arguments(schema: dict, demande: str) -> dict:
    proprietes = (schema.get("parameters") or {}).get("properties", {}) or {}
    mot = _mot_cle(demande)
    arguments: dict[str, Any] = {}
    for nom, champ in proprietes.items():
        type_ = champ.get("type")
        if type_ == "integer":
            arguments[nom] = 3
        elif type_ == "boolean":
            arguments[nom] = True
        elif type_ == "array":
            arguments[nom] = [mot]
        elif "ville" in nom:
            arguments[nom] = _ville(demande)
        else:
            arguments[nom] = mot
    return arguments


def _mot_cle(texte: str) -> str:
    m = re.search(r"\b(DevOps|Python|Java|cloud|data|MLOps|Kubernetes)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else "emploi"


def _ville(texte: str) -> str:
    m = re.search(r"\b(Lyon|Paris|Nantes|Bordeaux|Lille|Toulouse)\b",
                  texte, re.IGNORECASE)
    return m.group(1) if m else ""
