"""Docker Compose : le graphe, l'ordre, et ce que `depends_on` n'attend pas.

CE QUE COMPOSE FAIT, ET CE QU'IL NE FAIT PAS
--------------------------------------------
`docker compose up` cree un reseau, monte les volumes et demarre les
services dans l'ordre de leurs dependances. Le piege tient en une phrase,
et il coute une matinee a tout le monde une fois :

    `depends_on: [db]` attend que le conteneur `db` soit **DEMARRE**.
    Il n'attend pas que PostgreSQL accepte des connexions.

Entre les deux, il y a plusieurs secondes — le temps que le moteur de base
de donnees lise ses journaux et ouvre son port. L'application, elle, tente
sa premiere connexion tout de suite, et echoue.

Ce module modelise les deux formes et **date les evenements** : on voit
l'application se connecter avant que la base n'ecoute, puis attendre que
le `healthcheck` passe au vert.

⚠️ LES DUREES SONT DECLAREES. Aucun conteneur ne demarre ici. Chaque
service porte un champ d'extension `x-simulation` disant en combien de
temps il demarre et au bout de combien il accepte des connexions. Comme
`effets.py`, ce sont des ENTREES ; ce qui est mesure, c'est l'ORDRE des
evenements et le verdict de chaque tentative de connexion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import yaml_minimal


class ErreurCompose(Exception):
    """Un cycle, un service inconnu, une variable non definie."""


@dataclass
class Sante:
    """Le `healthcheck` d'un service."""

    commande: list[str]
    intervalle: float = 30.0
    essais: int = 3
    demarrage: float = 0.0

    @property
    def declaree(self) -> bool:
        return bool(self.commande)


@dataclass
class Dependance:
    service: str
    condition: str          # service_started | service_healthy | service_completed_successfully

    @property
    def attend_la_sante(self) -> bool:
        return self.condition == "service_healthy"


@dataclass
class Service:
    nom: str
    image: str | None = None
    construction: str | None = None
    ports: list[str] = field(default_factory=list)
    exposes: list[int] = field(default_factory=list)
    environnement: dict[str, str] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    reseaux: list[str] = field(default_factory=list)
    depend_de: list[Dependance] = field(default_factory=list)
    sante: Sante = field(default_factory=lambda: Sante([]))
    # Entrees declarees (`x-simulation`), voir l'en-tete du module.
    # Toutes comptees depuis la CREATION du conteneur.
    demarre_en: float = 0.2          # le processus a fini de demarrer
    accepte_apres: float = 0.2       # il accepte des connexions entrantes
    se_connecte_apres: float = 0.0   # il ouvre ses connexions sortantes

    @property
    def ports_publies(self) -> list[tuple[int, int]]:
        """« 8080:8080 » — le premier est celui de l'HOTE."""
        paires = []
        for entree in self.ports:
            morceaux = str(entree).split(":")
            if len(morceaux) == 2:
                paires.append((int(morceaux[0]), int(morceaux[1])))
            else:
                paires.append((int(morceaux[0]), int(morceaux[0])))
        return paires


@dataclass
class Projet:
    nom: str
    services: dict[str, Service] = field(default_factory=dict)
    volumes: list[str] = field(default_factory=list)
    reseaux: list[str] = field(default_factory=list)

    @property
    def reseau_par_defaut(self) -> str:
        """Compose cree `<projet>_default` et y joint tout le monde.

        C'est ce reseau qui donne le DNS interne : un service y est
        joignable **par son nom**, jamais par une IP a ecrire quelque part.
        """
        return f"{self.nom}_default"


# ── la lecture ───────────────────────────────────────────────────────────

