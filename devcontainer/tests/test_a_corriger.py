"""Les douze configurations fautives, et qui attrape quoi.

Cinq sont refusées par le schéma publié ; sept passent et méritent quand
même un mot. Ce tableau est la mesure centrale du projet : il dit exactement ce
qu'un schéma peut faire, et ce qu'il ne peut pas.

**Ne pas « réparer » `configs/a-corriger/`** : ces fichiers sont la pièce à
conviction.
"""

from __future__ import annotations

import pytest

from jobportal import schema_publie
from jobportal.commun import A_CORRIGER, PORTAIL
from jobportal.config import charger
from outils.verifier_devcontainer import avertissements

FICHIERS = sorted(A_CORRIGER.glob("*.json"))

# (nom, refuse par le schema ?, nombre d'avertissements attendu)
ATTENDU = {
    "01-contexte-point.json": (False, 1),
    "02-image-et-build.json": (True, 0),
    "03-shutdown-croise.json": (True, 0),
    "04-compose-incomplet.json": (True, 0),
    "05-faute-de-frappe.json": (True, 0),
    "06-waitfor-trop-loin.json": (True, 1),
    "07-tout-dans-postcreate.json": (False, 2),
    "08-tableau-avec-shell.json": (False, 3),
    "09-attach-lourd.json": (False, 1),
    "10-option-inconnue.json": (False, 1),
    "11-ordre-impossible.json": (False, 1),
    "12-virgule-finale.json": (False, 0),
}


def test_douze_fichiers():
    assert [p.name for p in FICHIERS] == sorted(ATTENDU)


@pytest.mark.parametrize("nom", sorted(ATTENDU), ids=lambda n: n[:2])
def test_le_verdict_du_schema(nom):
    refuse, _ = ATTENDU[nom]
    config = charger(A_CORRIGER / nom)
    assert schema_publie.valide(config) is not refuse


@pytest.mark.parametrize("nom", sorted(ATTENDU), ids=lambda n: n[:2])
def test_le_nombre_d_avertissements(nom):
    _, combien = ATTENDU[nom]
    config = charger(A_CORRIGER / nom)
    avis = avertissements(config, PORTAIL)
    assert len(avis) == combien, avis


def test_cinq_refuses_sept_acceptes():
    """La mesure centrale : le schema n'attrape pas la moitie des fautes."""
    refuses = sum(1 for nom, (r, _) in ATTENDU.items() if r)
    assert refuses == 5
    assert len(ATTENDU) - refuses == 7


# ── le diagnostic, faute par faute ──────────────────────────────────────

def diagnostic(nom: str) -> str:
    return " | ".join(m for _, m in
                      schema_publie.verifier(charger(A_CORRIGER / nom)))


def test_02_les_trois_points_de_depart_s_excluent():
    assert "s'excluent" in diagnostic("02-image-et-build.json")


def test_03_l_enumeration_est_celle_de_la_branche():
    message = diagnostic("03-shutdown-croise.json")
    assert "stopContainer" in message
    assert "stopCompose" in message


def test_04_workspacefolder_manque():
    assert "workspaceFolder" in diagnostic("04-compose-incomplet.json")


def test_05_la_faute_de_frappe_est_nommee():
    assert "postCreatCommand" in diagnostic("05-faute-de-frappe.json")


def test_06_waitfor_n_accepte_pas_postattach():
    message = diagnostic("06-waitfor-trop-loin.json")
    assert "postAttachCommand" in message
    assert "is not one of" in message


# ── les avertissements, un par un ───────────────────────────────────────

def avis(nom: str) -> str:
    return " | ".join(avertissements(charger(A_CORRIGER / nom), PORTAIL))


def test_01_le_contexte_ne_remonte_pas():
    assert "ne remonte pas d'un cran" in avis("01-contexte-point.json")


def test_07_la_decoupe_est_perdue_et_la_main_arrive_trop_tot():
    message = avis("07-tout-dans-postcreate.json")
    assert "rien ne peut se preconstruire" in message
    assert "avant la fin de : postCreateCommand" in message


def test_08_les_operateurs_sont_inertes():
    message = avis("08-tableau-avec-shell.json")
    assert message.count("SANS shell") == 2


def test_09_le_cout_par_onglet():
    assert "a CHAQUE connexion" in avis("09-attach-lourd.json")


def test_10_l_option_est_ignoree_en_silence():
    message = avis("10-option-inconnue.json")
    assert "versionne" in message
    assert "ignoree(s) en silence" in message


def test_11_la_feature_est_installee_deux_fois():
    assert "installee 2 fois" in avis("11-ordre-impossible.json")


def test_12_la_virgule_finale_n_est_pas_un_avertissement_de_config():
    """Elle est signalee par l'outil au niveau du TEXTE, pas de l'objet :
    une fois le fichier lu, elle a disparu.
    """
    from jobportal.jsonc import virgules_finales
    chemin = A_CORRIGER / "12-virgule-finale.json"
    assert avertissements(charger(chemin), PORTAIL) == []
    assert virgules_finales(chemin.read_text(encoding="utf-8")) == [8]


# ── le dev container du projet, lui, est propre ─────────────────────────

def test_le_portail_ne_declenche_rien():
    portail = charger(PORTAIL / "devcontainer.json")
    assert schema_publie.valide(portail) is True
    assert avertissements(portail) == []
