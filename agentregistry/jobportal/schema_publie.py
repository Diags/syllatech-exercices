"""Couche A — le schema que le registre PUBLIE.

`schema/openapi.yaml` est le document OpenAPI 3.1 du depot amont, copie
verbatim (agentregistry-dev/agentregistry, commit 82bbd6c). Rien n'y est
transcrit : c'est le contrat que le serveur publie et que n'importe quel
generateur de client consomme.

OpenAPI 3.1 EST du JSON Schema 2020-12 — on peut donc valider un manifeste
contre `#/components/schemas/MCPServer` sans rien reecrire. C'est le seul
niveau de ce projet ou la fidelite a l'amont ne se discute pas.

Sa portee, en revanche, se discute : le chapitre 3 mesure ce qu'il laisse
passer, et la couche B (`regles.py`) dit pourquoi.
"""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from jobportal.commun import SCHEMA
from jobportal.manifeste import Document

URN = "urn:agentregistry:openapi"


@functools.lru_cache(maxsize=1)
def document(chemin: Path | None = None) -> dict[str, Any]:
    """Le document OpenAPI, charge une fois."""
    return yaml.safe_load((chemin or SCHEMA).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=1)
def _registre() -> Registry:
    ressource = Resource(contents=document(), specification=DRAFT202012)
    return Registry().with_resource(URN, ressource)


@functools.lru_cache(maxsize=32)
def _controleur(type_: str) -> Draft202012Validator:
    return Draft202012Validator(
        {"$ref": f"{URN}#/components/schemas/{type_}"}, registry=_registre())


def types_publies() -> list[str]:
    """Les types qui ont un schema d'enveloppe dans le document publie.

    Un schema d'enveloppe porte apiVersion + kind + metadata + spec ; les
    autres composants (MCPPackage, ResourceRef…) sont des morceaux.
    """
    schemas = document()["components"]["schemas"]
    return sorted(
        nom for nom, s in schemas.items()
        if isinstance(s, dict)
        and {"apiVersion", "kind", "metadata", "spec"} <= set(s.get("properties", {}))
    )


def requis(type_: str, chemin_schema: str = "") -> list[str]:
    """Les champs que le schema publie declare obligatoires.

    `chemin_schema` permet de descendre : requis("MCPServer", "spec") rend les
    champs obligatoires de MCPServerSpec.
    """
    schemas = document()["components"]["schemas"]
    courant = schemas.get(type_, {})
    for segment in filter(None, chemin_schema.split(".")):
        prop = courant.get("properties", {}).get(segment, {})
        ref = prop.get("$ref")
        courant = schemas.get(ref.rsplit("/", 1)[-1], {}) if ref else prop
    return list(courant.get("required", []))


def verifier(doc: Document) -> list[tuple[str, str]]:
    """Valide un document contre son schema publie.

    Rend une liste de (chemin, message). Un type inconnu du document publie
    est signale comme tel : c'est le cas d'un `kind` mal orthographie, que
    rien d'autre n'attrape.
    """
    if doc.type not in document()["components"]["schemas"]:
        return [("kind", f"type inconnu du schema publie : {doc.type!r}")]
    erreurs = []
    for e in _controleur(doc.type).iter_errors(doc.brut):
        chemin = ".".join(str(x) for x in e.absolute_path) or "(racine)"
        erreurs.append((chemin, e.message))
    return sorted(erreurs)
