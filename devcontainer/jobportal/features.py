"""L'ordre d'installation des Features — l'algorithme, transcrit.

`amont/feature-dependencies.md` le spécifie en trois étapes, et assez
précisément pour être implanté ligne à ligne :

    (B1) construire le graphe : `dependsOn` est une dépendance DURE et
         RÉCURSIVE — la Feature exigée entre dans la file même si personne
         ne l'a demandée. `installsAfter` est une dépendance MOLLE et NON
         récursive : son arête est retirée si la cible n'est pas déjà dans
         la file.

    (B2) attribuer un `roundPriority` : 0 par défaut, et `n - idx` pour
         chaque Feature nommée dans `overrideFeatureInstallOrder`.

    (B3) trier par tours : à chaque tour, on retient les Features dont
         toutes les dépendances sont déjà installées ; on n'en valide que
         celles qui ont le `roundPriority` MAXIMAL du tour ; les autres
         retournent dans la file. Un tour qui n'installe rien est une
         erreur — cycle.

Les manifestes de `amont/features/` sont les vrais : les relations qu'on
mesure ici sont celles des Features officielles, pas d'un exemple inventé.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from jobportal.commun import FEATURES_AMONT


class CycleDeDependances(Exception):
    """« If there is ever a round where no elements are added to
    `installationOrder`, the algorithm should terminate and return an error. »
    """


def nom_qualifie(identifiant: str) -> str:
    """L'identifiant sans sa version ni son digest.

    C'est sous cette forme que `installsAfter` et
    `overrideFeatureInstallOrder` designent une Feature — « l'identifiant
    s'ecrit sans la version : c'est la Feature qu'on ordonne, pas une de ses
    versions ». Attention au « : » d'un port dans une URL : on ne coupe que
    sur le DERNIER segment.
    """
    for separateur in ("@sha256:", "@"):
        if separateur in identifiant:
            identifiant = identifiant.split(separateur, 1)[0]
    dernier = identifiant.rsplit("/", 1)[-1]
    if ":" in dernier:
        base = identifiant[:len(identifiant) - len(dernier)]
        return base + dernier.split(":", 1)[0]
    return identifiant


def etiquette(identifiant: str) -> str:
    """La version demandee, ou « latest » si elle est omise."""
    dernier = identifiant.rsplit("/", 1)[-1]
    if "@" in identifiant:
        return identifiant.split("@", 1)[1]
    if ":" in dernier:
        return dernier.split(":", 1)[1]
    return "latest"


@dataclass
class Feature:
    """Une Feature dans la file, avec ses options et ses deux jeux d'aretes."""

    identifiant: str
    options: dict[str, Any] = field(default_factory=dict)
    manifeste: dict[str, Any] = field(default_factory=dict)
    demandee: bool = True            # posee par l'utilisateur, ou tiree
    priorite: int = 0                # roundPriority — (B2)

    @property
    def qualifie(self) -> str:
        return nom_qualifie(self.identifiant)

    @property
    def dures(self) -> list[str]:
        """`dependsOn` — les cles sont des identifiants complets."""
        d = self.manifeste.get("dependsOn")
        return list(d) if isinstance(d, dict) else []

    @property
    def molles(self) -> list[str]:
        """`installsAfter` — des identifiants sans version."""
        a = self.manifeste.get("installsAfter")
        return [str(x) for x in a] if isinstance(a, list) else []

    @property
    def locale(self) -> bool:
        """« For local Features, each Feature is considered unique. »"""
        return self.identifiant.startswith((".", "/"))

    def cle(self) -> tuple:
        """Feature Equality, dans la limite de ce projet.

        L'amont compare les digests de manifeste ; ici on n'a pas de
        registre, donc on compare (identifiant, options). Une Feature locale
        n'est jamais egale a une autre — d'ou l'identite d'objet.
        """
        if self.locale:
            return ("local", id(self))
        return (self.identifiant, tuple(sorted(self.options.items(),
                                               key=lambda kv: str(kv))))

    def etiquette_triable(self) -> tuple:
        """« from oldest to newest tag (`latest` being the "most new") »."""
        t = etiquette(self.identifiant)
        return (1, "") if t == "latest" else (0, t)

    def __str__(self) -> str:
        court = self.qualifie.rsplit("/", 1)[-1]
        return court if not self.options else \
            f"{court}({','.join(f'{c}={v}' for c, v in sorted(self.options.items()))})"


