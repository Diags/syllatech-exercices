"""Un cluster factice, avec un incident dedans.

POURQUOI UN CLUSTER FACTICE
---------------------------
Le cours enseigne le *grounding* : un agent ne devine pas l'etat du cluster,
il l'OBSERVE. Pour le mesurer, il faut un etat observable — et un etat qui
contredit ce qu'un modele repondrait de memoire.

L'INCIDENT, ET IL EST RESOLUBLE
-------------------------------
`jobportal-api` redemarre en boucle. Trois observations, et trois
seulement, permettent de conclure :

1. `k8s_get_resources` montre 12 redemarrages et l'etat `CrashLoopBackOff` ;
2. `k8s_get_pod_logs` montre une `OutOfMemoryError` a la fin du journal ;
3. `prometheus_query` montre la memoire du conteneur a 98 % de sa limite.

Un agent qui saute les outils repond a cote — et le chapitre 3 imprime les
deux reponses cote a cote.

⚠️ ENTREE DECLAREE. Ce cluster est un dictionnaire : aucune API n'est
appelee, rien n'est en cours d'execution. Ce que le projet mesure est ce que
l'agent FAIT de ces donnees — quels outils il appelle, dans quel ordre, et
si sa conclusion s'appuie sur ce qu'il a lu.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class ErreurCluster(Exception):
    """Une ressource inexistante, un espace de noms inconnu."""


@dataclass
class Pod:
    nom: str
    espace: str
    etat: str
    redemarrages: int
    image: str
    memoire_limite_mio: int
    journal: list[str] = field(default_factory=list)


@dataclass
class Evenement:
    espace: str
    objet: str
    genre: str            # Normal | Warning
    raison: str
    message: str
    compte: int = 1


@dataclass
class Publication:
    nom: str
    espace: str
    revision: int
    etat: str


class Cluster:
    """Ce que les outils de lecture observent, et ce que ceux d'action font."""

    def __init__(self) -> None:
        self.pods: dict[str, Pod] = {}
        self.evenements_: list[Evenement] = []
        self.publications_: dict[str, Publication] = {}
        self.metriques: dict[str, float] = {}
        self.deploiements: dict[str, int] = {}
        # Tout ce qu'un outil d'ACTION a fait, pour pouvoir le montrer.
        self.journal_des_actions: list[str] = []

    # -- lecture --------------------------------------------------------

    def ressources(self, genre: str = "Pod",
                   espace: str = "default") -> list[dict[str, Any]]:
        if genre != "Pod":
            raise ErreurCluster(
                f"ce cluster factice ne connait que « Pod », pas « {genre} »")
        return [{"nom": p.nom, "etat": p.etat, "redemarrages": p.redemarrages,
                 "image": p.image}
                for p in sorted(self.pods.values(), key=lambda p: p.nom)
                if p.espace == espace]

    def journaux(self, pod: str, lignes: int = 20) -> list[str]:
        if pod not in self.pods:
            raise ErreurCluster(f"pod introuvable : « {pod} »")
        return self.pods[pod].journal[-lignes:]

    def evenements(self, espace: str = "default") -> list[dict[str, Any]]:
        return [{"objet": e.objet, "genre": e.genre, "raison": e.raison,
                 "message": e.message, "compte": e.compte}
                for e in self.evenements_ if e.espace == espace]

    def prometheus(self, requete: str) -> dict[str, Any]:
        if requete not in self.metriques:
            # ⚠️ Une requete PromQL qui ne correspond a rien rend un
            # resultat VIDE, pas une erreur. C'est vrai de Prometheus, et
            # c'est le piege : « aucune donnee » se lit trop vite comme
            # « tout va bien ».
            return {"requete": requete, "resultat": [], "vide": True}
        return {"requete": requete,
                "resultat": [{"valeur": self.metriques[requete]}],
                "vide": False}

    def publications(self, espace: str = "default") -> list[dict[str, Any]]:
        return [{"nom": p.nom, "revision": p.revision, "etat": p.etat}
                for p in self.publications_.values() if p.espace == espace]

    # -- action ---------------------------------------------------------

    def supprimer(self, genre: str, nom: str, espace: str = "default") -> str:
        if nom not in self.pods:
            raise ErreurCluster(f"pod introuvable : « {nom} »")
        del self.pods[nom]
        self.journal_des_actions.append(f"supprime {genre}/{nom}")
        return f"{genre}/{nom} supprime"

    def appliquer_brut(self, manifeste: str) -> str:
        self.journal_des_actions.append("applique un manifeste")
        return "manifeste applique"

    def redimensionner(self, nom: str, repliques: int,
                       espace: str = "default") -> str:
        self.deploiements[nom] = repliques
        self.journal_des_actions.append(f"redimensionne {nom} a {repliques}")
        return f"{nom} redimensionne a {repliques}"

    def annuler(self, publication: str, revision: int) -> str:
        if publication in self.publications_:
            self.publications_[publication].revision = revision
        self.journal_des_actions.append(
            f"annule {publication} vers la revision {revision}")
        return f"{publication} ramene a la revision {revision}"


def avec_incident() -> Cluster:
    """Le cluster du portail de l'emploi, un mauvais jour."""
    cluster = Cluster()
    cluster.pods["jobportal-api-7d4f"] = Pod(
        "jobportal-api-7d4f", "default", "CrashLoopBackOff", 12,
        "registry.exemple.fr/jobportal:2.1.0", 512,
        ["2026-09-15T09:12:04Z  demarrage du contexte Spring",
         "2026-09-15T09:12:31Z  chargement de 41 200 offres en memoire",
         "2026-09-15T09:12:44Z  GC overhead limit approche",
         "2026-09-15T09:12:47Z  java.lang.OutOfMemoryError: Java heap space",
         "2026-09-15T09:12:47Z  arret du conteneur (code 137)"])
    cluster.pods["jobportal-web-5b9c"] = Pod(
        "jobportal-web-5b9c", "default", "Running", 0,
        "registry.exemple.fr/jobportal-web:2.1.0", 256,
        ["2026-09-15T09:10:02Z  ecoute sur :8080",
         "2026-09-15T09:14:10Z  502 depuis jobportal-api"])
    cluster.pods["jobportal-batch-1a2b"] = Pod(
        "jobportal-batch-1a2b", "default", "Running", 0,
        "registry.exemple.fr/jobportal-batch:2.0.4", 1024,
        ["2026-09-15T09:00:00Z  lot du matin termine"])

    cluster.evenements_ = [
        Evenement("default", "pod/jobportal-api-7d4f", "Warning",
                  "BackOff", "Back-off restarting failed container", 12),
        Evenement("default", "pod/jobportal-api-7d4f", "Warning",
                  "OOMKilled", "Container app was OOMKilled", 12),
        Evenement("default", "pod/jobportal-web-5b9c", "Normal",
                  "Pulled", "Container image already present", 1),
    ]
    cluster.metriques = {
        "container_memory_working_set_bytes{pod=\"jobportal-api-7d4f\"}":
            0.98 * 512 * 1024 ** 2,
        "kube_pod_container_status_restarts_total{pod=\"jobportal-api-7d4f\"}":
            12.0,
        "rate(http_requests_total{status=\"502\"}[5m])": 4.7,
    }
    cluster.publications_["jobportal"] = Publication(
        "jobportal", "default", 7, "deployed")
    cluster.deploiements["jobportal-api"] = 3
    return cluster
