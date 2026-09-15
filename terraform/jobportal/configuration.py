"""Du HCL analyse a une liste d'instances de ressources voulues.

C'est le premier temps d'un `plan` : lire les fichiers, valider les
variables, derouler les `for_each` et les `count`, et produire la liste
plate de ce que l'on veut — chaque element portant son *adresse* complete,
par exemple `conteneur.app["prod"]`.

⚠️ **`for_each` et `count` ne produisent PAS la meme adresse**, et c'est
toute la difference que le chapitre 2 mesure :

- `for_each` indexe par CLE : `conteneur.app["staging"]` ;
- `count` indexe par POSITION : `conteneur.app[1]`.

Retirer un element au milieu d'une liste ne change rien aux cles des
autres ; il decale en revanche toutes les positions suivantes. D'ou des
destructions et des recreations que personne n'avait demandees.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import hcl
from .evaluation import ErreurEvaluation, evaluer


class ErreurConfiguration(Exception):
    """Une variable invalide, un module introuvable, un bloc inattendu."""


@dataclass
class InstanceVoulue:
    """Ce que le code demande : une instance, ses attributs, son adresse."""

    type: str
    nom: str
    cle: str | None
    attributs: dict[str, Any]
    empeche_la_destruction: bool = False
    module: str = ""

    @property
    def adresse(self) -> str:
        prefixe = f"module.{self.module}." if self.module else ""
        return f"{prefixe}{self.type}.{self.nom}"

    @property
    def adresse_complete(self) -> str:
        if self.cle is None:
            return self.adresse
        cle = (f'["{self.cle}"]' if not str(self.cle).isdigit()
               else f"[{self.cle}]")
        return f"{self.adresse}{cle}"


@dataclass
class Configuration:
    """Le resultat de la lecture : instances voulues, outputs, variables."""

    instances: list[InstanceVoulue] = field(default_factory=list)
    sorties: dict[str, Any] = field(default_factory=dict)
    variables: dict[str, Any] = field(default_factory=dict)
    modules: list[str] = field(default_factory=list)

    def par_adresse(self, adresse: str) -> InstanceVoulue | None:
        for instance in self.instances:
            if instance.adresse_complete == adresse:
                return instance
        return None


def charger(dossier: Path | str,
            valeurs: dict[str, Any] | None = None,
            module: str = "") -> Configuration:
    """Lit un dossier `.tf` et rend ce qu'il demande."""
    dossier = Path(dossier)
    blocs = hcl.analyser_dossier(dossier)
    fournies = dict(valeurs or {})

    variables = _variables(blocs, fournies)
    contexte: dict[str, Any] = {"var": variables}
    contexte["local"] = _locals(blocs, contexte)

    configuration = Configuration(variables=variables)

    # Les ressources d'abord : les outputs peuvent les citer.
    # ⚠️ On garde la liste des ressources declarees DANS CE DOSSIER a part.
    # Les outputs d'un module citent `reseau.ce`, pas
    # `module.x.reseau.ce` : a l'interieur d'un module, les ressources
    # s'appellent par leur nom court. Melanger les deux ferait echouer
    # toute reference d'output dans un module.
    locales: list[InstanceVoulue] = []
    for bloc in blocs:
        if bloc.type == "resource":
            locales.extend(_instances(bloc, contexte, module))
    configuration.instances.extend(locales)

    # Les modules : charges recursivement, avec leurs propres variables.
    for bloc in blocs:
        if bloc.type != "module":
            continue
        nom = bloc.etiquettes[0]
        configuration.modules.append(nom)
        source = evaluer(bloc.attributs.get("source"), contexte)
        if not isinstance(source, str):
            raise ErreurConfiguration(
                f"module « {nom} » : « source » est obligatoire")
        entrees = {cle: evaluer(valeur, contexte)
                   for cle, valeur in bloc.attributs.items()
                   if cle not in ("source", "version")}
        interne = charger(dossier / source, entrees, module=nom)
        configuration.instances.extend(interne.instances)
        contexte.setdefault("module", {})[nom] = interne.sorties

    # Les ressources deviennent consultables par les outputs.
    contexte.update(_par_type(locales))

    for bloc in blocs:
        if bloc.type == "output":
            nom = bloc.etiquettes[0]
            configuration.sorties[nom] = evaluer(
                bloc.attributs.get("value"), contexte)

    return configuration


# ── les variables ────────────────────────────────────────────────────────