_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def interpoler(valeur: Any, variables: dict[str, str],
               manquantes: list[str] | None = None) -> Any:
    """`${DB_PASSWORD}` et `${PORT:-8080}`.

    ⚠️ Une variable non definie et sans valeur par defaut devient une
    CHAINE VIDE, avec un avertissement sur la sortie d'erreur — pas une
    erreur. Compose demarre donc, et c'est le service qui echoue plus tard,
    avec un message sans rapport.
    """
    if isinstance(valeur, dict):
        return {cle: interpoler(sous, variables, manquantes)
                for cle, sous in valeur.items()}
    if isinstance(valeur, list):
        return [interpoler(sous, variables, manquantes) for sous in valeur]
    if not isinstance(valeur, str):
        return valeur

    def remplacer(trouve: re.Match[str]) -> str:
        nom, defaut = trouve.group(1), trouve.group(2)
        if nom in variables:
            return variables[nom]
        if defaut is not None:
            return defaut
        if manquantes is not None and nom not in manquantes:
            manquantes.append(nom)
        return ""

    return _VARIABLE.sub(remplacer, valeur)


def lire_env(texte: str) -> dict[str, str]:
    variables: dict[str, str] = {}
    for brute in texte.splitlines():
        ligne = brute.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        variables[cle.strip()] = valeur.strip().strip('"').strip("'")
    return variables


def charger(chemin: Path | str, variables: dict[str, str] | None = None,
            nom_du_projet: str | None = None) -> tuple[Projet, list[str]]:
    """Lit un `compose.yaml` et rend le projet plus les variables manquantes."""
    fichier = Path(chemin)
    env = dict(variables or {})
    fichier_env = fichier.parent / ".env"
    if fichier_env.exists():
        for cle, valeur in lire_env(
                fichier_env.read_text(encoding="utf-8")).items():
            env.setdefault(cle, valeur)

    manquantes: list[str] = []
    brut = yaml_minimal.charger(fichier.read_text(encoding="utf-8")) or {}
    brut = interpoler(brut, env, manquantes)

    projet = Projet(nom_du_projet or brut.get("name")
                    or fichier.parent.name)
    projet.volumes = sorted((brut.get("volumes") or {}).keys())
    projet.reseaux = sorted((brut.get("networks") or {}).keys())

    for nom, description in (brut.get("services") or {}).items():
        projet.services[nom] = _service(nom, description or {})

    for service in projet.services.values():
        for dependance in service.depend_de:
            if dependance.service not in projet.services:
                raise ErreurCompose(
                    f"service « {service.nom} » : « depends_on » cite "
                    f"« {dependance.service} », qui n'existe pas")
    return projet, manquantes


def _service(nom: str, description: dict[str, Any]) -> Service:
    service = Service(nom)
    service.image = description.get("image")
    construction = description.get("build")
    service.construction = (construction.get("context")
                            if isinstance(construction, dict) else construction)
    service.ports = [str(p) for p in (description.get("ports") or [])]
    service.exposes = [int(p) for p in (description.get("expose") or [])]
    service.volumes = [str(v) for v in (description.get("volumes") or [])]
    service.reseaux = [str(r) for r in (description.get("networks") or [])]

    environnement = description.get("environment") or {}
    if isinstance(environnement, list):
        environnement = dict(
            (str(e).split("=", 1) + [""])[:2] for e in environnement)
    service.environnement = {str(c): str(v) if v is not None else ""
                             for c, v in environnement.items()}

    service.depend_de = _dependances(description.get("depends_on"))

    sante = description.get("healthcheck") or {}
    if sante:
        service.sante = Sante(
            [str(m) for m in (sante.get("test") or [])],
            _secondes(sante.get("interval", "30s")),
            int(sante.get("retries", 3)),
            _secondes(sante.get("start_period", "0s")))

    simulation = description.get("x-simulation") or {}
    service.demarre_en = float(simulation.get("demarre_en", 0.2))
    service.accepte_apres = float(
        simulation.get("accepte_apres", service.demarre_en))
    service.se_connecte_apres = float(
        simulation.get("se_connecte_apres", service.demarre_en))
    return service


def _dependances(brut: Any) -> list[Dependance]:
    if not brut:
        return []
    if isinstance(brut, list):
        # ⚠️ LA FORME COURTE. Elle vaut `condition: service_started`, et
        # c'est tout le probleme : « demarre » n'est pas « pret ».
        return [Dependance(str(nom), "service_started") for nom in brut]
    return [Dependance(str(nom), (detail or {}).get("condition",
                                                    "service_started"))
            for nom, detail in brut.items()]


