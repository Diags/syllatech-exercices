"""Le serveur d'outils, et la seule question qui compte : LIRE ou AGIR.

CE QUE KAGENT FOURNIT
---------------------
Un `kagent-tool-server` deja outille pour l'ecosysteme cloud-native :
ressources et journaux Kubernetes, requetes Prometheus, Helm, Argo, Istio.
L'idee est de donner a l'agent les memes gestes qu'un SRE humain, mais par
des appels d'outils TRACES.

LA LIGNE QUI SEPARE TOUT
------------------------
Chaque outil est d'un des deux cotes : il **lit** ou il **agit**. Un agent
qui ne recoit que des outils de lecture ne peut rien casser, quoi que le
modele decide — et il peut deja diagnostiquer. C'est la raison pour laquelle
on commence toujours par la lecture seule, et pourquoi l'elargissement est
un geste separe.

⚠️ ENTREE DECLAREE. Ce catalogue est une transcription abregee de celui du
`kagent-tool-server` : on garde les outils dont le cours parle. Le
classement lecture/action, lui, est une propriete de chaque outil, pas une
opinion — `k8s_delete_resource` supprime, quelle que soit la facon dont on
le presente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

LECTURE = "lecture"
ACTION = "action"


class ErreurOutil(Exception):
    """Un outil inconnu, ou appele sans permission."""


@dataclass(frozen=True)
class Outil:
    nom: str
    genre: str                 # lecture | action
    description: str
    executer: Callable[..., Any] = None    # type: ignore[assignment]

    @property
    def dangereux(self) -> bool:
        return self.genre == ACTION


def catalogue(cluster) -> dict[str, Outil]:
    """Les outils, branches sur un cluster factice qu'on peut interroger."""
    return {
        "k8s_get_resources": Outil(
            "k8s_get_resources", LECTURE,
            "liste les ressources d'un genre dans un espace de noms",
            lambda genre="Pod", espace="default":
                cluster.ressources(genre, espace)),
        "k8s_get_pod_logs": Outil(
            "k8s_get_pod_logs", LECTURE,
            "rend les dernieres lignes de journal d'un pod",
            lambda pod="", lignes=20: cluster.journaux(pod, lignes)),
        "k8s_get_events": Outil(
            "k8s_get_events", LECTURE,
            "rend les evenements recents d'un espace de noms",
            lambda espace="default": cluster.evenements(espace)),
        "prometheus_query": Outil(
            "prometheus_query", LECTURE,
            "evalue une requete PromQL instantanee",
            lambda requete="": cluster.prometheus(requete)),
        "helm_list_releases": Outil(
            "helm_list_releases", LECTURE,
            "liste les publications Helm",
            lambda espace="default": cluster.publications(espace)),
        # ── de l'autre cote de la ligne ──────────────────────────────────
        "k8s_delete_resource": Outil(
            "k8s_delete_resource", ACTION,
            "⚠️ supprime une ressource",
            lambda genre="Pod", nom="", espace="default":
                cluster.supprimer(genre, nom, espace)),
        "k8s_apply_manifest": Outil(
            "k8s_apply_manifest", ACTION,
            "⚠️ applique un manifeste",
            lambda manifeste="": cluster.appliquer_brut(manifeste)),
        "k8s_scale_deployment": Outil(
            "k8s_scale_deployment", ACTION,
            "⚠️ change le nombre de repliques d'un deploiement",
            lambda nom="", repliques=1, espace="default":
                cluster.redimensionner(nom, repliques, espace)),
        "helm_rollback": Outil(
            "helm_rollback", ACTION,
            "⚠️ annule une publication Helm",
            lambda publication="", revision=1:
                cluster.annuler(publication, revision)),
    }


def lecture_seule(disponibles: dict[str, Outil]) -> list[str]:
    return sorted(nom for nom, outil in disponibles.items()
                  if outil.genre == LECTURE)


def actions(disponibles: dict[str, Outil]) -> list[str]:
    return sorted(nom for nom, outil in disponibles.items()
                  if outil.genre == ACTION)


@dataclass
class Trousseau:
    """Ce qu'UN agent a le droit d'appeler — et rien de plus.

    ⚠️ Deux listes se croisent ici, et leur difference est instructive :
    ce que le SERVEUR expose, et ce que l'AGENT a nomme. Un nom qui figure
    dans le manifeste sans exister sur le serveur ne fait echouer personne :
    l'outil manque simplement, et le modele s'en passe sans le dire.
    """

    disponibles: dict[str, Outil]
    accordes: list[str]

    @property
    def utilisables(self) -> list[str]:
        return [nom for nom in self.accordes if nom in self.disponibles]

    @property
    def introuvables(self) -> list[str]:
        """Nommes dans le manifeste, absents du serveur. Silencieux."""
        # >>> depart: rendre les outils nommes que le serveur n'expose pas
        #     return []
        return [nom for nom in self.accordes if nom not in self.disponibles]
        # <<<

    @property
    def dangereux(self) -> list[str]:
        return [nom for nom in self.utilisables
                if self.disponibles[nom].dangereux]

    @property
    def en_lecture_seule(self) -> bool:
        return not self.dangereux

    def appeler(self, outil: str, **arguments: Any) -> Any:
        """⚠️ La permission se verifie ICI, pas dans le prompt.

        Un modele peut demander n'importe quel nom d'outil — c'est du
        texte. Ce qui l'arrete est cette methode, et le RBAC du compte de
        service en dessous. Un prompt qui dit « n'utilise jamais
        delete » n'est pas un controle d'acces.
        """
        # >>> depart: refuser ce qui n'est pas accorde, ou que le serveur n'expose pas
        #     return self.disponibles[outil].executer(**arguments)
        if outil not in self.accordes:
            raise ErreurOutil(
                f"« {outil} » n'est pas accorde a cet agent "
                f"(accordes : {self.accordes})")
        if outil not in self.disponibles:
            raise ErreurOutil(
                f"« {outil} » est accorde mais le serveur ne l'expose pas")
        return self.disponibles[outil].executer(**arguments)
        # <<<
