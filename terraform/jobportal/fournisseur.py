"""Le provider de ce projet : local, observable, et sans reseau.

Terraform ne sait rien faire seul — ce sont les *providers* qui traduisent
le HCL en appels d'API. Celui-ci ne parle a aucune API : il ecrit un
fichier JSON, `realite.json`, qui joue le role du monde exterieur.

C'est ce qui rend le cours mesurable. On peut :

- comparer le code, l'etat et la realite, et voir les trois diverger ;
- **modifier la realite dans le dos de Terraform**, pour fabriquer une
  derive et regarder le plan la detecter (chapitre 6) ;
- constater qu'un attribut CALCULE par le provider — ici un identifiant et
  un mot de passe — se retrouve en clair dans le state (chapitre 3).

⚠️ Un vrai provider fait davantage : il valide le schema, gere les
`timeouts`, distingue les attributs qui forcent un remplacement de ceux qui
se modifient en place. Ce dernier point, lui, est implante : c'est
`FORCENT_UN_REMPLACEMENT`, et le chapitre 1 le mesure.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ErreurFournisseur(Exception):
    """Un attribut obligatoire manque, ou un port est deja pris."""


@dataclass(frozen=True)
class Schema:
    """Ce qu'un type de ressource accepte, et ce qui force un remplacement."""

    obligatoires: tuple[str, ...]
    facultatifs: tuple[str, ...]
    calcules: tuple[str, ...]
    forcent_un_remplacement: tuple[str, ...]


SCHEMAS: dict[str, Schema] = {
    # Un conteneur : son nom et son image, plus des ports facultatifs.
    # ⚠️ Changer le NOM force un remplacement — on ne renomme pas un
    # conteneur, on en cree un autre et on detruit l'ancien. Changer
    # l'IMAGE, en revanche, se fait en place.
    "conteneur": Schema(
        obligatoires=("nom", "image"),
        facultatifs=("ports", "etiquettes", "memoire"),
        calcules=("id", "mot_de_passe"),
        forcent_un_remplacement=("nom",),
    ),
    # Un reseau : le module du chapitre 4 en cree un.
    "reseau": Schema(
        obligatoires=("nom",),
        facultatifs=("plage",),
        calcules=("id",),
        forcent_un_remplacement=("nom",),
    ),
}


class Realite:
    """Le monde exterieur — un fichier JSON que l'on peut lire et trafiquer."""

    def __init__(self, chemin: Path | str) -> None:
        self.chemin = Path(chemin)
        self.objets: dict[str, dict[str, Any]] = {}
        if self.chemin.exists():
            self.objets = json.loads(self.chemin.read_text(encoding="utf-8"))

    def enregistrer(self) -> None:
        self.chemin.parent.mkdir(parents=True, exist_ok=True)
        self.chemin.write_text(
            json.dumps(self.objets, indent=2, ensure_ascii=False,
                       sort_keys=True) + "\n",
            encoding="utf-8")

    # -- ce que le provider sait faire ----------------------------------

    def creer(self, type_ressource: str,
              attributs: dict[str, Any]) -> dict[str, Any]:
        schema = _schema(type_ressource)
        for obligatoire in schema.obligatoires:
            if attributs.get(obligatoire) in (None, ""):
                raise ErreurFournisseur(
                    f"{type_ressource} : l'attribut « {obligatoire} » "
                    f"est obligatoire")
        identifiant = _identifiant(type_ressource, attributs)
        if identifiant in self.objets:
            raise ErreurFournisseur(
                f"{type_ressource} « {attributs.get('nom')} » existe deja "
                f"dans la realite")
        complets = dict(attributs)
        # Les attributs CALCULES : ceux que le provider decide, et que le
        # code HCL ne peut pas connaitre d'avance.
        complets["id"] = identifiant
        if "mot_de_passe" in schema.calcules:
            complets["mot_de_passe"] = _mot_de_passe(identifiant)
        self.objets[identifiant] = complets
        self.enregistrer()
        return complets

    def modifier(self, identifiant: str,
                 attributs: dict[str, Any]) -> dict[str, Any]:
        if identifiant not in self.objets:
            raise ErreurFournisseur(f"objet introuvable : {identifiant}")
        conserves = {cle: valeur
                     for cle, valeur in self.objets[identifiant].items()
                     if cle in ("id", "mot_de_passe")}
        self.objets[identifiant] = {**attributs, **conserves}
        self.enregistrer()
        return self.objets[identifiant]

    def detruire(self, identifiant: str) -> None:
        self.objets.pop(identifiant, None)
        self.enregistrer()

    def lire(self, identifiant: str) -> dict[str, Any] | None:
        return self.objets.get(identifiant)

    def tout(self) -> dict[str, dict[str, Any]]:
        return dict(self.objets)


def _schema(type_ressource: str) -> Schema:
    schema = SCHEMAS.get(type_ressource)
    if schema is None:
        raise ErreurFournisseur(
            f"type de ressource inconnu : « {type_ressource} ». "
            f"Ce provider connait : {', '.join(sorted(SCHEMAS))}")
    return schema


def _identifiant(type_ressource: str, attributs: dict[str, Any]) -> str:
    return f"{type_ressource}-{attributs.get('nom')}"


def _mot_de_passe(graine: str) -> str:
    """Un secret « engendre par le provider » — donc ecrit dans le state."""
    return hashlib.sha256(graine.encode("utf-8")).hexdigest()[:16]


def force_un_remplacement(type_ressource: str, attribut: str) -> bool:
    return attribut in _schema(type_ressource).forcent_un_remplacement


def attributs_calcules(type_ressource: str) -> tuple[str, ...]:
    return _schema(type_ressource).calcules
