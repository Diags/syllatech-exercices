"""Couche A — le schéma que le proxy PUBLIE.

`amont/config.schema.json` est `schema/config.json` du dépôt agentgateway,
copié verbatim. Ce n'est pas une pièce justificative : c'est **le
vérificateur**. Le `schema/README.md` amont le présente ainsi — « The schema
for the configuration file (passed with `--file` to agentgateway) » — et
c'est du JSON Schema draft 2020-12, que `jsonschema` applique tel quel.

Aucune règle n'est transcrite ici. Ce module ne fait que deux choses :
appeler le validateur, et rendre ses erreurs lisibles — parce qu'un schéma à
305 définitions produit, pour une faute de frappe, une cascade de messages
dont un seul compte.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from jobportal.commun import SCHEMA
from jobportal.config import Config

# Un `oneOf` a dix branches peut produire une trentaine de sous-erreurs. On
# en garde les plus parlantes : au-dela, l'outil devient illisible.
MAX_ERREURS_PAR_CAUSE = 3


@functools.lru_cache(maxsize=1)
def document(chemin: Path | None = None) -> dict[str, Any]:
    return json.loads((chemin or SCHEMA).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _controleur() -> Draft202012Validator:
    return Draft202012Validator(document())


def definitions() -> dict[str, Any]:
    return document()["$defs"]


def branches(nom: str) -> list[str]:
    """Les branches d'un `oneOf` de definition, par leur champ requis.

    C'est ainsi que le schema encode une union : LocalRouteBackend a dix
    branches, chacune exigeant une cle differente.
    """
    o = definitions().get(nom, {})
    sorties = []
    for b in o.get("oneOf", []) + o.get("anyOf", []):
        requis = b.get("required") or list(b.get("properties", {}))
        sorties.extend(requis)
    return sorties


def constantes(nom: str) -> list[str]:
    """Les valeurs d'un enum encode en `oneOf` de `const`.

    Builtin, McpPrefixMode et McpStatefulMode sont ecrits ainsi : chaque
    valeur porte sa propre description.
    """
    o = definitions().get(nom, {})
    if "enum" in o:
        return list(o["enum"])
    return [b["const"] for b in o.get("oneOf", []) if "const" in b]


def description(nom: str, constante: str) -> str:
    for b in definitions().get(nom, {}).get("oneOf", []):
        if b.get("const") == constante:
            return b.get("description", "")
    return ""


def defaut(nom: str, champ: str) -> Any:
    """La valeur par defaut d'un champ, telle que le schema la declare."""
    return definitions().get(nom, {}).get("properties", {}) \
        .get(champ, {}).get("default")


def _chemin(erreur) -> str:
    return "/".join(str(x) for x in erreur.absolute_path) or "(racine)"


def _feuilles(erreur) -> list:
    """Toutes les erreurs terminales sous un `anyOf` / `oneOf`.

    Presque tout champ facultatif du schema est un `anyOf: [X, null]` : la
    moitie `null` echoue systematiquement et n'apprend rien. On l'ecarte
    avant de descendre.
    """
    if not erreur.context:
        return [erreur]
    utiles = [s for s in erreur.context
              if not s.message.endswith("is not of type 'null'")]
    sorties = []
    for sous in utiles:
        sorties.extend(_feuilles(sous))
    return sorties or [erreur]


def verifier(config: Config, *, resumer: bool = True) -> list[tuple[str, str]]:
    """Valide une configuration, et rend (chemin, message).

    `resumer=False` rend les erreurs brutes du validateur, telles que
    `jsonschema` les produit — utile pour se convaincre que le resume ne
    cache rien.
    """
    brutes = list(_controleur().iter_errors(config.brut))
    if not resumer:
        return sorted((_chemin(e), e.message) for e in brutes)
    sorties = []
    for erreur in brutes:
        feuilles = _feuilles(erreur)
        # Une branche REFUSEE d'entree (« 'service' is a required property »
        # sur un backend qui n'a pas de `service`) n'apprend rien : elle dit
        # seulement qu'on n'a pas pris CETTE branche-la. On ne la garde que
        # faute de mieux.
        parlantes = [f for f in feuilles
                     if f.validator in ("additionalProperties",
                                        "unevaluatedProperties",
                                        "enum", "const", "type")]
        retenues = parlantes or feuilles
        retenues.sort(key=lambda f: -len(list(f.absolute_path)))
        for feuille in retenues[:MAX_ERREURS_PAR_CAUSE]:
            message = feuille.message
            if feuille is not erreur:
                # On garde la trace du conteneur : sinon « 'url' was
                # unexpected » ne dit pas dans quel backend.
                message = f"{message}  [dans {_chemin(erreur)}]"
            sorties.append((_chemin(feuille), message))
    return sorted(set(sorties))
