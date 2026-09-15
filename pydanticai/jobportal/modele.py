"""Le modèle factice — pour que tout tourne **sans clé d'API**.

PydanticAI fournit deux modèles de test, et ce projet utilise les deux :

`TestModel` remplit la sortie structurée avec des valeurs valides mais vides
de sens (`'a'`, `0`). Il vérifie la **plomberie** : le schéma est-il bien
transmis, la validation passe-t-elle, les outils sont-ils appelés ?

`FunctionModel` laisse écrire la réponse **en Python**. C'est lui qui permet de
simuler un vrai comportement : appeler un outil, lire son résultat, puis
répondre en s'appuyant dessus. Sans lui, aucun test ne peut vérifier qu'un
agent se sert vraiment de ce que ses outils lui rendent.

Le jour où vous posez `ANTHROPIC_API_KEY`, `modele()` rend le vrai modèle et
**rien d'autre ne change** : c'est tout l'intérêt d'avoir le modèle en
paramètre plutôt qu'en dur dans le code.
"""

from __future__ import annotations

import os
import re

from pydantic_ai.messages import (ModelMessage, ModelResponse, TextPart,
                                  ToolCallPart, ToolReturnPart)
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.test import TestModel

MODELE_REEL = "anthropic:claude-sonnet-5"
_DEJA_DIT = False


def modele(factice=None):
    """Rend le vrai modèle si une clé est posée ET le fournisseur installé.

    Les deux conditions comptent. `pydantic-ai-slim` n'embarque AUCUN client
    de fournisseur : avec une clé posée mais sans l'extra, `Agent(...)` lève
    `ImportError` dès la construction — avant le moindre appel réseau, et avec
    un message qui parle d'installation là où l'on cherchait une erreur de
    configuration. On préfère ici le dire une fois et continuer.

        uv sync --extra reel     pour installer le client Anthropic
    """
    global _DEJA_DIT
    if avec_cle():
        if _fournisseur_installe():
            return MODELE_REEL
        if not _DEJA_DIT:
            _DEJA_DIT = True
            print("  (cle ANTHROPIC_API_KEY posee, mais le client anthropic n'est "
                  "pas installe : « uv sync --extra reel ». On continue en factice.)")
    return factice if factice is not None else TestModel()


def avec_cle() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def en_factice() -> bool:
    """Vrai quand `modele()` rendra le factice — cle absente OU client absent.

    Deux conditions, donc deux raisons de tourner en factice. Les confondre
    ferait afficher « vous etes sur le vrai modele » a quelqu'un qui ne l'est
    pas, et c'est exactement le genre de message qui fait perdre une heure.
    """
    return not (avec_cle() and _fournisseur_installe())


def _fournisseur_installe() -> bool:
    try:
        import anthropic     # noqa: F401
    except ImportError:
        return False
    return True


# ------------------------------------------- un modèle qui SE SERT des outils

def conseiller(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
    """Un modèle qui appelle l'outil disponible, puis répond à partir du retour.

    C'est le comportement qu'on veut vérifier et que `TestModel` ne produit
    pas : il appelle bien les outils, mais sa réponse finale ne dépend pas de
    ce qu'ils ont rendu. Un agent qui ignore le retour de ses outils passe
    tous les tests de plomberie et se trompe en production.
    """
    # TODO : au premier tour, appeler le premier outil disponible (ToolCallPart). Aux tours suivants, lire le dernier ToolReturnPart et construire la sortie A PARTIR DE LUI. Un test exige que les offres citees existent toutes dans la base.
    return ModelResponse(parts=[TextPart("a")])


def _valeur(nom: str, schema: dict, messages: list[ModelMessage]):
    """Choisit un argument plausible à partir de la question posée.

    Volontairement simple : ce n'est pas un modèle, c'est un gabarit. Mais il
    doit varier avec l'entrée, sinon le test ne prouve rien sur le passage des
    arguments.
    """
    if schema.get("type") == "boolean":
        return True
    if schema.get("type") == "integer":
        return 1
    demande = _derniere_question(messages)
    m = re.search(r"\b(DevOps|Python|Java|cloud|data)\b", demande, re.IGNORECASE)
    return m.group(1) if m else ""


def _derniere_question(messages: list[ModelMessage]) -> str:
    for message in reversed(messages):
        for part in message.parts:
            contenu = getattr(part, "content", None)
            if isinstance(contenu, str) and contenu:
                return contenu
    return ""


def _sortie(info: AgentInfo, contenu) -> dict:
    """Remplit le schéma de sortie à partir du retour d'outil."""
    schema = info.output_tools[0].parameters_json_schema
    sortie = {}
    for nom, champ in schema.get("properties", {}).items():
        type_ = champ.get("type")
        if type_ == "array":
            sortie[nom] = [str(x) for x in (contenu or [])][:5]
        elif type_ == "integer":
            sortie[nom] = min(10, len(contenu or []))
        elif type_ == "boolean":
            sortie[nom] = bool(contenu)
        else:
            sortie[nom] = _resume(contenu)
    return sortie


def _resume(contenu) -> str:
    if isinstance(contenu, list) and contenu:
        return f"{len(contenu)} resultat(s) : " + ", ".join(str(x) for x in contenu[:3])
    if contenu:
        return str(contenu)[:200]
    return "aucun resultat"


def modele_conseiller() -> FunctionModel:
    return FunctionModel(conseiller)


__all__ = ["FunctionModel", "TestModel", "avec_cle", "conseiller", "en_factice",
           "modele", "modele_conseiller", "modele_diffuseur"]


# ------------------------------------------ un modèle qui DIFFUSE par morceaux

# Un vrai modèle n'envoie pas son JSON d'un bloc : il arrive par fragments, et
# la plupart sont du JSON INVALIDE — accolade manquante, chaîne non fermée.
# Ces morceaux sont coupés exprès au mauvais endroit, y compris au milieu d'un
# mot : c'est précisément ce que le chapitre 4 doit montrer.
MORCEAUX = [
    '{"titre": "Marche D',
    'evOps 2026", "points": ["Kubernetes reste ',
    'dominant"',
    ', "Le Go progresse sur l',
    'e tooling"',
    ', "Les salaires se tassent en province"]}',
]


def modele_diffuseur(morceaux: list[str] | None = None) -> FunctionModel:
    from pydantic_ai.models.function import DeltaToolCall

    async def flux(messages, info):
        nom = info.output_tools[0].name
        for i, morceau in enumerate(morceaux or MORCEAUX):
            yield {0: DeltaToolCall(name=nom if i == 0 else None, json_args=morceau)}

    return FunctionModel(stream_function=flux)
