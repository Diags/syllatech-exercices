"""Le modèle factice — Agno n'en fournit pas, on l'écrit.

PydanticAI livre `TestModel` ; LangGraph se contente d'un objet qui répond.
Agno, lui, attend un vrai `Model` : six méthodes abstraites, un contrat précis.
Les implémenter une fois apprend plus sur le framework que n'importe quelle
page de documentation — c'est en écrivant ce fichier qu'on comprend ce qu'Agno
attend vraiment d'un fournisseur.

LE CONTRAT, ET LE PIÈGE

`invoke()` doit rendre un **`ModelResponse` déjà construit**, pas la réponse
brute du fournisseur. `_parse_provider_response` est un helper que les
implémentations réelles appellent depuis *leur propre* `invoke` — la classe de
base ne l'appelle jamais pour vous. Rendre un dict depuis `invoke` produit
`'dict' object has no attribute 'role'`, une erreur qui ne dit rien de la
cause.

Le jour où vous posez `ANTHROPIC_API_KEY` et installez l'extra, `modele()`
rend `Claude(...)` et **rien d'autre ne change**.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from typing import Any

from agno.models.base import Model
from agno.models.response import ModelResponse

MODELE_REEL = "claude-sonnet-5"
_DEJA_DIT = False


def avec_cle() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def _client_installe() -> bool:
    try:
        import anthropic       # noqa: F401
    except ImportError:
        return False
    return True


def en_factice() -> bool:
    """Vrai quand `modele()` rendra le factice — clé absente OU client absent.

    Deux raisons distinctes, et les confondre ferait afficher « vous êtes sur
    le vrai modèle » à quelqu'un qui ne l'est pas.
    """
    return not (avec_cle() and _client_installe())


def modele(factice: Model | None = None) -> Model:
    global _DEJA_DIT
    if avec_cle():
        if _client_installe():
            from agno.models.anthropic import Claude
            return Claude(id=MODELE_REEL)
        if not _DEJA_DIT:
            _DEJA_DIT = True
            print("  (cle ANTHROPIC_API_KEY posee, mais le client anthropic n'est "
                  "pas installe : « uv sync --extra reel ». On continue en factice.)")
    return factice if factice is not None else ModeleFactice()


@dataclass
class ModeleFactice(Model):
    """Un modèle qui appelle les outils, lit leurs retours, et s'en sert.

    C'est le point qui compte pour tester un agent : un modèle qui appelle bien
    ses outils mais dont la réponse finale ne dépend pas de leur retour passe
    tous les tests de plomberie et se trompe en production.
    """

    id: str = "factice"
    name: str = "Factice"
    provider: str = "syllatech"

    # Ce que le modèle a « vu » — pour que les tests puissent l'inspecter.
    appels: list[str] = field(default_factory=list)
    outils_recus: list[str] = field(default_factory=list)

    # ------------------------------------------------------- le contrat

    def invoke(self, messages=None, tools=None, **kwargs) -> ModelResponse:
        messages = messages or []
        self.outils_recus = [_nom_outil(t) for t in (tools or [])]

        # TODO : rendre un ModelResponse (JAMAIS un dict : « 'dict' object has no attribute 'role' »). S'il y a des outils, qu'aucun retour d'outil n'est encore la, et que la question le merite, appeler un outil ; sinon repondre A PARTIR du dernier retour d'outil. Sept tests le verifient.
        return ModelResponse(role="assistant", content="")

    async def ainvoke(self, **kwargs) -> ModelResponse:
        return self.invoke(**kwargs)

    def invoke_stream(self, **kwargs):
        yield self.invoke(**kwargs)

    async def ainvoke_stream(self, **kwargs):
        yield self.invoke(**kwargs)

    def _parse_provider_response(self, response: Any, **kwargs) -> ModelResponse:
        return response

    def _parse_provider_response_delta(self, response: Any) -> ModelResponse:
        return response

    # ------------------------------------------------------- le comportement

    # Les mots qui déclenchent une recherche. Un vrai modèle décide par le
    # sens ; ici par une liste — mais la DÉCISION existe, et c'est elle qu'on
    # veut pouvoir observer.
    DECLENCHEURS = re.compile(
        r"\b(offre|poste|emploi|salaire|marche|marché|DevOps|Python|Java|"
        r"cloud|data|MLOps|Kubernetes|recrut)\w*", re.IGNORECASE)

    def _merite_un_outil(self, messages, tools) -> bool:
        question = next((m.content for m in reversed(messages)
                         if m.role == "user" and isinstance(m.content, str)), "")
        if self.DECLENCHEURS.search(question):
            return True
        # Les outils internes du framework (mémoire, délégation d'équipe) ne
        # dépendent pas de la question : ils font partie du fonctionnement.
        return any(_nom_outil(t) in OUTILS_DU_CADRE for t in tools)

    def _appeler_un_outil(self, messages, tools) -> ModelResponse:
        outil = self._choisir(messages, tools)
        nom = _nom_outil(outil)
        self.appels.append(nom)
        return ModelResponse(role="assistant", tool_calls=[{
            "id": f"appel-{len(self.appels)}",
            "type": "function",
            "function": {"name": nom,
                         "arguments": json.dumps(_arguments(outil, messages))},
        }])

    def _choisir(self, messages, tools):
        """Choisit l'outil que la question designe, pas le premier venu.

        Prendre `tools[0]` marche tant qu'il n'y a qu'un outil, puis devient
        faux en silence : l'agent appelle toujours le meme, et l'on croit que
        le modele « prefere » cet outil. Ici, un mot de la question suffit.
        """
        question = next((m.content for m in reversed(messages)
                         if m.role == "user" and isinstance(m.content, str)), "").lower()
        for outil in tools:
            if _nom_outil(outil) in OUTILS_DU_CADRE:
                return outil
        if "salaire" in question:
            for outil in tools:
                if "salaire" in _nom_outil(outil):
                    return outil
        return tools[0]

    def _repondre(self, messages, retours) -> str:
        question = next((m.content for m in reversed(messages)
                         if m.role == "user" and m.content), "")
        if not retours:
            return f"(sans outil) J'ai bien lu : {question!r}"
        # LA ligne qui compte : la réponse est construite A PARTIR du retour.
        lignes = _aplatir(retours[-1])
        return (f"D'apres l'outil, pour {question!r} : "
                + " ; ".join(lignes[:3]) + (f" (+{len(lignes) - 3})" if len(lignes) > 3 else ""))


# Les outils qu'Agno ajoute lui-meme quand on active une fonction : memoire,
# delegation d'equipe, recherche de connaissances. Ils ne dependent pas de la
# question — un agent a qui on a donne des connaissances CHERCHE avant de
# repondre, c'est tout l'interet de search_knowledge=True.
OUTILS_DU_CADRE = {"add_memory", "update_memory", "delegate_task_to_member",
                   "search_knowledge_base"}


def _nom_outil(outil) -> str:
    if isinstance(outil, dict):
        return outil.get("function", {}).get("name") or outil.get("name", "?")
    return getattr(outil, "name", "?")


def _arguments(outil, messages) -> dict:
    """Construit des arguments qui RESPECTENT le schéma de l'outil.

    Volontairement simple : ce n'est pas un modèle, c'est un gabarit. Mais il
    doit respecter le schéma, sinon Agno refuse l'appel — et cette contrainte
    apprend quelque chose : les outils internes du framework (mémoire,
    délégation d'équipe) sont des outils **comme les autres**, avec un schéma
    que le modèle doit honorer. Passer une chaîne là où un tableau est attendu
    lève une `ValidationError` pydantic, exactement comme pour vos outils.
    """
    schema = {}
    if isinstance(outil, dict):
        schema = outil.get("function", {}).get("parameters", {}).get("properties", {})
    question = next((m.content for m in reversed(messages)
                     if m.role == "user" and m.content), "")
    mot = re.search(r"\b(DevOps|Python|Java|cloud|data|MLOps|Kubernetes)\b",
                    question, re.IGNORECASE)
    sujet = mot.group(1) if mot else (question[:40] or "offres")

    # TODO : construire un argument par propriete du schema, en RESPECTANT son type (array -> liste, boolean -> True, integer -> 3, enum -> premiere valeur). Un tableau recu sous forme de chaine leve une ValidationError pydantic, meme pour les outils internes d'Agno.
    return {}


def _valeur(nom: str, champ: dict, sujet: str, messages) -> Any:
    if champ.get("enum"):
        return champ["enum"][0]
    type_ = champ.get("type")
    if type_ == "boolean":
        return True
    if type_ in ("integer", "number"):
        return 3
    if type_ == "array":
        return [sujet]
    if type_ == "object":
        return {}
    # Le coordinateur d'une équipe délègue par IDENTIFIANT de membre. Inventer
    # un identifiant fait échouer l'appel avec « Member with ID … not found » —
    # une erreur qu'un vrai modèle commet aussi, et qu'il corrige en relisant
    # la liste des membres. Ici on la relit directement.
    if nom == "member_id":
        return _premier_membre(messages) or sujet
    # Une recherche documentaire prend la QUESTION ENTIERE, pas un mot-cle :
    # reduire « combien de jours de teletravail » a « teletravail » perd
    # justement ce qu'on cherchait.
    if nom in ("query", "question", "search_query"):
        return _question(messages) or sujet
    return sujet


def _question(messages) -> str:
    return next((m.content for m in reversed(messages)
                 if m.role == "user" and isinstance(m.content, str)), "")


def _premier_membre(messages) -> str | None:
    """Lit le premier identifiant de membre dans le bloc <team_members>.

    Agno les écrit sous la forme `<member id="analyste-offres" name="…">`.
    L'identifiant est DÉRIVÉ du nom — « Analyste offres » devient
    « analyste-offres » — et ce n'est ni le nom ni le rôle : déléguer au nom
    échoue avec « Member with ID … not found ».
    """
    for message in messages:
        contenu = message.content if isinstance(message.content, str) else ""
        m = re.search(r'<member\s+id="([^"]+)"', contenu)
        if m:
            return m.group(1)
    return None


def _aplatir(contenu) -> list[str]:
    if isinstance(contenu, str):
        try:
            contenu = json.loads(contenu)
        except (ValueError, TypeError):
            return [contenu]
    if isinstance(contenu, list):
        return [str(x) for x in contenu]
    return [str(contenu)]
