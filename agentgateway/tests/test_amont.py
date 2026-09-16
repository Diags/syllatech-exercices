"""Le garde-fou : les 27 configurations d'exemple du dépôt doivent passer.

C'est ce qui rend l'outil crédible quand il refuse une configuration. Si l'un
de ces fichiers cesse de valider, c'est que `amont/config.schema.json` a bougé
— pas que l'exemple a tort.
"""

from __future__ import annotations

import pytest

from jobportal import schema_publie
from jobportal.commun import AMONT, EXEMPLES_AMONT, SCHEMA
from jobportal.config import (
    FOURNISSEURS, SECTIONS, TYPES_DE_BACKEND, TYPES_DE_CIBLE_MCP, charger,
)

FICHIERS = sorted(EXEMPLES_AMONT.glob("*.yaml"))


def test_vingt_sept_exemples():
    assert len(FICHIERS) == 27


@pytest.mark.parametrize("chemin", FICHIERS, ids=lambda p: p.stem)
def test_un_exemple_amont_passe_le_schema(chemin):
    assert schema_publie.verifier(charger(chemin)) == []


@pytest.mark.parametrize("chemin", FICHIERS, ids=lambda p: p.stem)
def test_un_exemple_amont_n_a_que_des_sections_connues(chemin):
    assert charger(chemin).sections_inconnues == []


def test_le_schema_est_bien_celui_du_depot():
    document = schema_publie.document()
    assert document["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert document["title"] == "LocalConfig"
    assert len(document["$defs"]) > 300


def test_le_fichier_de_schema_n_a_pas_ete_resume():
    assert SCHEMA.stat().st_size > 300_000


def test_les_quatorze_sections_sont_celles_du_schema():
    assert set(SECTIONS) == set(schema_publie.document()["properties"])


def test_les_dix_branches_de_backend():
    assert set(TYPES_DE_BACKEND) == set(schema_publie.branches("LocalRouteBackend"))


def test_a2a_n_est_pas_un_backend_mais_une_politique():
    """Le point du chapitre 4, verrouillé."""
    assert "a2a" not in TYPES_DE_BACKEND
    assert "a2a" in schema_publie.definitions()["FilterOrPolicy"]["properties"]


def test_les_huit_fournisseurs_et_la_casse():
    assert set(FOURNISSEURS) == set(schema_publie.branches("AIProvider"))
    assert "openAI" in FOURNISSEURS
    assert "openai" not in FOURNISSEURS
    assert "selfHosted" not in FOURNISSEURS


def test_les_quatre_cibles_mcp():
    assert set(TYPES_DE_CIBLE_MCP) == set(schema_publie.branches("LocalMcpTarget"))


def test_les_cinq_builtins_de_guardrail():
    assert schema_publie.constantes("Builtin") == [
        "ssn", "creditCard", "phoneNumber", "email", "caSin"]
    assert "credit_card" not in schema_publie.constantes("Builtin")


def test_le_mode_jwt_par_defaut_laisse_passer():
    """La mesure centrale du chapitre 5, citée verbatim."""
    modes = schema_publie.constantes("Mode")
    assert modes == ["strict", "optional", "permissive"]
    optionnel = schema_publie.description("Mode", "optional")
    assert "This is the default option" in optionnel
    assert "allows requests without a JWT" in optionnel


def test_l_action_d_un_garde_est_mask_par_defaut():
    assert schema_publie.defaut("RegexRules", "action") == "mask"


def test_une_route_sans_matches_attrape_tout():
    assert schema_publie.defaut("LocalRoute", "matches") == [
        {"path": {"pathPrefix": "/"}}]


def test_le_prefixage_a_trois_modes():
    assert set(schema_publie.constantes("McpPrefixMode")) == {
        "conditional", "always", "never"}


def test_binds_est_declare_bas_niveau():
    description = schema_publie.document()["properties"]["binds"]["description"]
    assert "low-level API" in description


def test_le_contexte_cel_documente_mcp_tool_name():
    """`cel.md` est la source du chapitre 5 sur le nom resolu."""
    texte = (AMONT / "cel.md").read_text(encoding="utf-8")
    assert "The resolved tool name sent to the upstream target." in texte
    assert "after multiplexing resolution" in texte


def test_les_fonctions_ajoutees_sont_documentees():
    texte = (AMONT / "cel-functions.md").read_text(encoding="utf-8")
    for fonction in ("default", "coalesce", "regexReplace"):
        assert f"`{fonction}`" in texte


def test_le_deny_est_declare_faillible():
    """La citation qui fait tout le chapitre 5, section 5."""
    formes = schema_publie.definitions()["RuleSerde"]["anyOf"][0]["oneOf"]
    deny = next(b for b in formes if "deny" in (b.get("required") or []))
    assert "expression failures fail to deny" in deny["description"]
