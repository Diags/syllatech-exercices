"""Le `terraform.tfstate` : la carte entre le code et la realite.

C'est la piece que le cours appelle « la source de verite », et c'est
exactement cela : sans elle, un `apply` ne saurait pas qu'un conteneur
existe deja, et il en creerait un second.

Le format ecrit ici reprend celui de Terraform — `version`, `serial`,
`lineage`, et une liste de `resources` portant chacune ses `instances`. Ce
n'est pas de la decoration : c'est ce qui rend le fichier lisible par
quelqu'un qui a deja vu un vrai `tfstate`.

⚠️ **LE STATE CONTIENT LES SECRETS EN CLAIR.** Tout attribut calcule par un
provider — un mot de passe engendre, une cle d'acces — y est ecrit tel
quel. Le chapitre 3 le montre en imprimant le fichier. C'est la raison pour
laquelle on ne le met pas dans Git et qu'on chiffre le backend.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class EtatVerrouille(Exception):
    """Un autre `apply` tient le verrou."""


@dataclass
class Instance:
    """Une instance de ressource : sa cle (`for_each`) et ses attributs."""

    cle: str | None
    attributs: dict[str, Any]


@dataclass
class RessourceEnEtat:
    type: str
    nom: str
    instances: list[Instance] = field(default_factory=list)

    @property
    def adresse(self) -> str:
        return f"{self.type}.{self.nom}"


class Etat:
    """Le fichier d'etat, charge en memoire."""

    VERSION = 4

    def __init__(self, chemin: Path | str) -> None:
        self.chemin = Path(chemin)
        self.serial = 0
        self.lignee = str(uuid.uuid4())
        self.ressources: dict[str, RessourceEnEtat] = {}
        if self.chemin.exists():
            self._charger()

    # -- lecture et ecriture --------------------------------------------

    def _charger(self) -> None:
        donnees = json.loads(self.chemin.read_text(encoding="utf-8"))
        self.serial = donnees.get("serial", 0)
        self.lignee = donnees.get("lineage", self.lignee)
        for brute in donnees.get("resources", []):
            ressource = RessourceEnEtat(brute["type"], brute["name"])
            for instance in brute.get("instances", []):
                ressource.instances.append(Instance(
                    instance.get("index_key"),
                    instance.get("attributes", {})))
            self.ressources[ressource.adresse] = ressource

    def ecrire(self) -> None:
        self.serial += 1
        donnees = {
            "version": self.VERSION,
            "terraform_version": "jobportal-1.0.0",
            "serial": self.serial,
            "lineage": self.lignee,
            "resources": [
                {
                    "mode": "managed",
                    "type": ressource.type,
                    "name": ressource.nom,
                    "provider": "provider[\"syllatech/local\"]",
                    "instances": [
                        {"index_key": instance.cle,
                         "schema_version": 0,
                         "attributes": instance.attributs}
                        for instance in ressource.instances
                    ],
                }
                for ressource in sorted(self.ressources.values(),
                                        key=lambda r: r.adresse)
            ],
        }
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(
            json.dumps(donnees, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8")

    # -- consultation ---------------------------------------------------

    def adresses(self) -> list[str]:
        """Ce que rendrait `terraform state list`."""
        listees: list[str] = []
        for ressource in sorted(self.ressources.values(),
                                key=lambda r: r.adresse):
            for instance in ressource.instances:
                listees.append(ressource.adresse
                               + (f'["{instance.cle}"]'
                                  if instance.cle is not None else ""))
        return listees

    def instance(self, adresse: str, cle: str | None) -> Instance | None:
        ressource = self.ressources.get(adresse)
        if ressource is None:
            return None
        for instance in ressource.instances:
            if instance.cle == cle:
                return instance
        return None

    def poser(self, adresse: str, cle: str | None,
              attributs: dict[str, Any]) -> None:
        type_ressource, _, nom = adresse.partition(".")
        ressource = self.ressources.setdefault(
            adresse, RessourceEnEtat(type_ressource, nom))
        existante = self.instance(adresse, cle)
        if existante is None:
            ressource.instances.append(Instance(cle, attributs))
        else:
            existante.attributs = attributs

    def retirer(self, adresse: str, cle: str | None = None) -> bool:
        """`terraform state rm` : on cesse de suivre, on ne detruit pas."""
        ressource = self.ressources.get(adresse)
        if ressource is None:
            return False
        if cle is None:
            del self.ressources[adresse]
            return True
        avant = len(ressource.instances)
        ressource.instances = [instance for instance in ressource.instances
                               if instance.cle != cle]
        if not ressource.instances:
            del self.ressources[adresse]
        return len(ressource.instances) != avant

    def deplacer(self, source: str, cible: str) -> bool:
        """`terraform state mv` : on renomme l'entree, pas la ressource."""
        ressource = self.ressources.pop(source, None)
        if ressource is None:
            return False
        type_cible, _, nom_cible = cible.partition(".")
        ressource.type = type_cible
        ressource.nom = nom_cible
        self.ressources[cible] = ressource
        return True


class Verrou:
    """Le verrou d'etat — un fichier, comme le fait le backend local.

    ⚠️ Ce que le verrou empeche n'est PAS qu'on lise l'etat : c'est que deux
    `apply` ecrivent en meme temps. Sans lui, deux collegues qui appliquent
    simultanement produisent un etat qui ne decrit ni l'une ni l'autre des
    deux realites — et plus rien ne correspond a rien.
    """

    def __init__(self, chemin_etat: Path | str) -> None:
        self.chemin = Path(str(chemin_etat) + ".lock")

    def prendre(self, qui: str = "moi") -> None:
        # TODO : refuser si le verrou existe deja, sinon l'ecrire avec son detenteur
        pass

    def rendre(self) -> None:
        self.chemin.unlink(missing_ok=True)

    @property
    def pris(self) -> bool:
        return self.chemin.exists()

    def __enter__(self) -> "Verrou":
        self.prendre()
        return self

    def __exit__(self, *_) -> None:
        self.rendre()
