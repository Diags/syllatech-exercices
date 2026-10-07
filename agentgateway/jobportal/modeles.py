"""Les modèles virtuels : pondération, bascule, et condition en CEL.

Le cours dit que budgets, load balancing et failover « se règlent au proxy ».
C'est vrai, et le schéma dit **où** : sous `llm.virtualModels[].routing`, qui
a exactement trois formes, chacune avec sa sémantique écrite noir sur blanc.

    weighted    « Relative proportion of traffic sent to this target model. »
    failover    « targets are grouped by priority. Lower values are preferred. »
    conditional « targets are evaluated in order. The first matching
                  condition selects the model. »

La troisième est la seule qui regarde la requête, et elle le fait en **CEL**.
Ce module l'évalue pour de bon, avec `cel-python` — pas par comparaison de
chaînes. Une règle qui ne compile pas est signalée comme telle : sur un
proxy, elle empêcherait le démarrage.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import celpy

from jobportal.config import Config


class ErreurDeCEL(Exception):
    """Une expression qui ne compile pas, ou qui ne s'evalue pas."""


class ExtensionAgentgateway(ErreurDeCEL):
    """L'expression utilise une fonction que seul agentgateway fournit."""


# `amont/cel-functions.md`, section « Functions » : agentgateway AJOUTE ces
# fonctions au CEL standard. `cel-python` n'implemente que le standard — une
# expression qui les emploie est donc signalee comme non evaluable ICI,
# plutot que devinee. C'est la difference entre un outil qui se tait et un
# outil qui ment.
EXTENSIONS = (
    "json", "toJson", "unvalidatedJwtPayload", "with", "variables",
    "mapValues", "filterKeys", "merge", "flatten", "flattenRecursive",
    "base64.encode", "base64.decode", "url.encode", "url.decode",
    "form.decode", "form.encode", "sha1.encode", "sha256.encode",
    "md5.encode", "random", "default", "coalesce", "regexReplace",
    "fail", "uuid",
)


def extensions_utilisees(expression: str) -> list[str]:
    """Les fonctions propres a agentgateway qu'une expression appelle."""
    return sorted({f for f in EXTENSIONS if f"{f}(" in expression})


@dataclass
class Decision:
    """Quel modèle a été choisi, et par quelle règle."""

    modele: str
    forme: str
    regle: str = ""
    rang: int = -1


def _programme(expression: str):
    env = celpy.Environment()
    try:
        return env.program(env.compile(expression))
    except Exception as erreur:                        # noqa: BLE001
        raise ErreurDeCEL(f"{expression} → {erreur}") from erreur


def evaluer(expression: str, contexte: dict[str, Any]) -> bool:
    """Évalue une expression CEL et rend un booléen.

    Le contexte est converti en valeurs CEL : `celpy.json_to_cel` transforme
    les dictionnaires Python en tables CEL, faute de quoi l'accès par point
    (`llmRequest.model`) ne résout rien.
    """
    ajoutees = extensions_utilisees(expression)
    if ajoutees:
        raise ExtensionAgentgateway(
            f"{', '.join(ajoutees)} — fonction(s) ajoutee(s) par agentgateway, "
            f"hors CEL standard : non evaluable ici")
    prg = _programme(expression)
    activation = {cle: celpy.json_to_cel(valeur)
                  for cle, valeur in contexte.items()}
    try:
        resultat = prg.evaluate(activation)
    except Exception as erreur:                        # noqa: BLE001
        raise ErreurDeCEL(f"{expression} → {erreur}") from erreur
    return bool(resultat)


def modeles_virtuels(config: Config) -> list[dict[str, Any]]:
    bloc = config.brut.get("llm")
    if not isinstance(bloc, dict):
        return []
    return [m for m in bloc.get("virtualModels") or [] if isinstance(m, dict)]


def modeles_declares(config: Config) -> list[str]:
    bloc = config.brut.get("llm")
    if not isinstance(bloc, dict):
        return []
    return [m.get("name", "") for m in bloc.get("models") or []
            if isinstance(m, dict)]


def visibilite(config: Config, nom: str) -> str:
    """`visibility` — « controls whether clients can request this model
    directly (rather than only via a `virtualModel`) ».
    """
    bloc = config.brut.get("llm")
    for m in (bloc or {}).get("models") or []:
        if isinstance(m, dict) and m.get("name") == nom:
            return m.get("visibility", "(defaut)")
    return "(inconnu)"


def choisir(routage: dict[str, Any], contexte: dict[str, Any]) -> Decision:
    """Applique la forme de routage d'un modèle virtuel à une requête.

    Pour `weighted`, aucune requête n'est nécessaire : la décision est un
    tirage, et ce projet ne tire rien — il rend la répartition attendue sous
    la forme du premier modèle et note la forme. Les deux autres sont
    déterministes, et c'est là que le chapitre 2 mesure.
    """
    if not isinstance(routage, dict):
        raise ErreurDeCEL("routing absent")

    # TODO : appliquer les trois formes — conditional, failover, weighted
    return Decision("", "a completer")


def repartition(routage: dict[str, Any]) -> list[tuple[str, str]]:
    """Ce que la forme de routage promet, lue sans requête.

    Sert au chapitre 2 : on affiche le contrat de chaque forme avant de le
    mettre à l'épreuve.
    """
    pondere = (routage or {}).get("weighted")
    if isinstance(pondere, dict):
        cibles = [c for c in pondere.get("targets") or [] if isinstance(c, dict)]
        total = sum(c.get("weight", 1) for c in cibles) or 1
        return [(c.get("model", ""), f"{c.get('weight', 1) / total:.0%}")
                for c in cibles]
    bascule = (routage or {}).get("failover")
    if isinstance(bascule, dict):
        cibles = sorted((c for c in bascule.get("targets") or []
                         if isinstance(c, dict)),
                        key=lambda c: c.get("priority", 0))
        return [(c.get("model", ""), f"priorite {c.get('priority', 0)}")
                for c in cibles]
    conditionnel = (routage or {}).get("conditional")
    if isinstance(conditionnel, dict):
        return [(c.get("model", ""), (c.get("when") or "(repli)")[:46])
                for c in conditionnel.get("targets") or [] if isinstance(c, dict)]
    return []
