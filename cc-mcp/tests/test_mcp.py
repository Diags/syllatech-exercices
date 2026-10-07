"""Ce que le serveur et ses permissions doivent garantir.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))

from jobportal import donnees, serveur as srv          # noqa: E402
from verifier_acces import (ancree, correspond, outils_reels,  # noqa: E402
                            verifier)


def soucis(dossier: Path):
    return verifier(dossier)


def erreurs(dossier: Path):
    return [s for s in soucis(dossier) if s.gravite == "erreur"]


# ------------------------------------------------------------- le serveur

async def test_le_serveur_expose_les_quatre_outils():
    noms = await srv.outils_exposes()
    assert set(noms) == {"rechercher_offres", "statistiques_candidatures",
                         "offres_sans_candidature", "supprimer_offre"}


async def test_chaque_outil_porte_une_description():
    """La docstring est le SEUL indice du modele. Un outil sans description
    ne se declenche jamais, et rien ne le signale."""
    for outil in await srv.serveur.list_tools():
        assert outil.description and len(outil.description) > 40, outil.name


async def test_chaque_outil_a_un_schema_d_entree():
    """Deduit des annotations de type. Sans annotation, le modele passe
    n'importe quoi."""
    for outil in await srv.serveur.list_tools():
        assert "properties" in outil.input_schema, outil.name


async def test_le_schema_est_une_ressource_et_non_un_outil():
    """Une ressource se lit, un outil agit. Exposer le schema comme un outil
    le rendrait interdisable — alors qu'il n'y a rien a interdire."""
    ressources = {str(r.uri) for r in await srv.serveur.list_resources()}
    noms = await srv.outils_exposes()
    assert "schema://tables" in ressources
    assert not any("schema" in n for n in noms)


# ------------------------------------------------------------ les donnees

def test_la_recherche_filtre_bien_par_ville():
    for offre in srv.rechercher_offres("Python", "Lyon"):
        assert offre["ville"] == "Lyon"
        assert "Python" in offre["titre"]


def test_la_recherche_sans_ville_rend_plus_de_resultats():
    assert len(srv.rechercher_offres("Python")) > len(srv.rechercher_offres("Python", "Lyon"))


def test_le_titre_et_la_colonne_ville_concordent():
    """Une base incoherente apprend a douter des donnees, pas du code."""
    for offre in donnees.query("SELECT titre, ville FROM offres LIMIT 50"):
        assert offre["titre"].endswith(offre["ville"])


def test_la_base_est_deterministe():
    a = donnees.ouvrir().execute("SELECT id, titre FROM offres").fetchall()
    b = donnees.ouvrir().execute("SELECT id, titre FROM offres").fetchall()
    assert [tuple(r) for r in a] == [tuple(r) for r in b]


def test_les_offres_sans_candidature_n_en_ont_vraiment_aucune():
    for offre in srv.offres_sans_candidature():
        assert donnees.query("SELECT id FROM candidatures WHERE offre_id = ?",
                             offre["id"]) == []


def test_la_suppression_emporte_les_candidatures():
    """Un outil de permission n'a de sens que sur un outil capable d'agir."""
    base = donnees.ouvrir()
    donnees.BASE, ancienne = base, donnees.BASE
    try:
        avant = len(donnees.query("SELECT id FROM candidatures WHERE offre_id = 'off-000'"))
        assert avant > 0
        resultat = srv.supprimer_offre("off-000")
        assert resultat["offres_supprimees"] == 1
        assert resultat["candidatures_supprimees"] == avant
        assert donnees.query("SELECT id FROM offres WHERE id = 'off-000'") == []
    finally:
        donnees.BASE = ancienne


# --------------------------------------------------- les globs de permission

@pytest.mark.parametrize("regle, attendu", [
    ("mcp__jobportal__*", True),
    ("mcp__jobportal__recherche*", True),
    ("mcp__jobportal__rechercher_offres", True),
    ("mcp__jobportal__.*", False),        # une regex, pas un glob
    ("mcp__autre__*", False),
])
def test_un_glob_de_permission_n_est_pas_une_regex(regle, attendu):
    assert correspond(regle, "mcp__jobportal__rechercher_offres") is attendu


