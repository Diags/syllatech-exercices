"""La boucle de reconciliation : placement, sondes, mise a jour, blocage."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import kubernetes as k8s

RACINE = Path(__file__).resolve().parent.parent
MANIFESTES = RACINE / "manifestes"
DEPLOIEMENT = (MANIFESTES / "deployment.yaml").read_text(encoding="utf-8")


@pytest.fixture
def cluster() -> k8s.Cluster:
    return k8s.Cluster([k8s.noeud("noeud-1", 2, 4), k8s.noeud("noeud-2", 2, 4)])


@pytest.fixture
def deploye(cluster: k8s.Cluster) -> k8s.Cluster:
    cluster.appliquer(DEPLOIEMENT)
    cluster.stabiliser()
    return cluster


# ── les unites ───────────────────────────────────────────────────────────

def test_les_millicores():
    assert k8s.millicores("250m") == 250
    assert k8s.millicores("1") == 1000
    assert k8s.millicores(None) == 0
    with pytest.raises(k8s.ErreurKubernetes):
        k8s.millicores("beaucoup")


def test_512M_et_512Mi_ne_font_pas_la_meme_taille():
    """⚠️ 5 % d'ecart, et c'est la source de surprises sur les limites."""
    assert k8s.octets("512Mi") == 512 * 1024 ** 2
    assert k8s.octets("512M") == 512 * 1000 ** 2
    assert k8s.octets("512Mi") > k8s.octets("512M")


def test_la_capacite_nest_pas_lallouable():
    machine = k8s.noeud("n", 2, 4)

    assert machine.cpu == 1900
    assert machine.memoire < 4 * 1024 ** 3


# ── la boucle ────────────────────────────────────────────────────────────

def test_apply_necree_aucun_pod(cluster: k8s.Cluster):
    """`kubectl apply` ecrit un etat voulu. Il n'execute rien."""
    cluster.appliquer(DEPLOIEMENT)

    assert cluster.pods == {}
    assert cluster.deploiements["jobportal"].voulus == 3


def test_les_controleurs_amenent_trois_pods_prets(deploye: k8s.Cluster):
    pods = deploye.par_deploiement("jobportal")

    assert len(pods) == 3
    assert deploye.disponibles("jobportal") == 3
    assert all(pod.noeud is not None for pod in pods)
    assert len(deploye.replicasets) == 1


def test_les_pods_sont_repartis_sur_les_noeuds(deploye: k8s.Cluster):
    noeuds = {pod.noeud for pod in deploye.par_deploiement("jobportal")}

    assert len(noeuds) == 2


def test_appliquer_deux_fois_ne_recree_rien(deploye: k8s.Cluster):
    avant = {pod.nom for pod in deploye.par_deploiement("jobportal")}
    deploye.appliquer(DEPLOIEMENT)
    deploye.stabiliser()

    assert {pod.nom for pod in deploye.par_deploiement("jobportal")} == avant
    assert len(deploye.replicasets) == 1


def test_un_pod_supprime_est_recree(deploye: k8s.Cluster):
    victime = deploye.par_deploiement("jobportal")[0]
    deploye.supprimer_pod(victime.nom)
    deploye.stabiliser()

    noms = {pod.nom for pod in deploye.par_deploiement("jobportal")}
    assert len(noms) == 3
    assert victime.nom not in noms          # un AUTRE pod, pas le meme
    assert deploye.disponibles("jobportal") == 3


# ── le Service ───────────────────────────────────────────────────────────

def test_un_selecteur_fautif_ne_donne_aucun_endpoint(deploye: k8s.Cluster):
    """⚠️ Une lettre, aucune erreur, et le service ne repond jamais."""
    deploye.appliquer((MANIFESTES / "service-mauvais-selecteur.yaml")
                      .read_text(encoding="utf-8"))

    assert len(deploye.endpoints("jobportal")) == 3
    assert deploye.endpoints("jobportal-casse") == []


def test_un_pod_pas_pret_sort_des_endpoints(cluster: k8s.Cluster):
    cluster.appliquer(DEPLOIEMENT)
    cluster.reconcilier(2)

    assert cluster.par_deploiement("jobportal")
    assert cluster.endpoints("jobportal") == []      # pas encore prets

    cluster.stabiliser()
    assert len(cluster.endpoints("jobportal")) == 3


def test_sans_readiness_un_pod_est_pret_des_quil_tourne(cluster: k8s.Cluster):
    """⚠️ D'ou les 502 du debut de chaque deploiement."""
    cluster.appliquer((MANIFESTES / "deployment-sans-sondes.yaml")
                      .read_text(encoding="utf-8"))
    cluster.reconcilier(2)

    assert cluster.disponibles("jobportal-sans-sondes") == 3


# ── l'ordonnancement ─────────────────────────────────────────────────────

def test_un_pod_trop_gourmand_reste_pending(cluster: k8s.Cluster):
    cluster.appliquer((MANIFESTES / "deployment-gourmand.yaml")
                      .read_text(encoding="utf-8"))
    cluster.stabiliser()

    pods = cluster.par_deploiement("jobportal-gourmand")
    en_attente = [pod for pod in pods if pod.phase == "Pending"]
    assert len(pods) == 4
    assert len(en_attente) == 2
    assert all(pod.raison == "Insufficient memory" for pod in en_attente)


