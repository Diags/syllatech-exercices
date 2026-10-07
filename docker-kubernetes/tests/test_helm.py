"""Helm : la fusion des valeurs, le rendu, et le tag qui ne deploie rien."""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import helm
from jobportal import kubernetes as k8s
from jobportal import yaml_minimal

RACINE = Path(__file__).resolve().parent.parent
CHART = RACINE / "chart"
PRODUCTION = CHART / "values-production.yaml"


@pytest.fixture
def chart() -> helm.Chart:
    return helm.charger(CHART)


def cluster_neuf() -> k8s.Cluster:
    return k8s.Cluster([k8s.noeud("noeud-1", 2, 4), k8s.noeud("noeud-2", 2, 4)])


# ── les valeurs ──────────────────────────────────────────────────────────

def test_la_fusion_est_profonde(chart: helm.Chart):
    valeurs = helm.valeurs_de(chart, [PRODUCTION])

    assert valeurs["replicas"] == 3                      # surcharge
    assert valeurs["ressources"]["cpu"] == "500m"        # surcharge
    assert valeurs["image"]["repository"] == \
        "registry.exemple.fr/jobportal"                  # survivant


def test_une_liste_est_remplacee_en_entier():
    """⚠️ Jamais fusionnee element par element."""
    fusion = helm.fusionner({"ports": [80, 443], "x": 1}, {"ports": [8080]})

    assert fusion["ports"] == [8080]
    assert fusion["x"] == 1


def test_set_passe_apres_tout_le_reste(chart: helm.Chart):
    valeurs = helm.valeurs_de(chart, [PRODUCTION],
                              ["replicas=7", "image.tag=abc"])

    assert valeurs["replicas"] == 7
    assert valeurs["image"]["tag"] == "abc"


def test_set_cree_les_niveaux_manquants():
    valeurs = helm.poser({}, "a.b.c", "x")

    assert valeurs == {"a": {"b": {"c": "x"}}}


# ── le moteur ────────────────────────────────────────────────────────────

def test_le_rendu_remplit_les_valeurs(chart: helm.Chart):
    rendu = helm.rendre(chart, helm.valeurs_de(chart, set_=["image.tag=1.0"]))
    manifeste = yaml_minimal.charger(rendu["deployment.yaml"])

    assert manifeste["spec"]["replicas"] == 1
    assert manifeste["spec"]["template"]["spec"]["containers"][0]["image"] == \
        "registry.exemple.fr/jobportal:1.0"


def test_le_bloc_if_disparait_quand_la_valeur_est_fausse(chart: helm.Chart):
    avec = helm.rendre(chart, helm.valeurs_de(
        chart, set_=["image.tag=1.0"]))["deployment.yaml"]
    sans = helm.rendre(chart, helm.valeurs_de(
        chart, set_=["image.tag=1.0", "sondes=false"]))["deployment.yaml"]

    assert "readinessProbe" in avec
    assert "readinessProbe" not in sans
    assert yaml_minimal.charger(sans) is not None       # reste du YAML valide


def test_required_fait_echouer_le_rendu(chart: helm.Chart):
    """⚠️ La seule facon de deplacer la panne vers la pull request."""
    with pytest.raises(helm.ErreurHelm, match="image.tag est obligatoire"):
        helm.rendre(chart, helm.valeurs_de(chart, [PRODUCTION]))


def test_sans_required_une_valeur_absente_rend_du_vide():
    moteur = helm.Moteur()
    rendu = moteur.rendre("image: {{ .Values.image.repository }}:"
                          "{{ .Values.image.tag }}",
                          {"Values": {"image": {"repository": "x"}}})

    assert rendu == "image: x:"


