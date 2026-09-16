"""Un cluster Kubernetes en boucle de reconciliation, tick par tick.

CE QU'EST VRAIMENT KUBERNETES
-----------------------------
Pas un systeme qui « lance des conteneurs ». Un ensemble de **controleurs**
qui comparent, en boucle, un etat VOULU a un etat REEL, et font un pas vers
le premier. `kubectl apply` n'execute rien : il ecrit l'etat voulu dans
l'API. Tout le reste est de la reconciliation.

Ce module ecrit cette boucle. Quatre controleurs, dans cet ordre, a chaque
tick d'une seconde :

    1. le controleur de Deployment  cree et redimensionne les ReplicaSets
    2. le controleur de ReplicaSet  cree et supprime les Pods
    3. l'ordonnanceur (scheduler)   place les Pods en attente sur un noeud
    4. le kubelet                   demarre les Pods et sonde leur sante

Chaque chapitre imprime les ticks. On y voit les choses que les schemas ne
montrent pas : un pod supprime qui revient, une mise a jour qui se bloque
sans jamais couper le service, un pod `Pending` pour toujours parce qu'il
demande plus de memoire qu'un noeud n'en a.

⚠️ CE QUI EST MODELISE, ET CE QUI NE L'EST PAS
Les ressources sont comptees en millicores et en octets ; `requests` sert a
**placer**, `limits` sert a **tuer**. Il n'y a ni reseau, ni volumes
persistants, ni `kube-proxy` : les *endpoints* d'un Service sont simplement
les pods PRETS dont les etiquettes correspondent. C'est assez pour mesurer
tout ce que le cours enseigne, et c'est dit ici pour qu'on ne cite pas ce
projet au-dela.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

from . import yaml_minimal


class ErreurKubernetes(Exception):
    """Un manifeste incomplet, une reference introuvable."""


# ── ce que ce cluster sait des images ────────────────────────────────────
#
# ⚠️ ENTREE DECLAREE, comme `effets.py`. Aucun conteneur ne demarre : ce
# tableau dit, pour chaque image, si elle demarre, en combien de ticks elle
# devient PRETE, et combien de memoire elle consomme reellement. C'est ce
# qui permet de fabriquer une panne — une image qui ne passe jamais la
# sonde de readiness — et d'en mesurer les consequences.

@dataclass(frozen=True)
class ImageConnue:
    pret_en: int = 2                 # ticks avant que la readiness passe
    demarre: bool = True             # sinon : CrashLoopBackOff
    memoire_utilisee: int = 300 * 1024 * 1024
    commentaire: str = ""


REGISTRE: dict[str, ImageConnue] = {
    "registry.exemple.fr/jobportal:1.0": ImageConnue(
        pret_en=6, commentaire="l'application qui tourne aujourd'hui"),
    "registry.exemple.fr/jobportal:1.1": ImageConnue(
        pret_en=6, commentaire="la version suivante, saine"),
    "registry.exemple.fr/jobportal:1.2-cassee": ImageConnue(
        pret_en=10 ** 6, commentaire=(
            "⚠️ elle DEMARRE mais ne passe jamais la readiness — "
            "le cas qui bloque un deploiement sans rien couper")),
    "registry.exemple.fr/jobportal:1.3-gourmande": ImageConnue(
        pret_en=6, memoire_utilisee=900 * 1024 * 1024,
        commentaire="⚠️ elle depasse sa limite : OOMKilled"),
    "postgres:16": ImageConnue(pret_en=9, memoire_utilisee=200 * 1024 * 1024),
}

DEFAUT = ImageConnue(commentaire="image hors du registre du projet")


def connue(image: str) -> ImageConnue:
    return REGISTRE.get(image, DEFAUT)


# ── les unites de Kubernetes ─────────────────────────────────────────────

_CPU = re.compile(r"^(\d+(?:\.\d+)?)(m)?$")
_MEMOIRE = re.compile(r"^(\d+(?:\.\d+)?)(Ki|Mi|Gi|Ti|K|M|G|T)?$")
_FACTEURS = {"Ki": 1024, "Mi": 1024 ** 2, "Gi": 1024 ** 3, "Ti": 1024 ** 4,
             "K": 1000, "M": 1000 ** 2, "G": 1000 ** 3, "T": 1000 ** 4}


def millicores(valeur: Any) -> int:
    """« 250m » et « 1 » — le second vaut mille fois le premier."""
    if valeur is None:
        return 0
    trouve = _CPU.match(str(valeur).strip())
    if trouve is None:
        raise ErreurKubernetes(f"quantite de CPU illisible : « {valeur} »")
    nombre = float(trouve.group(1))
    return int(nombre) if trouve.group(2) else int(nombre * 1000)


def octets(valeur: Any) -> int:
    """⚠️ « 512M » et « 512Mi » ne font pas la meme taille : 5 % d'ecart."""
    if valeur is None:
        return 0
    trouve = _MEMOIRE.match(str(valeur).strip())
    if trouve is None:
        raise ErreurKubernetes(f"quantite de memoire illisible : « {valeur} »")
    return int(float(trouve.group(1)) * _FACTEURS.get(trouve.group(2) or "", 1))


