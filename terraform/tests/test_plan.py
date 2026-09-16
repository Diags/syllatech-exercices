"""Le plan : creation, modification, remplacement, destruction.

C'est l'algorithme central de Terraform, et ces tests le figent cas par
cas. Le plus important est {@code test_for_each_contre_count} : il mesure
l'ecart que le chapitre 2 imprime.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal.configuration import ErreurConfiguration
from jobportal.plan import Action
from jobportal.terraform import Terraform

INFRA = Path(__file__).resolve().parent.parent / "infra"

FOR_EACH = """
resource "conteneur" "app" {
  for_each = var.environnements
  nom      = "jobportal-${each.key}"
  image    = "jobportal:1.4.0"
}
variable "environnements" {
  type    = list(string)
  default = ["dev", "recette", "staging", "prod"]
}
"""

COUNT = """
resource "conteneur" "app" {
  count = length(var.environnements)
  nom   = "jobportal-${var.environnements[count.index]}"
  image = "jobportal:1.4.0"
}
variable "environnements" {
  type    = list(string)
  default = ["dev", "recette", "staging", "prod"]
}
"""


@pytest.fixture
def tf(tmp_path: Path) -> Terraform:
    return Terraform(INFRA, etat=tmp_path / "s.tfstate",
                     realite=tmp_path / "r.json")


def _projet(tmp_path: Path, source: str) -> Terraform:
    dossier = tmp_path / "code"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "main.tf").write_text(source, encoding="utf-8")
    return Terraform(dossier, etat=tmp_path / "s.tfstate",
                     realite=tmp_path / "r.json")


def test_le_premier_plan_ne_contient_que_des_creations(tf: Terraform):
    plan = tf.plan()

    assert plan.compter(Action.CREER) == 3
    assert plan.compter(Action.DETRUIRE) == 0
    assert plan.resume == "Plan: 3 to add, 0 to change, 0 to destroy."


def test_appliquer_deux_fois_ne_change_rien(tf: Terraform):
    """L'idempotence : ce qui distingue un outil declaratif d'un script."""
    tf.apply()

    assert tf.plan().vide
    assert len(tf.realite().tout()) == 3

    tf.apply()
    assert len(tf.realite().tout()) == 3


def test_un_attribut_ordinaire_se_modifie_en_place(tf: Terraform):
    tf.apply()

    plan = tf.plan({"version_image": "1.5.0"})

    assert plan.compter(Action.MODIFIER) == 3
    assert plan.compter(Action.REMPLACER) == 0


def test_un_attribut_identifiant_force_un_remplacement(tf: Terraform):
    """⚠️ Le cas qui coute cher : un changement de nom detruit et recree."""
    tf.apply()

    plan = tf.plan({"prefixe": "portail"})

    assert plan.compter(Action.REMPLACER) == 3
    assert plan.compter(Action.MODIFIER) == 0
    assert "3 to add" in plan.resume and "3 to destroy" in plan.resume


def test_retirer_un_element_produit_une_destruction(tf: Terraform):
    tf.apply()

    plan = tf.plan({"environnements": ["dev", "prod"]})

    assert plan.compter(Action.DETRUIRE) == 1


def test_for_each_contre_count(tmp_path: Path):
    """⚠️ La mesure du chapitre 2 : 1 destruction contre 3.

    Retirer un element AU MILIEU d'une liste ne change rien aux cles des
    autres ; il decale en revanche toutes les positions suivantes.
    """
    trois = ["dev", "staging", "prod"]

    avec_cles = _projet(tmp_path / "a", FOR_EACH)
    avec_cles.apply()
    plan_cles = avec_cles.plan({"environnements": trois})

    avec_rangs = _projet(tmp_path / "b", COUNT)
    avec_rangs.apply()
    plan_rangs = avec_rangs.plan({"environnements": trois})

    detruites_par_cle = (plan_cles.compter(Action.DETRUIRE)
                         + plan_cles.compter(Action.REMPLACER))
    detruites_par_rang = (plan_rangs.compter(Action.DETRUIRE)
                          + plan_rangs.compter(Action.REMPLACER))

    assert detruites_par_cle == 1
    assert detruites_par_rang == 3


def test_les_attributs_calcules_ne_font_pas_de_difference(tf: Terraform):
    """Sinon chaque plan annoncerait une modification imaginaire."""
    tf.apply()
    etat = tf.etat()
    instance = etat.ressources["conteneur.app"].instances[0]

    assert "mot_de_passe" in instance.attributs
    assert tf.plan().vide


def test_la_validation_arrete_avant_le_plan(tf: Terraform):
    with pytest.raises(ErreurConfiguration, match="small ou medium"):
        tf.plan({"taille": "enorme"})


def test_le_type_arrete_avant_le_plan(tf: Terraform):
    with pytest.raises(ErreurConfiguration, match="number"):
        tf.plan({"memoire": "beaucoup"})


def test_destroy_vide_tout(tf: Terraform):
    tf.apply()

    tf.destroy()

    assert tf.realite().tout() == {}
    assert tf.state_list() == []


def test_un_module_cree_des_adresses_prefixees(tmp_path: Path):
    appelant = Path(__file__).resolve().parent.parent / "infra-modules"
    tf = Terraform(appelant, etat=tmp_path / "s.tfstate",
                   realite=tmp_path / "r.json")

    tf.apply()

    adresses = tf.state_list()
    assert len(adresses) == 4
    assert all(adresse.startswith("module.") for adresse in adresses)
    assert "module.reseau_prod.reseau.ce" in adresses


def test_les_outputs_dun_module_remontent(tmp_path: Path):
    appelant = Path(__file__).resolve().parent.parent / "infra-modules"
    tf = Terraform(appelant, etat=tmp_path / "s.tfstate",
                   realite=tmp_path / "r.json")

    sorties = tf.configuration().sorties

    assert sorties["reseaux"] == ["jobportal-prod", "jobportal-staging"]
