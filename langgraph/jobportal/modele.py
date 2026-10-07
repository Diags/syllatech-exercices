"""Le chaînon manquant : le `llm` que les extraits du cours appellent.

Dans la vidéo, le code écrit `llm.invoke(...)` sans jamais montrer d'où vient
`llm`. Exiger une clé d'API pour exécuter le projet fermerait la porte à qui
veut simplement voir tourner un graphe — or ce que LangGraph enseigne, c'est
la STRUCTURE : les nœuds, les arêtes, l'état, la boucle. Elle s'observe très
bien avec un modèle factice.

    modele()            un faux modèle, déterministe, sans réseau
    modele(reel=True)   le vrai, si une clé est posée

Le faux sait deux choses, et c'est tout ce dont les six chapitres ont besoin :
répondre du texte, et DEMANDER UN OUTIL quand la question porte sur des
offres. Sans cette seconde capacité, la boucle agentique du chapitre 4 ne
tournerait jamais — on verrait le graphe, pas le cycle.
"""

from __future__ import annotations

import os
import re
from typing import Any, Sequence

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult


class ModeleFactice(BaseChatModel):
    """Un modèle qui ne parle à personne, et qui suffit à faire tourner le cours."""

    outils: list = []

    @property
    def _llm_type(self) -> str:
        return "factice-jobportal"

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> "ModeleFactice":
        # bind_tools rend un NOUVEAU modèle : le graphe compte là-dessus pour
        # garder un modèle nu à côté du modèle outillé.
        return ModeleFactice(outils=list(tools))

    def _generate(self, messages: list[BaseMessage], stop=None,
                  run_manager: CallbackManagerForLLMRun | None = None,
                  **kwargs: Any) -> ChatResult:
        return ChatResult(generations=[ChatGeneration(message=self._repondre(messages))])

    def _repondre(self, messages: list[BaseMessage]) -> AIMessage:
        # Un résultat d'outil vient d'arriver : on le met en forme et on
        # s'arrête. C'est le second tour de la boucle agentique.
        if messages and isinstance(messages[-1], ToolMessage):
            return AIMessage(content=f"D'après l'outil : {messages[-1].content}")

        demande = str(messages[-1].content) if messages else ""

        # Sans outil lié, pas d'appel d'outil possible. Et on appelle LE
        # premier outil qu'on nous a lié, quel qu'il soit : coder son nom en
        # dur marcherait pour un agent et casserait au second.
        if self.outils and self._parle_d_offres(demande):
            premier = self.outils[0]
            nom = getattr(premier, "name", None) or getattr(premier, "__name__", "outil")
            return AIMessage(
                content="",
                tool_calls=[{
                    "name": nom,
                    "args": {"mot_cle": self._mot_cle(demande)},
                    "id": "appel-1",
                }],
            )
        return AIMessage(content=f"(modèle factice) Vous avez dit : « {demande} »")

    @staticmethod
    def _parle_d_offres(texte: str) -> bool:
        return bool(re.search(r"offre|poste|emploi|job|recrut", texte, re.IGNORECASE))

    @staticmethod
    def _mot_cle(texte: str) -> str:
        """Le dernier mot « technique » de la phrase fait un mot-clé crédible."""
        mots = re.findall(r"[A-Za-zÀ-ÿ+#.]{3,}", texte)
        bruit = {"offre", "offres", "poste", "postes", "emploi", "cherche",
                 "trouve", "des", "les", "une", "pour", "moi", "avec", "sur"}
        utiles = [m for m in mots if m.lower() not in bruit]
        return utiles[-1] if utiles else ""


def modele(reel: bool = False) -> BaseChatModel:
    """Le modèle du projet. Factice par défaut, réel si vous le demandez.

    Pour passer au réel : `pip install langchain-anthropic`, posez
    ANTHROPIC_API_KEY, puis `modele(reel=True)`. Rien d'autre ne change dans
    les six chapitres — c'est le propos : le graphe ne dépend pas du modèle.
    """
    if not reel:
        return ModeleFactice()

    cle = os.environ.get("ANTHROPIC_API_KEY")
    if not cle:
        raise RuntimeError(
            "ANTHROPIC_API_KEY n'est pas posée. Laissez reel=False pour le "
            "modèle factice, ou posez la clé pour parler au vrai modèle."
        )
    from langchain_anthropic import ChatAnthropic   # dépendance optionnelle
    return ChatAnthropic(model="claude-sonnet-5", temperature=0)
