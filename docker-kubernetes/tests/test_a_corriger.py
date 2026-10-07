"""Les pieces a conviction restent fautives.

⚠️ Ces tests echouent le jour ou quelqu'un « repare » l'un des fichiers
suivants. C'est voulu : un verificateur qui n'a jamais vu de fichier
incorrect ne prouve rien, et les chapitres mesurent SUR ces fichiers.

    contexte/Dockerfile.naif                  six defauts
    pile/compose.naif.yaml                    quatre defauts
    manifestes/deployment-sans-sondes.yaml    trois absences
    manifestes/service-mauvais-selecteur.yaml une lettre
"""

from __future__ import annotations

from pathlib import Path

from jobportal import compose, construction, contexte, dockerfile
from jobportal import kubernetes as k8s

RACINE = Path(__file__).resolve().parent.parent
CONTEXTE = RACINE / "contexte"
PILE = RACINE / "pile"
MANIFESTES = RACINE / "manifestes"


# ── contexte/Dockerfile.naif ─────────────────────────────────────────────

def test_le_dockerfile_naif_a_toujours_ses_six_defauts():
    fichier = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile.naif")
    sans = contexte.charger(CONTEXTE, appliquer_dockerignore=False)
    resultat = construction.construire(fichier, sans, construction.Cache())

    assert not fichier.multi_etages                       # 1. un seul etage
    premier = [i for i in fichier.finale.instructions
               if i.mot == "COPY"][0]
    assert premier.arguments.strip() == ". ."             # 2. COPY . . en tete
    assert resultat.image.fouiller("/app/.env")           # 3. le secret reste
    assert resultat.image.poids_mort > 0                  # 4. le rm inutile
    assert fichier.finale.utilisateur == "root"           # 5. root
    assert not dockerfile.forme_exec(                     # 6. forme shell
        fichier.finale.cherchees("CMD")[0])


def test_le_bon_dockerfile_na_aucun_de_ces_defauts():
    fichier = dockerfile.analyser_fichier(CONTEXTE / "Dockerfile")
    resultat = construction.construire(
        fichier, contexte.charger(CONTEXTE), construction.Cache())

    assert fichier.multi_etages
    assert resultat.image.fouiller("/app/.env") == []
    assert resultat.image.poids_mort == 0
    assert fichier.finale.utilisateur == "appuser"
    assert dockerfile.forme_exec(fichier.finale.cherchees("ENTRYPOINT")[0])


# ── pile/compose.naif.yaml ───────────────────────────────────────────────

def test_le_compose_naif_a_toujours_ses_quatre_defauts():
    projet, _ = compose.charger(PILE / "compose.naif.yaml")
    app, base = projet.services["app"], projet.services["db"]

    assert app.depend_de[0].condition == "service_started"   # 1. forme courte
    assert not base.sante.declaree                           # 2. pas de sonde
    assert app.environnement["DB_PASSWORD"] == "motdepasse"  # 3. en clair
    assert base.ports_publies == [(5432, 5432)]              # 4. port publie


def test_le_bon_compose_na_aucun_de_ces_defauts():
    projet, _ = compose.charger(PILE / "compose.yaml")
    app, base = projet.services["app"], projet.services["db"]

    assert app.depend_de[0].attend_la_sante
    assert base.sante.declaree
    assert base.ports_publies == []
    assert compose.echecs(compose.demarrer(projet)) == []


# ── les manifestes ───────────────────────────────────────────────────────

def test_le_deploiement_sans_sondes_est_toujours_sans_sondes():
    cluster = k8s.Cluster([k8s.noeud("n", 4, 8)])
    cluster.appliquer((MANIFESTES / "deployment-sans-sondes.yaml")
                      .read_text(encoding="utf-8"))
    cluster.stabiliser()
    conteneur = cluster.par_deploiement(
        "jobportal-sans-sondes")[0].conteneurs[0]
    strategie = cluster.deploiements["jobportal-sans-sondes"].strategie

    assert not conteneur.readiness and not conteneur.liveness   # 1. aucune sonde
    assert conteneur.cpu_demande == 0                          # 2. aucune resources
    assert strategie.max_surge == "25%"                        # 3. valeurs par defaut
    assert strategie.max_indisponible == "25%"


def test_le_service_casse_a_toujours_sa_faute_de_frappe():
    cluster = k8s.Cluster([k8s.noeud("n", 4, 8)])
    cluster.appliquer((MANIFESTES / "deployment.yaml")
                      .read_text(encoding="utf-8"))
    cluster.appliquer((MANIFESTES / "service-mauvais-selecteur.yaml")
                      .read_text(encoding="utf-8"))
    cluster.stabiliser()

    assert cluster.services["jobportal-casse"].selecteur == {"app": "jobporta"}
    assert cluster.endpoints("jobportal-casse") == []
    assert len(cluster.endpoints("jobportal")) == 3


def test_le_deploiement_gourmand_demande_toujours_trop():
    cluster = k8s.Cluster([k8s.noeud("noeud-1", 2, 4), k8s.noeud("noeud-2", 2, 4)])
    cluster.appliquer((MANIFESTES / "deployment-gourmand.yaml")
                      .read_text(encoding="utf-8"))
    cluster.stabiliser()

    en_attente = [pod for pod in cluster.par_deploiement("jobportal-gourmand")
                  if pod.phase == "Pending"]
    assert len(en_attente) == 2
