"""Couche A — le schéma que la spécification PUBLIE.

`amont/devContainer.base.schema.json` est le fichier du dépôt
`devcontainers/spec`, copié verbatim. C'est celui que les éditeurs
appliquent à votre `devcontainer.json` ; c'est du JSON Schema draft
2019-09, et `jsonschema` le lit tel quel.

**Deux passes, et elles ne servent pas à la même chose.**

`valide()` applique le schéma tel quel et rend un verdict. C'est la vérité,
sans une ligne de transcription.

`diagnostiquer()` produit un message lisible — et c'est une aide de CE
projet, pas la spécification. La raison tient à la forme du schéma : sa
racine est un `oneOf` de deux branches, dont l'une contient un `oneOf`
imbriqué. Un fichier qui déclare `image` ET `build` échoue donc contre
toutes les branches à la fois, et `jsonschema` remonte des reproches de la
branche Compose — « 'dockerComposeFile' is a required property » — qui
n'ont rien à voir avec ce que l'auteur voulait écrire.

Le diagnostic devine donc l'intention à partir des clés présentes, puis
n'applique que la branche correspondante. Un `oneOf` donne un verdict juste
et un message inutilisable : c'est une leçon en soi, et c'est pourquoi les
deux passes existent séparément.
"""

from __future__ import annotations

import functools
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft201909Validator
from jsonschema.validators import validator_for

from jobportal.commun import SCHEMA, SCHEMA_FEATURE
from jobportal.config import Config

# Les trois formes que la racine du schema distingue, et la definition qui
# decrit chacune.
FORMES = {
    "image": ("imageContainer", True),
    "build": ("dockerfileContainer", True),
    "dockerComposeFile": ("composeContainer", False),
}


@functools.lru_cache(maxsize=2)
def document(chemin: Path | None = None) -> dict[str, Any]:
    return json.loads((chemin or SCHEMA).read_text(encoding="utf-8"))


@functools.lru_cache(maxsize=2)
def _controleur(feature: bool = False):
    """Le validateur que le document DECLARE, pas celui qu'on suppose.

    Les deux schemas de la specification ne sont pas au meme brouillon :
    `devContainer.base.schema.json` est en 2019-09, et
    `devContainerFeature.schema.json` en draft-07. `validator_for` lit la
    cle `$schema` et choisit — c'est la seule facon de ne pas appliquer les
    regles d'un brouillon a l'autre.
    """
    schema = document(SCHEMA_FEATURE if feature else SCHEMA)
    return validator_for(schema)(schema)


def definitions() -> dict[str, Any]:
    return document()["definitions"]


def commun() -> dict[str, Any]:
    return definitions()["devContainerCommon"]["properties"]


def description(champ: str) -> str:
    """La description d'une propriete, telle que le schema l'ecrit."""
    return " ".join((commun().get(champ, {}).get("description") or "").split())


def defaut(champ: str) -> Any:
    return commun().get(champ, {}).get("default")


def enum(champ: str) -> list[Any]:
    return commun().get(champ, {}).get("enum", [])


def enum_de(definition: str, champ: str) -> list[Any]:
    return definitions()[definition]["properties"][champ].get("enum", [])


def _chemin(erreur) -> str:
    return "/".join(str(x) for x in erreur.absolute_path) or "(racine)"


# ─────────────────────────────────────────────────────────────────────────
# Passe 1 — le schema publie, tel quel
# ─────────────────────────────────────────────────────────────────────────

def valide(config: Config) -> bool:
    """Le verdict du schema publie. Aucune interpretation."""
    return _controleur().is_valid(config.brut)


def erreurs_brutes(config: Config) -> list[tuple[str, str]]:
    """Ce que `jsonschema` rend, sans tri ni choix.

    A regarder une fois : un `oneOf` de `oneOf` produit des reproches qui
    designent la mauvaise branche.
    """
    return sorted((_chemin(e), e.message)
                  for e in _controleur().iter_errors(config.brut))


# ─────────────────────────────────────────────────────────────────────────
# Passe 2 — le diagnostic lisible
# ─────────────────────────────────────────────────────────────────────────

def _proprietes_admises(formes: list[str]) -> set[str]:
    d = definitions()
    admises = set(d["devContainerCommon"]["properties"])
    for forme in formes:
        nom, non_compose = FORMES[forme]
        admises |= set(d[nom].get("properties", {}))
        for branche in d[nom].get("oneOf", []):
            admises |= set(branche.get("properties", {}))
        if non_compose:
            admises |= set(d["nonComposeBase"]["properties"])
    return admises


@functools.lru_cache(maxsize=8)
def _controleur_de_forme(forme: str) -> Draft201909Validator:
    nom, non_compose = FORMES[forme]
    refs = [{"$ref": "#/definitions/devContainerCommon"},
            {"$ref": f"#/definitions/{nom}"}]
    if non_compose:
        refs.append({"$ref": "#/definitions/nonComposeBase"})
    return Draft201909Validator(
        {"allOf": refs, "definitions": definitions()})


def formes_declarees(config: Config) -> list[str]:
    return [f for f in FORMES if f in config.brut]


def diagnostiquer(config: Config) -> list[tuple[str, str]]:
    """Un message par faute, dans le vocabulaire de l'auteur.

    ⚠️ Cette passe est une aide de ce projet. Le verdict, lui, vient de
    `valide()` — et les deux se contredisent parfois : le diagnostic peut
    trouver zero faute sur un fichier que le schema refuse, quand la faute
    est justement de ne declarer aucun point de depart.
    """
    formes = formes_declarees(config)
    sorties: list[tuple[str, str]] = []

    if not formes:
        sorties.append(("(racine)",
                        "aucun point de depart : il faut `image`, `build` "
                        "ou `dockerComposeFile`"))
    elif len(formes) > 1:
        sorties.append(("(racine)",
                        f"{' et '.join(formes)} sont declares ensemble — "
                        f"les trois points de depart s'excluent"))

    for forme in formes:
        for erreur in _controleur_de_forme(forme).iter_errors(config.brut):
            sorties.append((_chemin(erreur), erreur.message))

    admises = _proprietes_admises(formes or list(FORMES))
    for cle in config.brut:
        if cle not in admises:
            sorties.append((cle, f"propriete inconnue : {cle!r}"))

    return sorted(set(sorties))


def verifier(config: Config) -> list[tuple[str, str]]:
    """Le diagnostic, mais seulement si le schema refuse vraiment.

    Un fichier que le schema accepte ne doit produire aucun message : sinon
    l'outil crie sur des configurations correctes, et on cesse de l'ecouter.
    """
    if valide(config):
        return []
    return diagnostiquer(config) or [
        ("(racine)", "refuse par le schema publie, sans cause isolable — "
                     "voir `--brut`")]


def verifier_feature(manifeste: dict[str, Any]) -> list[tuple[str, str]]:
    """Valide un `devcontainer-feature.json` contre SON schema publie."""
    return sorted({(_chemin(e), e.message)
                   for e in _controleur(True).iter_errors(manifeste)})