_DUREE = re.compile(r"^(\d+(?:\.\d+)?)(ms|s|m|h)?$")


def _secondes(valeur: Any) -> float:
    if isinstance(valeur, (int, float)):
        return float(valeur)
    trouve = _DUREE.match(str(valeur).strip())
    if trouve is None:
        raise ErreurCompose(f"duree illisible : « {valeur} »")
    nombre = float(trouve.group(1))
    return nombre * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[
        trouve.group(2) or "s"]


# ── l'ordre de demarrage ─────────────────────────────────────────────────

def ordre(projet: Projet) -> list[str]:
    """Un tri topologique : les dependances d'abord.

    ⚠️ Ce tri dit l'ordre dans lequel Compose LANCE les conteneurs. Il ne
    dit rien de leur disponibilite — c'est la distinction que `demarrer()`
    mesure.
    """
    # TODO : trier les services par dependances, et refuser un cycle
    return sorted(projet.services)


@dataclass
class Evenement:
    instant: float
    service: str
    quoi: str
    reussi: bool = True

    def __str__(self) -> str:
        marque = "" if self.reussi else "   ← ECHEC"
        return f"t={self.instant:6.2f}s  {self.service:<10} {self.quoi}{marque}"


def premier_vert(sante: Sante, accepte_a: float) -> float:
    """L'instant du premier `healthcheck` au vert.

    ⚠️ Ce n'est PAS l'instant ou le service devient disponible. Docker
    lance la premiere sonde apres `interval` (ou apres `start_period`),
    puis toutes les `interval`. Le service est donc declare sain au
    premier tick QUI SUIT sa disponibilite reelle — jusqu'a un intervalle
    entier de retard, ajoute a chaque `compose up`.
    """
    # TODO : rendre le premier tick de sonde QUI SUIT la disponibilite
    return accepte_a


def demarrer(projet: Projet) -> list[Evenement]:
    """Deroule un `compose up` et date chaque evenement.

    Un service est lance des que ses dependances sont satisfaites SELON
    LEUR CONDITION — « demarre » pour la forme courte, « sain » pour la
    forme longue — puis il ouvre ses connexions sortantes a l'instant
    declare par `se_connecte_apres`.
    """
    evenements: list[Evenement] = []
    cree_a: dict[str, float] = {}
    demarre_a: dict[str, float] = {}
    accepte_a: dict[str, float] = {}
    sain_a: dict[str, float] = {}

    for nom in ordre(projet):
        service = projet.services[nom]
        depart = 0.0
        for dependance in service.depend_de:
            autre = projet.services[dependance.service]
            if dependance.attend_la_sante:
                if not autre.sante.declaree:
                    raise ErreurCompose(
                        f"« {nom} » attend « {dependance.service} » en bonne "
                        f"sante, mais ce service n'a pas de healthcheck")
                depart = max(depart, sain_a[dependance.service])
            else:
                depart = max(depart, demarre_a[dependance.service])

        cree_a[nom] = depart
        demarre_a[nom] = depart + service.demarre_en
        accepte_a[nom] = depart + service.accepte_apres
        evenements.append(Evenement(depart, nom, "conteneur cree"))
        evenements.append(Evenement(demarre_a[nom], nom, "processus demarre"))
        if service.accepte_apres > service.demarre_en:
            evenements.append(Evenement(accepte_a[nom], nom,
                                        "accepte des connexions"))
        if service.sante.declaree:
            sain_a[nom] = premier_vert(service.sante, accepte_a[nom])
            evenements.append(Evenement(sain_a[nom], nom,
                                        "healthcheck au vert"))

        for dependance in service.depend_de:
            instant = round(depart + service.se_connecte_apres, 3)
            cible = dependance.service
            reussi = instant >= accepte_a[cible]
            detail = "" if reussi else                 f" (elle n'accepte qu'a t={accepte_a[cible]:.2f}s)"
            evenements.append(Evenement(
                instant, nom, f"se connecte a « {cible} »{detail}", reussi))

    return sorted(evenements, key=lambda e: (e.instant, e.service))


def echecs(evenements: list[Evenement]) -> list[Evenement]:
    return [e for e in evenements if not e.reussi]