@pytest.mark.parametrize("regle, attendu", [
    ("mcp__jobportal__*", True),
    ("mcp__jobportal__rechercher_offres", True),
    ("mcp__*", False),          # segment serveur non litteral : ignore
    ("mcp__job*__lire", False),
])
def test_un_glob_d_autorisation_doit_nommer_un_serveur_litteral(regle, attendu):
    assert ancree(regle) is attendu


# ---------------------------------------------- la configuration du projet

def test_la_configuration_livree_est_propre():
    """Si ce test tombe, le projet enseigne ce qu'il denonce."""
    assert soucis(RACINE) == [], [s.message for s in soucis(RACINE)]


def test_tous_les_outils_du_serveur_sont_couverts_par_une_regle():
    reglages = json.loads((RACINE / ".claude" / "settings.json").read_text(encoding="utf-8"))
    regles = (reglages["permissions"].get("allow", [])
              + reglages["permissions"].get("deny", []))
    for outil in outils_reels():
        assert any(correspond(r, outil) for r in regles), outil


def test_l_outil_d_ecriture_est_refuse():
    reglages = json.loads((RACINE / ".claude" / "settings.json").read_text(encoding="utf-8"))
    assert any(correspond(r, "mcp__jobportal__supprimer_offre")
               for r in reglages["permissions"]["deny"])


def test_aucun_secret_en_clair_dans_le_mcp_json():
    brut = (RACINE / ".mcp.json").read_text(encoding="utf-8")
    assert "${GITHUB_PAT}" in brut
    assert "ghp_" not in brut


# ------------------------------------------- la configuration a corriger

@pytest.fixture(scope="module")
def casse():
    return {s.ou: s.message for s in soucis(RACINE / "config-a-corriger")}


def test_la_faute_de_frappe_est_attrapee(casse):
    """LE defaut du chapitre 4. Les noms MCP contiennent « _ », donc Claude
    Code est exempte du controle de faute de frappe : aucun avertissement,
    la regle ne correspond a rien, l'outil reste autorise."""
    assert "deny / mcp__jobportal__supprimer_ofre" in casse
    assert "AUCUN outil" in casse["deny / mcp__jobportal__supprimer_ofre"]


def test_la_consequence_de_la_faute_est_signalee_aussi(casse):
    """Deux messages, et c'est voulu : la regle caduque, ET l'outil
    d'ecriture laisse sans protection. Le second est celui qui coute."""
    assert "ECRITURE" in casse["mcp__jobportal__supprimer_offre"]


def test_un_glob_non_ancre_est_une_erreur(casse):
    assert "n'autorise rien" in casse["allow / mcp__*"]


def test_le_secret_en_clair_est_une_erreur(casse):
    assert "secret en clair" in casse[".mcp.json"]


def test_le_transport_sse_est_signale(casse):
    assert "deprecie" in casse[".mcp.json/notifications"]


def test_une_url_sans_type_est_signalee(casse):
    assert "type" in casse[".mcp.json/github"]


def test_la_configuration_fautive_echoue_vraiment():
    assert len(erreurs(RACINE / "config-a-corriger")) >= 4


def test_une_variable_dollar_n_est_pas_prise_pour_un_secret(tmp_path):
    """Sinon le verificateur refuserait la BONNE forme, et personne ne
    l'utiliserait."""
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".mcp.json").write_text(
        json.dumps({"mcpServers": {"a": {"type": "http", "url": "https://x/mcp",
                                         "headers": {"Authorization": "Bearer ${TOKEN}"}}}}),
        encoding="utf-8")
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"deny": ["mcp__jobportal__supprimer_offre"]}}),
        encoding="utf-8")
    assert not any("secret en clair" in s.message for s in verifier(tmp_path))


def test_un_settings_absent_est_une_erreur(tmp_path):
    assert any("absent" in s.message for s in verifier(tmp_path))