@pytest.mark.parametrize("gabarit, attendu", [
    ('{{ .Values.x | quote }}', '"oui"'),
    ('{{ .Values.x | upper }}', "OUI"),
    ('{{ .Values.absente | default "repli" }}', "repli"),
    ('{{ default "repli" .Values.absente }}', "repli"),
    ('{{ .Release.Name }}', "jobportal"),
    ('{{ .Chart.Name }}-{{ .Chart.Version }}', "chart-1.0"),
    ('{{ include "nom" . }}', "jobportal-chart"),
    ('{{- if .Values.vrai }}A{{- else }}B{{- end }}', "A"),
    ('{{- if .Values.faux }}A{{- else }}B{{- end }}', "B"),
    ('{{- range .Values.liste }}[{{ . }}]{{- end }}', "[a][b]"),
])
def test_les_constructions_du_moteur(gabarit: str, attendu: str):
    moteur = helm.Moteur({"nom": "{{ .Release.Name }}-{{ .Chart.Name }}"})
    contexte = {
        "Values": {"x": "oui", "vrai": True, "faux": False,
                   "liste": ["a", "b"]},
        "Release": {"Name": "jobportal"},
        "Chart": {"Name": "chart", "Version": "1.0"},
    }

    assert moteur.rendre(gabarit, contexte) == attendu


def test_une_fonction_inconnue_leve():
    with pytest.raises(helm.ErreurHelm, match="fonction inconnue"):
        helm.Moteur().rendre("{{ .Values.x | b64enc }}", {"Values": {"x": "a"}})


def test_un_end_manquant_leve():
    with pytest.raises(helm.ErreurHelm, match="end"):
        helm.Moteur().rendre("{{- if .Values.x }}A", {"Values": {"x": True}})


# ── les publications ─────────────────────────────────────────────────────

def test_le_tag_latest_ne_change_aucun_manifeste(chart: helm.Chart):
    """⚠️ LA MESURE DU CHAPITRE 6."""
    publication = helm.Publication("jobportal", chart)
    cluster = cluster_neuf()
    for _ in range(2):
        valeurs = helm.valeurs_de(chart, [PRODUCTION], ["image.tag=latest"])
        revision = publication.mettre_a_jour(valeurs)
        cluster.appliquer(publication.manifeste(revision.numero))
        cluster.stabiliser()

    assert publication.identiques(1, 2)
    assert len(cluster.replicasets) == 1
    assert cluster.deploiements["jobportal"].revision == 1
    assert len({pod.age for pod in cluster.par_deploiement("jobportal")}) == 1


def test_le_sha_du_commit_declenche_une_bascule(chart: helm.Chart):
    publication = helm.Publication("jobportal", chart)
    cluster = cluster_neuf()
    for tag in ("a1b2c3d", "9f8e7d6"):
        valeurs = helm.valeurs_de(chart, [PRODUCTION], [f"image.tag={tag}"])
        revision = publication.mettre_a_jour(valeurs)
        cluster.appliquer(publication.manifeste(revision.numero))
        cluster.stabiliser()

    assert not publication.identiques(1, 2)
    assert len(cluster.replicasets) == 2
    assert {pod.conteneurs[0].image
            for pod in cluster.par_deploiement("jobportal")} == \
        {"registry.exemple.fr/jobportal:9f8e7d6"}


def test_le_rollback_rejoue_les_manifestes_rendus(chart: helm.Chart):
    publication = helm.Publication("jobportal", chart)
    publication.installer(helm.valeurs_de(chart, [PRODUCTION],
                                          ["image.tag=a1b2c3d"]))
    publication.mettre_a_jour(helm.valeurs_de(
        chart, [PRODUCTION], ["image.tag=9f8e7d6", "replicas=5"]))
    publication.annuler(1)

    assert len(publication.revisions) == 3
    assert publication.identiques(1, 3)
    manifeste = publication.manifeste()
    assert "jobportal:a1b2c3d" in manifeste
    assert "replicas: 3" in manifeste


def test_le_manifeste_rendu_est_applicable_tel_quel(chart: helm.Chart):
    """Le lien entre les deux moities du projet : Helm rend, le cluster lit."""
    cluster = cluster_neuf()
    valeurs = helm.valeurs_de(chart, [PRODUCTION], ["image.tag=1.0"])
    publication = helm.Publication("jobportal", chart)
    publication.installer(valeurs)

    cluster.appliquer(publication.manifeste())
    cluster.stabiliser()

    assert cluster.disponibles("jobportal") == 3
    assert len(cluster.endpoints("jobportal")) == 3
