"""Le plan : la difference entre ce qu'on veut et ce qui est.

C'est le cœur de Terraform, et c'est un algorithme de quelques dizaines de
lignes. Pour chaque adresse :

- elle est voulue et absente de l'etat  → **creation** (`+`) ;
- elle est dans l'etat et plus voulue   → **destruction** (`-`) ;
- elle est dans les deux, identique     → **rien** ;
- elle est dans les deux, differente    → **modification** (`~`)… sauf si
  l'un des attributs modifies force un remplacement, auquel cas c'est une
  **destruction suivie d'une creation** (`-/+`).

⚠️ Cette derniere ligne est celle qui coute cher en production. Un
changement d'apparence anodine — renommer une ressource — detruit et
recree, avec la coupure que cela suppose. C'est pour la voir venir qu'on
lit le plan avant d'appliquer, et le chapitre 1 la mesure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .configuration import Configuration, InstanceVoulue
from .etat import Etat
from .fournisseur import attributs_calcules, force_un_remplacement


class Action(Enum):
    CREER = "+"
    MODIFIER = "~"
    REMPLACER = "-/+"
    DETRUIRE = "-"

    @property
    def libelle(self) -> str:
        return {"+": "creation", "~": "modification",
                "-/+": "remplacement", "-": "destruction"}[self.value]


@dataclass
class Changement:
    action: Action
    adresse: str
    avant: dict[str, Any] = field(default_factory=dict)
    apres: dict[str, Any] = field(default_factory=dict)
    raisons: list[str] = field(default_factory=list)
    instance: InstanceVoulue | None = None
    cle: str | None = None
    empeche_la_destruction: bool = False


@dataclass
class Plan:
    changements: list[Changement] = field(default_factory=list)
    sorties: dict[str, Any] = field(default_factory=dict)

    @property
    def vide(self) -> bool:
        return not self.changements

    def compter(self, action: Action) -> int:
        return sum(1 for c in self.changements if c.action is action)

    @property
    def resume(self) -> str:
        """La ligne finale de `terraform plan`, mot pour mot.

        ⚠️ Un REMPLACEMENT compte des DEUX cotes — une destruction et une
        creation — parce que c'est bien ce qui se passe. Terraform fait
        pareil, et c'est ce qui explique un total qui semble parfois plus
        grand que le nombre de ressources.
        """
        # >>> depart: rendre la ligne de resume — un remplacement compte des DEUX cotes
        #     return ""
        if self.vide:
            return ("No changes. Your infrastructure matches the "
                    "configuration.")
        remplacements = self.compter(Action.REMPLACER)
        return (f"Plan: {self.compter(Action.CREER) + remplacements} to add, "
                f"{self.compter(Action.MODIFIER)} to change, "
                f"{self.compter(Action.DETRUIRE) + remplacements} "
                f"to destroy.")
        # <<<


class DestructionEmpechee(Exception):
    """`prevent_destroy` a fait son travail."""


def calculer(configuration: Configuration, etat: Etat) -> Plan:
    """La difference entre le code et l'etat."""
    plan = Plan(sorties=dict(configuration.sorties))
    voulues = {instance.adresse_complete: instance
               for instance in configuration.instances}

    # Ce qui existe dans l'etat, adresse par adresse.
    existantes: dict[str, tuple[str, str | None, dict[str, Any]]] = {}
    for ressource in etat.ressources.values():
        for instance in ressource.instances:
            cle = instance.cle
            adresse = ressource.adresse + (
                f'["{cle}"]' if cle is not None and not str(cle).isdigit()
                else (f"[{cle}]" if cle is not None else ""))
            existantes[adresse] = (ressource.adresse, cle, instance.attributs)

    # >>> depart: pour chaque adresse, choisir entre creation, destruction, modification et remplacement
    #     pass
    for adresse in sorted(set(voulues) | set(existantes)):
        voulue = voulues.get(adresse)
        presente = existantes.get(adresse)

        if voulue is not None and presente is None:
            plan.changements.append(Changement(
                Action.CREER, adresse, apres=voulue.attributs,
                instance=voulue, cle=voulue.cle))
            continue

        if voulue is None and presente is not None:
            _, cle, attributs = presente
            plan.changements.append(Changement(
                Action.DETRUIRE, adresse, avant=attributs, cle=cle))
            continue

        assert voulue is not None and presente is not None
        _, cle, attributs = presente
        differences = _differences(voulue.type, attributs, voulue.attributs)
        if not differences:
            continue
        remplacants = [nom for nom in differences
                       if force_un_remplacement(voulue.type, nom)]
        action = Action.REMPLACER if remplacants else Action.MODIFIER
        raisons = [
            f"{nom} : {attributs.get(nom)!r} → {voulue.attributs.get(nom)!r}"
            + (" (force un remplacement)"
               if nom in remplacants else "")
            for nom in differences
        ]
        plan.changements.append(Changement(
            action, adresse, avant=attributs, apres=voulue.attributs,
            raisons=raisons, instance=voulue, cle=cle,
            empeche_la_destruction=voulue.empeche_la_destruction))
    # <<<

    return plan


def _differences(type_ressource: str, avant: dict[str, Any],
                 apres: dict[str, Any]) -> list[str]:
    """Les attributs qui changent — hors attributs calcules.

    ⚠️ Les attributs CALCULES par le provider (`id`, `mot_de_passe`) sont
    exclus : ils ne figurent pas dans le code, et les comparer ferait
    apparaitre une modification a chaque plan.
    """
    # >>> depart: comparer les attributs, en ignorant ceux que le provider calcule
    #     return []
    ignores = set(attributs_calcules(type_ressource))
    noms = (set(avant) | set(apres)) - ignores
    return sorted(nom for nom in noms
                  if _normaliser(avant.get(nom)) != _normaliser(apres.get(nom)))
    # <<<


def _normaliser(valeur: Any) -> Any:
    """Compare a la valeur pres, pas a la representation pres."""
    if isinstance(valeur, (list, tuple)):
        return [_normaliser(element) for element in valeur]
    if isinstance(valeur, dict):
        return {cle: _normaliser(sous) for cle, sous in sorted(valeur.items())}
    if isinstance(valeur, bool):
        return valeur
    if isinstance(valeur, (int, float)):
        return float(valeur)
    return valeur


def rendre(plan: Plan) -> list[str]:
    """Le plan, tel qu'on le lit dans un terminal."""
    lignes: list[str] = []
    if plan.vide:
        lignes.append(plan.resume)
        return lignes
    for changement in plan.changements:
        lignes.append(f"  {changement.action.value} {changement.adresse}"
                      f"   ({changement.action.libelle})")
        for raison in changement.raisons:
            lignes.append(f"      ~ {raison}")
    lignes.append("")
    lignes.append(plan.resume)
    return lignes