def test_les_requests_reservent_meme_sans_consommation(deploye: k8s.Cluster):
    cpu, memoire = deploye.reste("noeud-1")
    machine = deploye.noeuds["noeud-1"]

    assert cpu < machine.cpu
    assert memoire < machine.memoire


def test_depasser_sa_limite_donne_un_OOMKilled(cluster: k8s.Cluster):
    cluster.appliquer(DEPLOIEMENT.replace("jobportal:1.0",
                                          "jobportal:1.3-gourmande"))
    cluster.stabiliser(30)
    pods = cluster.par_deploiement("jobportal")

    assert all(pod.raison == "OOMKilled" for pod in pods)
    assert all(pod.redemarrages >= 1 for pod in pods)
    assert cluster.disponibles("jobportal") == 0


def test_les_classes_de_qualite(cluster: k8s.Cluster):
    cluster.appliquer(DEPLOIEMENT)
    cluster.appliquer((MANIFESTES / "deployment-sans-sondes.yaml")
                      .read_text(encoding="utf-8"))
    cluster.stabiliser()

    assert cluster.par_deploiement("jobportal")[0].qos == "Burstable"
    assert cluster.par_deploiement(
        "jobportal-sans-sondes")[0].qos == "BestEffort"


def test_requests_egales_aux_limits_donnent_Guaranteed(cluster: k8s.Cluster):
    cluster.appliquer(DEPLOIEMENT.replace("cpu: 500m, memory: 512Mi",
                                          "cpu: 250m, memory: 512Mi"))
    cluster.stabiliser()

    assert cluster.par_deploiement("jobportal")[0].qos == "Guaranteed"


# ── la mise a jour progressive ───────────────────────────────────────────

def _basculer(cluster: k8s.Cluster, manifeste: str, image: str,
              ticks: int = 60) -> int:
    """Rend le minimum de pods prets observe pendant la bascule."""
    cluster.appliquer(manifeste.replace("jobportal:1.0", image))
    minimum = 99
    for _ in range(ticks):
        cluster.reconcilier()
        minimum = min(minimum, cluster.disponibles("jobportal"))
        pods = cluster.par_deploiement("jobportal")
        if len(pods) == 3 and cluster.disponibles("jobportal") == 3 \
                and all(p.conteneurs[0].image.endswith(image.split(":")[1])
                        for p in pods):
            break
    return minimum


def test_maxUnavailable_zero_ne_descend_jamais_sous_le_plancher(
        deploye: k8s.Cluster):
    """⚠️ LA MESURE DU CHAPITRE 5 : minimum 3."""
    assert _basculer(deploye, DEPLOIEMENT, "jobportal:1.1") == 3
    assert len(deploye.replicasets) == 2


def test_maxSurge_zero_coupe_le_service(cluster: k8s.Cluster):
    brutale = DEPLOIEMENT.replace(
        "rollingUpdate: { maxSurge: 1, maxUnavailable: 0 }",
        "rollingUpdate: { maxSurge: 0, maxUnavailable: 3 }")
    cluster.appliquer(brutale)
    cluster.stabiliser()

    assert _basculer(cluster, brutale, "jobportal:1.1") == 0


def test_une_image_cassee_bloque_sans_rien_couper(deploye: k8s.Cluster):
    """⚠️ La mesure la plus utile du projet."""
    origine = {pod.nom for pod in deploye.par_deploiement("jobportal")}
    deploye.appliquer(DEPLOIEMENT.replace("jobportal:1.0",
                                          "jobportal:1.2-cassee"))
    minimum = 99
    for _ in range(60):
        deploye.reconcilier()
        minimum = min(minimum, deploye.disponibles("jobportal"))
        if deploye.deploiements["jobportal"].condition:
            break

    assert deploye.deploiements["jobportal"].condition == \
        "ProgressDeadlineExceeded"
    assert minimum == 3
    assert origine <= {pod.nom for pod in deploye.par_deploiement("jobportal")}


def test_rollout_undo_revient_a_la_revision_precedente(deploye: k8s.Cluster):
    deploye.appliquer(DEPLOIEMENT.replace("jobportal:1.0",
                                          "jobportal:1.2-cassee"))
    deploye.reconcilier(40)

    deploye.annuler("jobportal")
    deploye.stabiliser()

    images = {pod.conteneurs[0].image
              for pod in deploye.par_deploiement("jobportal")}
    assert images == {"registry.exemple.fr/jobportal:1.0"}
    assert deploye.disponibles("jobportal") == 3


def test_un_gabarit_identique_ne_cree_pas_de_replicaset(deploye: k8s.Cluster):
    """⚠️ Ce qui explique le `latest` du chapitre 6."""
    empreinte = deploye.deploiements["jobportal"].gabarit.empreinte
    deploye.appliquer(DEPLOIEMENT)
    deploye.stabiliser()

    assert deploye.deploiements["jobportal"].gabarit.empreinte == empreinte
    assert len(deploye.replicasets) == 1


def test_un_genre_non_gere_leve(cluster: k8s.Cluster):
    with pytest.raises(k8s.ErreurKubernetes, match="genre non gere"):
        cluster.appliquer("apiVersion: v1\nkind: Machin\nmetadata:\n  name: x\n")