def lisible(nombre: float) -> str:
    """Les unites binaires de Kubernetes, avec une decimale.

    ⚠️ La decimale n'est pas de la coquetterie : sans elle, 1 648 Mio
    s'affichent « 2Gi », et l'on ne comprend plus pourquoi un pod qui
    demande 2 Gi reste `Pending` sur un noeud qui semble en avoir 2.
    """
    if nombre < 1024:
        return f"{nombre:.0f} o"
    for unite in ("Ki", "Mi", "Gi"):
        nombre /= 1024.0
        if nombre < 1024 or unite == "Gi":
            return f"{nombre:.1f}{unite}"
    return f"{nombre:.1f}Gi"


# ── les objets ───────────────────────────────────────────────────────────

@dataclass
class Conteneur:
    nom: str
    image: str
    cpu_demande: int = 0
    memoire_demandee: int = 0
    cpu_limite: int = 0
    memoire_limite: int = 0
    readiness: bool = False
    liveness: bool = False

    @property
    def qos(self) -> str:
        """Guaranteed / Burstable / BestEffort — l'ordre d'eviction.

        ⚠️ C'est la classe la PLUS BASSE de ses conteneurs qui classe le
        pod, et c'est elle que le kubelet regarde quand un noeud manque de
        memoire. Un pod sans `requests` est evince le premier, sans
        preavis et sans que personne l'ait decide.
        """
        if not self.cpu_demande and not self.memoire_demandee \
                and not self.cpu_limite and not self.memoire_limite:
            return "BestEffort"
        if (self.cpu_demande == self.cpu_limite
                and self.memoire_demandee == self.memoire_limite
                and self.cpu_limite and self.memoire_limite):
            return "Guaranteed"
        return "Burstable"


@dataclass
class Gabarit:
    """Le `spec.template` d'un Deployment : les etiquettes et les conteneurs."""

    etiquettes: dict[str, str] = field(default_factory=dict)
    conteneurs: list[Conteneur] = field(default_factory=list)

    @property
    def empreinte(self) -> str:
        """Le `pod-template-hash` : ce qui distingue deux ReplicaSets.

        ⚠️ Deux gabarits identiques donnent la meme empreinte, donc le
        MEME ReplicaSet. C'est la raison pour laquelle un `helm upgrade`
        avec le tag `latest` ne redemarre aucun pod — le chapitre 6 le
        mesure.
        """
        morceaux = [f"{c}={v}" for c, v in sorted(self.etiquettes.items())]
        for conteneur in self.conteneurs:
            morceaux.append(f"{conteneur.nom}:{conteneur.image}:"
                            f"{conteneur.cpu_demande}:{conteneur.memoire_demandee}:"
                            f"{conteneur.cpu_limite}:{conteneur.memoire_limite}")
        empreinte = 0
        for morceau in morceaux:
            for caractere in morceau:
                empreinte = (empreinte * 33 + ord(caractere)) % 100_000
        return f"{empreinte:05d}"