def _variables(blocs: list[hcl.Bloc],
               fournies: dict[str, Any]) -> dict[str, Any]:
    valeurs: dict[str, Any] = {}
    for bloc in blocs:
        if bloc.type != "variable":
            continue
        nom = bloc.etiquettes[0]
        if nom in fournies:
            valeur = fournies[nom]
        elif "default" in bloc.attributs:
            valeur = evaluer(bloc.attributs["default"], {})
        else:
            raise ErreurConfiguration(
                f"variable « {nom} » : aucune valeur et aucun defaut")
        _verifier_le_type(nom, bloc.attributs.get("type"), valeur)
        valeurs[nom] = valeur

    # Les validations sont evaluees APRES, quand toutes les variables
    # existent : une condition peut en citer une autre.
    for bloc in blocs:
        if bloc.type != "variable":
            continue
        for validation in bloc.enfants("validation"):
            contexte = {"var": valeurs}
            try:
                acceptee = evaluer(validation.attributs.get("condition"),
                                   contexte)
            except ErreurEvaluation as erreur:
                raise ErreurConfiguration(
                    f"variable « {bloc.etiquettes[0]} » : "
                    f"condition invalide — {erreur}") from erreur
            if not acceptee:
                message = evaluer(
                    validation.attributs.get("error_message"), contexte)
                raise ErreurConfiguration(
                    f"variable « {bloc.etiquettes[0]} » : {message}")
    return valeurs


def _verifier_le_type(nom: str, contrainte: Any, valeur: Any) -> None:
    """Le typage de HCL, reduit a ce que ce projet utilise.

    ⚠️ Terraform fait mieux : il CONVERTIT quand c'est possible (un nombre
    ecrit en chaine devient un nombre). Ici on refuse — c'est plus strict
    que Terraform, et c'est dit.
    """
    if contrainte is None:
        return
    texte = _texte_de_type(contrainte)
    attendu = {
        "string": str,
        "number": (int, float),
        "bool": bool,
        "list": list,
        "set": (list, set),
        "map": dict,
        "any": object,
    }
    base = texte.split("(")[0]
    classe = attendu.get(base)
    if classe is None:
        return
    if base == "string" and isinstance(valeur, bool):
        raise ErreurConfiguration(
            f"variable « {nom} » : « string » attendu, booleen recu")
    if not isinstance(valeur, classe):
        raise ErreurConfiguration(
            f"variable « {nom} » : « {texte} » attendu, "
            f"{type(valeur).__name__} recu")


def _texte_de_type(contrainte: Any) -> str:
    if isinstance(contrainte, hcl.Reference):
        return ".".join(contrainte.chemin)
    if isinstance(contrainte, hcl.Appel):
        arguments = ", ".join(_texte_de_type(a) for a in contrainte.arguments)
        return f"{contrainte.nom}({arguments})"
    return str(contrainte)


def _locals(blocs: list[hcl.Bloc], contexte: dict[str, Any]) -> dict[str, Any]:
    valeurs: dict[str, Any] = {}
    for bloc in blocs:
        if bloc.type != "locals":
            continue
        for nom, expression in bloc.attributs.items():
            valeurs[nom] = evaluer(expression,
                                   {**contexte, "local": valeurs})
    return valeurs


# ── les ressources ───────────────────────────────────────────────────────

_RESERVES = {"for_each", "count", "depends_on", "provider", "lifecycle"}


def _instances(bloc: hcl.Bloc, contexte: dict[str, Any],
               module: str) -> list[InstanceVoulue]:
    type_ressource, nom = bloc.etiquettes[0], bloc.etiquettes[1]
    lifecycle = bloc.enfant("lifecycle")
    empeche = bool(evaluer(lifecycle.attributs.get("prevent_destroy", False),
                           contexte)) if lifecycle else False

    # TODO : derouler `for_each` (adresse par CLE) et `count` (adresse par POSITION)
    return [InstanceVoulue(type_ressource, nom, None,
                           _attributs(bloc, contexte), empeche, module)]


def _attributs(bloc: hcl.Bloc, contexte: dict[str, Any]) -> dict[str, Any]:
    attributs = {cle: evaluer(valeur, contexte)
                 for cle, valeur in bloc.attributs.items()
                 if cle not in _RESERVES}
    # Les blocs imbriques deviennent des listes d'objets — c'est ainsi que
    # Terraform represente un `ports { ... }` repete.
    for interne in bloc.blocs:
        if interne.type in ("lifecycle", "validation"):
            continue
        attributs.setdefault(interne.type, []).append(
            {cle: evaluer(valeur, contexte)
             for cle, valeur in interne.attributs.items()})
    return attributs


def _par_type(instances: list[InstanceVoulue]) -> dict[str, Any]:
    """Rend les ressources consultables : `conteneur.app["prod"].nom`."""
    par_type: dict[str, Any] = {}
    for instance in instances:
        ressources = par_type.setdefault(instance.type, {})
        if instance.cle is None:
            ressources[instance.nom] = instance.attributs
        else:
            ressources.setdefault(instance.nom, {})[instance.cle] = \
                instance.attributs
    return par_type
