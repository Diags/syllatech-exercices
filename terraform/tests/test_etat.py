"""Le fichier d'etat : son format, ses secrets, son verrou, sa chirurgie."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from jobportal.etat import EtatVerrouille, Verrou
from jobportal.plan import DestructionEmpechee
from jobportal.terraform import Terraform

INFRA = Path(__file__).resolve().parent.parent / "infra"
PROTEGEE = Path(__file__).resolve().parent.parent / "infra-protegee"


@pytest.fixture
def tf(tmp_path: Path) -> Terraform:
    return Terraform(INFRA, etat=tmp_path / "terraform.tfstate",
                     realite=tmp_path / "realite.json")


def test_le_format_du_fichier(tf: Terraform):
    tf.apply()

    donnees = json.loads(tf.chemin_etat.read_text(encoding="utf-8"))

    assert donnees["version"] == 4
    assert donnees["serial"] >= 1
    assert donnees["lineage"]
    assert donnees["resources"][0]["type"] == "conteneur"
    assert donnees["resources"][0]["instances"][0]["index_key"] == "dev"


def test_le_serial_augmente_a_chaque_ecriture(tf: Terraform):
    tf.apply()
    premier = json.loads(tf.chemin_etat.read_text(encoding="utf-8"))["serial"]

    tf.apply({"version_image": "1.5.0"})
    second = json.loads(tf.chemin_etat.read_text(encoding="utf-8"))["serial"]

    assert second > premier


def test_les_secrets_sont_en_clair_dans_letat(tf: Terraform):
    """⚠️ La raison pour laquelle l'etat ne va jamais dans Git.

    Le mot de passe n'apparait nulle part dans le code : c'est le provider
    qui l'a engendre, et l'etat le stocke tel quel.
    """
    tf.apply()

    contenu = tf.chemin_etat.read_text(encoding="utf-8")

    assert "mot_de_passe" in contenu
    attributs = json.loads(contenu)["resources"][0]["instances"][0][
        "attributes"]
    assert len(attributs["mot_de_passe"]) == 16


def test_perdre_letat_fait_tout_recreer(tf: Terraform):
    """Les objets existent toujours ; Terraform ne sait plus qu'ils sont a lui."""
    tf.apply()
    reels = len(tf.realite().tout())

    tf.chemin_etat.unlink()
    plan = tf.plan()

    assert reels == 3
    assert plan.resume == "Plan: 3 to add, 0 to change, 0 to destroy."


def test_import_fait_adopter_sans_rien_creer(tf: Terraform):
    tf.apply()
    realite = tf.realite()
    realite.creer("conteneur", {"nom": "legacy", "image": "vieux:1"})
    avant = len(tf.state_list())

    adopte = tf.importer("conteneur.reprise", "conteneur-legacy")

    assert adopte is True
    assert len(tf.state_list()) == avant + 1
    assert len(tf.realite().tout()) == 4


def test_state_mv_renomme_lentree_pas_la_ressource(tf: Terraform):
    tf.apply()
    realite = tf.realite()
    realite.creer("conteneur", {"nom": "legacy", "image": "vieux:1"})
    tf.importer("conteneur.reprise", "conteneur-legacy")
    objets_avant = len(tf.realite().tout())

    tf.state_mv("conteneur.reprise", "conteneur.ancienne")

    assert "conteneur.ancienne" in tf.state_list()
    assert "conteneur.reprise" not in tf.state_list()
    assert len(tf.realite().tout()) == objets_avant


def test_state_rm_cesse_de_suivre_sans_detruire(tf: Terraform):
    tf.apply()
    objets_avant = len(tf.realite().tout())

    tf.state_rm("conteneur.app", "dev")

    assert 'conteneur.app["dev"]' not in tf.state_list()
    assert len(tf.realite().tout()) == objets_avant


def test_le_verrou_empeche_un_second_apply(tf: Terraform):
    verrou = Verrou(tf.chemin_etat)
    verrou.prendre("collegue")

    with pytest.raises(EtatVerrouille, match="collegue"):
        tf.apply()

    verrou.rendre()
    tf.apply()   # ne leve plus


def test_prevent_destroy_refuse_la_destruction(tmp_path: Path):
    tf = Terraform(PROTEGEE, etat=tmp_path / "s.tfstate",
                   realite=tmp_path / "r.json")
    tf.apply()
    contenu = (PROTEGEE / "main.tf").read_text(encoding="utf-8")
    (PROTEGEE / "main.tf").write_text(
        contenu.replace('nom   = "jobportal-base"',
                        'nom   = "jobportal-base-v2"'), encoding="utf-8")
    try:
        with pytest.raises(DestructionEmpechee, match="prevent_destroy"):
            tf.apply()
    finally:
        (PROTEGEE / "main.tf").write_text(contenu, encoding="utf-8")


def test_le_plan_enregistre_sapplique_tel_quel(tf: Terraform):
    """⚠️ Ce que `plan -out` garantit, et qu'un apply nu ne garantit pas."""
    enregistre = tf.plan()

    tf.apply(plan=enregistre)

    noms = sorted(objet["nom"] for objet in tf.realite().tout().values())
    assert noms == ["jobportal-dev", "jobportal-prod", "jobportal-staging"]


def test_la_derive_est_invisible_sans_rafraichissement(tf: Terraform):
    """⚠️ Le plan compare le CODE a l'ETAT, jamais a la realite."""
    tf.apply()
    tf.realite().modifier("conteneur-jobportal-prod",
                          {"nom": "jobportal-prod", "image": "vieux:0.1",
                           "memoire": 64})

    assert tf.plan().vide           # la derive ne se voit pas

    etat = tf.etat()                # un « refresh » a la main
    realite = tf.realite()
    for ressource in etat.ressources.values():
        for instance in ressource.instances:
            reel = realite.lire(instance.attributs.get("id", ""))
            if reel is not None:
                instance.attributs = dict(reel)
    etat.ecrire()

    assert not tf.plan().vide       # maintenant, elle se voit