@dataclass
class Pod:
    nom: str
    etiquettes: dict[str, str]
    conteneurs: list[Conteneur]
    phase: str = "Pending"            # Pending | Running | Failed
    raison: str = ""
    pret: bool = False
    noeud: str | None = None
    age: int = 0
    proprietaire: str = ""
    redemarrages: int = 0

    @property
    def cpu_demande(self) -> int:
        return sum(c.cpu_demande for c in self.conteneurs)

    @property
    def memoire_demandee(self) -> int:
        return sum(c.memoire_demandee for c in self.conteneurs)

    @property
    def qos(self) -> str:
        classes = {c.qos for c in self.conteneurs}
        for classe in ("BestEffort", "Burstable", "Guaranteed"):
            if classe in classes:
                return classe
        return "BestEffort"

    @property
    def etat(self) -> str:
        if self.phase == "Running" and self.pret:
            return "Running"
        if self.phase == "Running":
            return f"Running (pas pret{', ' + self.raison if self.raison else ''})"
        if self.raison:
            return f"{self.phase} ({self.raison})"
        return self.phase


@dataclass
class ReplicaSet:
    nom: str
    empreinte: str
    selecteur: dict[str, str]
    gabarit: Gabarit
    voulus: int = 0
    revision: int = 1
    deploiement: str = ""


@dataclass
class Strategie:
    type: str = "RollingUpdate"
    max_surge: Any = "25%"
    max_indisponible: Any = "25%"

    def surge(self, voulus: int) -> int:
        return _proportion(self.max_surge, voulus, math.ceil)

    def indisponible(self, voulus: int) -> int:
        return _proportion(self.max_indisponible, voulus, math.floor)


def _proportion(valeur: Any, base: int, arrondi) -> int:
    texte = str(valeur).strip()
    if texte.endswith("%"):
        return int(arrondi(base * float(texte[:-1]) / 100.0))
    return int(texte)


@dataclass
class Deploiement:
    nom: str
    voulus: int
    selecteur: dict[str, str]
    gabarit: Gabarit
    strategie: Strategie = field(default_factory=Strategie)
    delai_de_progression: int = 60
    revision: int = 0
    condition: str = ""
    depuis_le_dernier_progres: int = 0


@dataclass
class ServiceK8s:
    nom: str
    selecteur: dict[str, str]
    port: int = 80
    port_cible: int = 8080
    type: str = "ClusterIP"


@dataclass
class Noeud:
    nom: str
    cpu: int                    # millicores allouables
    memoire: int                # octets allouables
    etiquettes: dict[str, str] = field(default_factory=dict)


# ⚠️ LA CAPACITE D'UN NOEUD N'EST PAS SON ALLOUABLE.
#
# Sur une machine de 4 Gio, Kubernetes n'en propose jamais 4 a vos pods :
# le kubelet, le moteur de conteneurs et les pods systeme en reservent une
# part (`--kube-reserved`, `--system-reserved`, plus un seuil d'eviction).
# Les valeurs ci-dessous sont celles d'un noeud gere courant. C'est ce qui
# fait qu'un pod demandant « la moitie du noeud » n'entre pas deux fois.
RESERVE_CPU = 100                        # millicores
RESERVE_MEMOIRE = 400 * 1024 ** 2        # octets


