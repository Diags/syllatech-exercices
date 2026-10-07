"""Un `devcontainer.json`, lu et interrogé.

Le schéma publié décrit la configuration comme un `oneOf` à deux branches,
dont la première est elle-même un `oneOf` : **compose**, ou **non-compose**
— et dans ce second cas, **image** ou **build**. C'est la traduction, en
JSON Schema, de la phrase du chapitre 1 : « ces trois propriétés
s'excluent ».

Une conséquence qu'on ne voit pas en lisant : `shutdownAction` n'accepte pas
les mêmes valeurs des deux côtés. `stopContainer` pour une image ou un
Dockerfile, `stopCompose` pour une pile Compose. Écrire l'un à la place de
l'autre est refusé par le schéma.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jobportal import jsonc

# Les trois points de depart, dans l'ordre ou le chapitre 1 les presente.
POINTS_DE_DEPART = ("image", "build", "dockerComposeFile")

# devContainerCommon : les six commandes du cycle de vie, dans l'ordre que
# leurs propres descriptions imposent (chacune cite sa voisine).
COMMANDES = ("initializeCommand", "onCreateCommand", "updateContentCommand",
             "postCreateCommand", "postStartCommand", "postAttachCommand")

# Les chemins qui se resolvent par rapport au FICHIER, pas a la racine.
CHEMINS_RELATIFS_AU_FICHIER = ("build.dockerfile", "build.context",
                               "dockerComposeFile")


@dataclass
class Config:
    """La description, et ce qu'on peut en dire sans rien construire."""

    brut: dict[str, Any]
    fichier: Path | None = None

    @property
    def nom(self) -> str:
        return self.brut.get("name") or "(sans nom)"

    @property
    def depart(self) -> str:
        """Lequel des trois points de depart est declare."""
        poses = [p for p in POINTS_DE_DEPART if p in self.brut]
        if not poses:
            return "(aucun — configuration de metadonnees seulement)"
        return " + ".join(poses)

    @property
    def compose(self) -> bool:
        return "dockerComposeFile" in self.brut

    @property
    def construction(self) -> dict[str, Any]:
        b = self.brut.get("build")
        return b if isinstance(b, dict) else {}

    @property
    def features(self) -> dict[str, Any]:
        f = self.brut.get("features")
        return f if isinstance(f, dict) else {}

    @property
    def ordre_impose(self) -> list[str]:
        o = self.brut.get("overrideFeatureInstallOrder")
        return [str(x) for x in o] if isinstance(o, list) else []

    def commande(self, nom: str) -> Any:
        return self.brut.get(nom)

    @property
    def commandes_posees(self) -> list[str]:
        return [c for c in COMMANDES if c in self.brut]

    @property
    def attend(self) -> str:
        """`waitFor` — « The default is "updateContentCommand". »"""
        return self.brut.get("waitFor") or "updateContentCommand"

    @property
    def attend_est_ecrit(self) -> bool:
        return "waitFor" in self.brut

    def fichiers_compose(self) -> list[str]:
        f = self.brut.get("dockerComposeFile")
        if isinstance(f, str):
            return [f]
        return [str(x) for x in f] if isinstance(f, list) else []

    def ports(self) -> list[Any]:
        p = self.brut.get("forwardPorts")
        return p if isinstance(p, list) else []

    def ports_etiquetes(self) -> dict[str, Any]:
        a = self.brut.get("portsAttributes")
        return a if isinstance(a, dict) else {}

    def montages(self) -> list[Any]:
        m = self.brut.get("mounts")
        return m if isinstance(m, list) else []


def charger(chemin: Path | str) -> Config:
    chemin = Path(chemin)
    return Config(jsonc.charger(chemin), chemin)


def depuis_texte(texte: str, fichier: Path | None = None) -> Config:
    return Config(jsonc.charger_texte(texte), fichier)