def catalogue(dossier: Path | None = None) -> dict[str, dict[str, Any]]:
    """Les manifestes disponibles, indexes par nom qualifie.

    En vrai, l'outil va les chercher au registre OCI. Ici ils sont sur le
    disque — c'est la seule difference, et elle ne change pas l'ordre.
    """
    index = {}
    for chemin in sorted((dossier or FEATURES_AMONT).glob("*.json")):
        manifeste = json.loads(chemin.read_text(encoding="utf-8"))
        index[f"ghcr.io/devcontainers/features/{chemin.stem}"] = manifeste
    return index


def _manifeste_de(identifiant: str,
                  index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return index.get(nom_qualifie(identifiant), {})


# ─────────────────────────────────────────────────────────────────────────
# (B1) construction du graphe
# ─────────────────────────────────────────────────────────────────────────

def construire(demandees: dict[str, dict[str, Any]],
               index: dict[str, dict[str, Any]] | None = None) -> list[Feature]:
    """(B1) — l'accumulateur de toutes les Features a installer.

    « The set of Features to be installed is the union of user-defined
    Features and their dependencies. » `dependsOn` est donc reinjecte dans
    la file et resolu recursivement ; `installsAfter` ne l'est pas.
    """
    index = catalogue() if index is None else index
    # TODO : accumuler les Features et resoudre `dependsOn` recursivement
    return [Feature(i, o or {}, _manifeste_de(i, index))
            for i, o in demandees.items()]


# ─────────────────────────────────────────────────────────────────────────
# (B2) roundPriority
# ─────────────────────────────────────────────────────────────────────────

def prioriser(features: list[Feature], ordre_impose: list[str]) -> None:
    """(B2) — « given `n` Features in the `overrideFeatureInstallOrder`
    array, assign a `roundPriority` of `n - idx` ».

    Modifie les Features en place, comme l'amont decrit une annotation du
    graphe.
    """
    # TODO : donner a chaque Feature nommee une priorite de n - index
    return


# ─────────────────────────────────────────────────────────────────────────
# (B3) tri par tours
# ─────────────────────────────────────────────────────────────────────────

def _tri_stable(tour: list[Feature]) -> list[Feature]:
    """Round Stable Sort, dans la limite de ce qu'on peut comparer ici.

    L'amont trie sur cinq criteres successifs ; les deux derniers demandent
    un registre (digest). On applique les trois premiers : nom qualifie,
    puis etiquette, puis nombre d'options definies par l'utilisateur — puis
    cles et valeurs d'options.
    """
    return sorted(tour, key=lambda f: (
        f.qualifie,
        f.etiquette_triable(),
        -len(f.options),
        sorted(f.options),
        sorted(str(v) for v in f.options.values()),
    ))


@dataclass
class Tour:
    numero: int
    candidates: list[Feature]
    retenues: list[Feature]
    priorite_max: int


def ordonner(features: list[Feature]) -> tuple[list[Feature], list[Tour]]:
    """(B3) — le tri par tours. Rend (ordre d'installation, journal).

    Le journal existe pour le chapitre 3 : un ordre sans ses tours ne
    s'explique pas, et c'est precisement ce qu'on veut pouvoir expliquer
    quand deux Features se genent.
    """
    # « remove all `installsAfter` directed edges that do not correspond
    # with a Feature in the `worklist` that is set to be installed »
    presents = {f.qualifie for f in features}
    exigences = {}
    for feature in features:
        dures = {nom_qualifie(d) for d in feature.dures}
        molles = {nom_qualifie(m) for m in feature.molles} & presents
        exigences[id(feature)] = (dures | molles) - {feature.qualifie}

    file = list(features)
    ordre: list[Feature] = []
    journal: list[Tour] = []
    installes: set[str] = set()

    # TODO : trier par tours — dependances satisfaites, puis priorite maximale
    return list(file), []


def resoudre(demandees: dict[str, dict[str, Any]],
             ordre_impose: list[str] | None = None,
             index: dict[str, dict[str, Any]] | None = None
             ) -> tuple[list[Feature], list[Tour]]:
    """Les trois etapes, dans l'ordre de la specification."""
    features = construire(demandees, index)
    prioriser(features, ordre_impose or [])
    return ordonner(features)