def noeud(nom: str, coeurs: float, gio: float,
          **etiquettes: str) -> "Noeud":
    """Un noeud decrit par sa CAPACITE ; ce qui est stocke est l'allouable."""
    return Noeud(nom,
                 int(coeurs * 1000) - RESERVE_CPU,
                 int(gio * 1024 ** 3) - RESERVE_MEMOIRE,
                 dict(etiquettes))


@dataclass
class Evenement:
    tick: int
    quoi: str

    def __str__(self) -> str:
        return f"t={self.tick:>3}s  {self.quoi}"


# ── le cluster ───────────────────────────────────────────────────────────

class Cluster:
    """L'API, les controleurs, et le temps qui passe."""

    def __init__(self, noeuds: Iterable[Noeud] | None = None) -> None:
        self.noeuds: dict[str, Noeud] = {n.nom: n for n in (noeuds or [])}
        self.deploiements: dict[str, Deploiement] = {}
        self.replicasets: dict[str, ReplicaSet] = {}
        self.pods: dict[str, Pod] = {}
        self.services: dict[str, ServiceK8s] = {}
        self.configmaps: dict[str, dict[str, str]] = {}
        self.secrets: dict[str, dict[str, str]] = {}
        self.evenements: list[Evenement] = []
        self.tick = 0
        self._compteur = 0

    # -- l'API --------------------------------------------------------

    def appliquer(self, manifeste: str) -> list[str]:
        """`kubectl apply -f` : ecrit l'etat voulu, et rien de plus."""
        appliques: list[str] = []
        for document in yaml_minimal.charger_tous(manifeste):
            if not document:
                continue
            appliques.append(self._appliquer_un(document))
        return appliques

    def _appliquer_un(self, document: dict[str, Any]) -> str:
        genre = document.get("kind")
        nom = (document.get("metadata") or {}).get("name")
        if not genre or not nom:
            raise ErreurKubernetes(
                "manifeste sans « kind » ou sans « metadata.name »")
        specification = document.get("spec") or {}

        if genre == "Deployment":
            gabarit = _gabarit(specification.get("template") or {})
            strategie = _strategie(specification.get("strategy") or {})
            existant = self.deploiements.get(nom)
            deploiement = Deploiement(
                nom, int(specification.get("replicas", 1)),
                ((specification.get("selector") or {}).get("matchLabels") or {}),
                gabarit, strategie,
                int(specification.get("progressDeadlineSeconds", 60)),
                existant.revision if existant else 0)
            self.deploiements[nom] = deploiement
            self._journal(f"deployment/{nom} configure "
                          f"(replicas={deploiement.voulus})")
        elif genre == "Service":
            self.services[nom] = ServiceK8s(
                nom, specification.get("selector") or {},
                _premier_port(specification, "port", 80),
                _premier_port(specification, "targetPort", 8080),
                specification.get("type", "ClusterIP"))
            self._journal(f"service/{nom} configure")
        elif genre == "ConfigMap":
            self.configmaps[nom] = dict(document.get("data") or {})
            self._journal(f"configmap/{nom} configure")
        elif genre == "Secret":
            self.secrets[nom] = dict(document.get("data")
                                     or document.get("stringData") or {})
            self._journal(f"secret/{nom} configure")
        else:
            raise ErreurKubernetes(f"genre non gere : « {genre} »")
        return f"{genre.lower()}/{nom}"

    def supprimer_pod(self, nom: str) -> bool:
        """`kubectl delete pod` — et le controleur le recree."""
        if nom not in self.pods:
            return False
        del self.pods[nom]
        self._journal(f"pod/{nom} supprime a la main")
        return True

    def annuler(self, nom: str) -> int:
        """`kubectl rollout undo` : revenir au ReplicaSet precedent."""
        deploiement = self.deploiements[nom]
        anciens = sorted(
            (rs for rs in self.replicasets.values()
             if rs.deploiement == nom and rs.empreinte != deploiement.gabarit.empreinte),
            key=lambda rs: rs.revision)
        if not anciens:
            raise ErreurKubernetes(f"deployment/{nom} : aucune revision anterieure")
        cible = anciens[-1]
        deploiement.gabarit = cible.gabarit
        deploiement.condition = ""
        deploiement.depuis_le_dernier_progres = 0
        self._journal(f"deployment/{nom} annule vers la revision "
                      f"{cible.revision}")
        return cible.revision

    # -- la boucle ----------------------------------------------------

    def reconcilier(self, ticks: int = 1) -> None:
        for _ in range(ticks):
            self.tick += 1
            self._controleur_de_deploiement()
            self._controleur_de_replicaset()
            self._ordonnanceur()
            self._kubelet()

    def stabiliser(self, maximum: int = 200) -> int:
        """Tourne jusqu'a ce que plus rien ne bouge — ou jusqu'au plafond.

        « Plus rien ne bouge » veut dire deux choses a la fois : aucun
        evenement de plus, ET aucun pod encore dans son delai de readiness.
        Sans la seconde, la boucle s'arreterait pendant le demarrage et
        conclurait qu'un pod n'est jamais pret.
        """
        depart = self.tick
        for _ in range(maximum):
            avant = len(self.evenements)
            self.reconcilier()
            en_demarrage = any(
                not pod.pret and pod.raison == "readiness"
                and pod.age < connue(pod.conteneurs[0].image).pret_en
                for pod in self.pods.values())
            if len(self.evenements) == avant and not en_demarrage:
                return self.tick - depart
        return self.tick - depart

    # -- 1. le controleur de Deployment -------------------------------

    def _controleur_de_deploiement(self) -> None:
        for deploiement in self.deploiements.values():
            attendu = deploiement.gabarit.empreinte
            courant = self._replicaset_de(deploiement.nom, attendu)
            if courant is None:
                deploiement.revision += 1
                courant = ReplicaSet(
                    f"{deploiement.nom}-{attendu}", attendu,
                    dict(deploiement.selecteur), deploiement.gabarit, 0,
                    deploiement.revision, deploiement.nom)
                self.replicasets[courant.nom] = courant
                deploiement.depuis_le_dernier_progres = 0
                self._journal(f"replicaset/{courant.nom} cree "
                              f"(revision {courant.revision})")

            anciens = [rs for rs in self.replicasets.values()
                       if rs.deploiement == deploiement.nom
                       and rs.empreinte != attendu and rs.voulus > 0]

            if not anciens:
                if courant.voulus != deploiement.voulus:
                    courant.voulus = deploiement.voulus
                continue

            self._avancer_la_mise_a_jour(deploiement, courant, anciens)

    def _avancer_la_mise_a_jour(self, deploiement: Deploiement,
                                courant: ReplicaSet,
                                anciens: list[ReplicaSet]) -> None:
        """L'arithmetique exacte d'un rolling update.

        ⚠️ Les deux bornes ne portent pas sur la meme chose :
        `maxSurge` plafonne le nombre TOTAL de pods, `maxUnavailable`
        plancherise le nombre de pods PRETS. Entre les deux, le controleur
        ne fait qu'un pas par tick — et si les nouveaux pods ne deviennent
        jamais prets, il s'arrete la. Sans rien couper.
        """
        # TODO : ajouter tant que maxSurge le permet, retirer tant que maxUnavailable le permet
        pass

    def _replicaset_de(self, deploiement: str,
                       empreinte: str) -> ReplicaSet | None:
        for replicaset in self.replicasets.values():
            if replicaset.deploiement == deploiement \
                    and replicaset.empreinte == empreinte:
                return replicaset
        return None

    # -- 2. le controleur de ReplicaSet -------------------------------

    def _controleur_de_replicaset(self) -> None:
        for replicaset in sorted(self.replicasets.values(),
                                 key=lambda rs: rs.nom):
            miens = [pod for pod in self.pods.values()
                     if pod.proprietaire == replicaset.nom]
            manquants = replicaset.voulus - len(miens)
            for _ in range(max(0, manquants)):
                self._creer_pod(replicaset)
            for pod in sorted(miens, key=lambda p: (p.pret, p.age))[
                    :max(0, -manquants)]:
                del self.pods[pod.nom]
                self._journal(f"pod/{pod.nom} supprime "
                              f"(replicaset/{replicaset.nom} reduit)")

    def _creer_pod(self, replicaset: ReplicaSet) -> Pod:
        self._compteur += 1
        nom = f"{replicaset.nom}-{self._compteur:03d}"
        etiquettes = dict(replicaset.gabarit.etiquettes)
        etiquettes["pod-template-hash"] = replicaset.empreinte
        pod = Pod(nom, etiquettes,
                  [Conteneur(**vars(c)) for c in replicaset.gabarit.conteneurs],
                  proprietaire=replicaset.nom)
        self.pods[nom] = pod
        self._journal(f"pod/{nom} cree")
        return pod

    # -- 3. l'ordonnanceur --------------------------------------------

    def _ordonnanceur(self) -> None:
        for pod in sorted(self.pods.values(), key=lambda p: p.nom):
            if pod.noeud is not None or pod.phase != "Pending":
                continue
            choisi = self._placer(pod)
            if choisi is None:
                if pod.raison != "Insufficient memory":
                    pod.raison = "Insufficient memory"
                    self._journal(
                        f"pod/{pod.nom} : aucun noeud ne peut l'accueillir "
                        f"({lisible(pod.memoire_demandee)} demandes)")
                continue
            pod.noeud = choisi
            pod.raison = ""
            self._journal(f"pod/{pod.nom} place sur {choisi}")

    def _placer(self, pod: Pod) -> str | None:
        """Le noeud le MOINS charge qui a la place.

        ⚠️ Ce sont les `requests` qui decident, jamais la consommation
        reelle. Un conteneur qui demande 2 Gi et n'en utilise que 300 Mo
        immobilise 2 Gi : l'ordonnanceur ne regarde pas ce qui se passe
        dans le pod, il regarde ce que le manifeste a reserve.

        Choisir le moins charge est la strategie par defaut de Kubernetes
        (`LeastAllocated`) ; c'est ce qui repartit les repliques au lieu de
        les empiler sur le premier noeud venu.
        """
        # TODO : choisir le noeud le moins charge qui a la place demandee
        return sorted(self.noeuds)[0] if self.noeuds else None

    def reste(self, noeud: str) -> tuple[int, int]:
        machine = self.noeuds[noeud]
        cpu = machine.cpu - sum(p.cpu_demande for p in self.pods.values()
                                if p.noeud == noeud)
        memoire = machine.memoire - sum(p.memoire_demandee
                                        for p in self.pods.values()
                                        if p.noeud == noeud)
        return cpu, memoire

    # -- 4. le kubelet -------------------------------------------------

    def _kubelet(self) -> None:
        for pod in sorted(self.pods.values(), key=lambda p: p.nom):
            if pod.noeud is None:
                continue
            pod.age += 1
            image = connue(pod.conteneurs[0].image)

            if not image.demarre:
                pod.phase = "Running"
                pod.pret = False
                pod.raison = "CrashLoopBackOff"
                pod.redemarrages = pod.age // 5
                continue

            depasse = any(
                c.memoire_limite and connue(c.image).memoire_utilisee > c.memoire_limite
                for c in pod.conteneurs)
            if depasse:
                pod.phase = "Running"
                pod.pret = False
                pod.raison = "OOMKilled"
                pod.redemarrages = max(1, pod.age // 4)
                continue

            pod.phase = "Running"
            if not pod.conteneurs[0].readiness:
                # ⚠️ SANS SONDE DE READINESS, un pod est declare PRET des
                # qu'il tourne. Le Service lui envoie donc du trafic avant
                # que l'application n'ait fini de demarrer — d'ou les 502
                # du debut de chaque deploiement.
                nouveau = True
            else:
                nouveau = pod.age >= image.pret_en
            if nouveau and not pod.pret:
                pod.pret = True
                pod.raison = ""
                self._journal(f"pod/{pod.nom} pret")
            elif not nouveau:
                pod.pret = False
                pod.raison = "readiness"

    # -- consultation --------------------------------------------------

    def endpoints(self, service: str) -> list[Pod]:
        """⚠️ Les pods PRETS dont les etiquettes correspondent. Un selecteur
        qui ne correspond a rien rend une liste vide — sans aucune erreur."""
        # TODO : rendre les pods PRETS dont les etiquettes correspondent
        return []

    def disponibles(self, deploiement: str) -> int:
        return sum(1 for pod in self.par_deploiement(deploiement) if pod.pret)

    def par_deploiement(self, deploiement: str) -> list[Pod]:
        # ⚠️ Par le ReplicaSet proprietaire, jamais par le prefixe du nom :
        # « jobportal » est un prefixe de « jobportal-gourmand ».
        miens = {rs.nom for rs in self.replicasets.values()
                 if rs.deploiement == deploiement}
        return sorted((pod for pod in self.pods.values()
                       if pod.proprietaire in miens), key=lambda p: p.nom)

    def _journal(self, quoi: str) -> None:
        self.evenements.append(Evenement(self.tick, quoi))

    def journal_depuis(self, tick: int) -> list[Evenement]:
        return [e for e in self.evenements if e.tick > tick]


def _correspond(etiquettes: dict[str, str], selecteur: dict[str, str]) -> bool:
    if not selecteur:
        return False
    return all(etiquettes.get(cle) == valeur
               for cle, valeur in selecteur.items())


# ── lecture des manifestes ───────────────────────────────────────────────

def _gabarit(brut: dict[str, Any]) -> Gabarit:
    etiquettes = ((brut.get("metadata") or {}).get("labels") or {})
    conteneurs = []
    for description in ((brut.get("spec") or {}).get("containers") or []):
        ressources = description.get("resources") or {}
        demandes = ressources.get("requests") or {}
        limites = ressources.get("limits") or {}
        conteneurs.append(Conteneur(
            description.get("name", "app"), description.get("image", ""),
            millicores(demandes.get("cpu")), octets(demandes.get("memory")),
            millicores(limites.get("cpu")), octets(limites.get("memory")),
            bool(description.get("readinessProbe")),
            bool(description.get("livenessProbe"))))
    if not conteneurs:
        raise ErreurKubernetes("un gabarit de pod sans conteneur")
    return Gabarit({str(c): str(v) for c, v in etiquettes.items()}, conteneurs)


def _strategie(brut: dict[str, Any]) -> Strategie:
    fin = brut.get("rollingUpdate") or {}
    return Strategie(brut.get("type", "RollingUpdate"),
                     fin.get("maxSurge", "25%"),
                     fin.get("maxUnavailable", "25%"))


def _premier_port(specification: dict[str, Any], cle: str, defaut: int) -> int:
    ports = specification.get("ports") or []
    if not ports:
        return defaut
    return int(ports[0].get(cle, defaut))


def rendre_pods(cluster: Cluster, pods: list[Pod] | None = None) -> list[str]:
    """Ce qu'afficherait `kubectl get pods -o wide`."""
    lignes = [f"{'NOM':<28} {'ETAT':<28} {'PRET':<5} {'RS':<3} NOEUD"]
    for pod in (pods if pods is not None
                else sorted(cluster.pods.values(), key=lambda p: p.nom)):
        lignes.append(f"{pod.nom:<28} {pod.etat:<28} "
                      f"{'1/1' if pod.pret else '0/1':<5} "
                      f"{pod.redemarrages:<3} {pod.noeud or '—'}")
    return lignes
