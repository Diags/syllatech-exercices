"""Autorisation : les trois formes, et le trou que le schéma annonce."""

from __future__ import annotations

import pytest

from jobportal import autorisation
from jobportal.commun import PORTAIL
from jobportal.config import charger

DATA = {"sub": "u1", "team": "data"}
RH = {"sub": "u2", "team": "rh"}
SANS_TEAM = {"sub": "u3"}
REGLE = 'jwt.team == "data" && mcp.tool.name.startsWith("postgres_")'


def decider(regles, outil, claims):
    return autorisation.decider(
        regles, autorisation.contexte_mcp(outil, claims=claims))


# ── lecture ─────────────────────────────────────────────────────────────

def test_une_chaine_nue_vaut_allow():
    """C'est la forme des exemples amont."""
    regles = autorisation.lire(['mcp.tool.name == "echo"'])
    assert regles == [autorisation.Regle("allow", 'mcp.tool.name == "echo"')]


def test_les_trois_formes():
    regles = autorisation.lire({"rules": [
        {"allow": "a"}, {"require": "b"}, {"deny": "c"}]})
    assert [r.forme for r in regles] == ["allow", "require", "deny"]


def test_une_entree_inconnue_est_ignoree():
    assert autorisation.lire([{"maybe": "x"}]) == []


# ── allow ───────────────────────────────────────────────────────────────

def test_allow_vrai_autorise():
    regles = [autorisation.Regle("allow", REGLE)]
    assert decider(regles, "postgres_query", DATA).autorise is True


def test_allow_faux_refuse():
    regles = [autorisation.Regle("allow", REGLE)]
    assert decider(regles, "postgres_query", RH).autorise is False


def test_allow_qui_leve_refuse():
    """Une expression non defensive sur un `allow` refuse — par accident."""
    regles = [autorisation.Regle("allow", REGLE)]
    verdict = decider(regles, "postgres_query", SANS_TEAM)
    assert verdict.autorise is False


def test_un_seul_allow_vrai_suffit():
    regles = autorisation.lire([{"allow": "false"}, {"allow": "true"}])
    assert decider(regles, "x", DATA).autorise is True


def test_sans_aucun_allow_rien_ne_s_y_oppose():
    assert decider([], "x", DATA).autorise is True


# ── deny : le trou annonce ──────────────────────────────────────────────

def test_deny_vrai_refuse():
    regles = [autorisation.Regle("deny", 'jwt.team == "rh"')]
    assert decider(regles, "postgres_query", RH).autorise is False


def test_deny_qui_leve_LAISSE_PASSER():
    """« expression failures fail to deny » — la citation du schema, mesuree.

    C'est le meme genre d'erreur d'ecriture que `test_allow_qui_leve_refuse`,
    et l'effet est exactement inverse.
    """
    regles = [autorisation.Regle(
        "deny", 'jwt.team != "data" && mcp.tool.name.startsWith("postgres_")')]
    verdict = decider(regles, "postgres_query", SANS_TEAM)
    assert verdict.autorise is True


def test_le_meme_deny_ecrit_defensivement_refuse():
    regles = [autorisation.Regle(
        "deny",
        '(!has(jwt.team) || jwt.team != "data") '
        '&& mcp.tool.name.startsWith("postgres_")')]
    assert decider(regles, "postgres_query", SANS_TEAM).autorise is False


# ── require ─────────────────────────────────────────────────────────────

def test_require_faux_refuse_malgre_un_allow_vrai():
    regles = autorisation.lire([{"allow": "true"}, {"require": "has(jwt.sub)"}])
    assert decider(regles, "x", None).autorise is False


def test_require_vrai_laisse_les_allow_decider():
    regles = autorisation.lire([{"require": "has(jwt.sub)"},
                                {"allow": 'jwt.team == "data"'}])
    assert decider(regles, "x", DATA).autorise is True
    assert decider(regles, "x", RH).autorise is False


def test_require_qui_leve_refuse():
    regles = autorisation.lire([{"require": 'jwt.absent == "x"'}])
    verdict = decider(regles, "x", DATA)
    assert verdict.autorise is False
    assert "illisible" in verdict.motif


# ── ecriture defensive ──────────────────────────────────────────────────

@pytest.mark.parametrize("expression, defensive", [
    ('jwt.team == "data"', False),
    ('has(jwt.team) && jwt.team == "data"', True),
    ('default(jwt.team, "") == "data"', True),
])
def test_reperage_de_l_ecriture_defensive(expression, defensive):
    assert autorisation.defensive(expression) is defensive


# ── la route protegee du portail ────────────────────────────────────────

def regles_du_portail():
    route = charger(PORTAIL / "03-securite.yaml").routes()[0]
    return autorisation.lire(route.politiques["mcpAuthorization"])


def test_toutes_les_regles_du_portail_sont_defensives():
    assert all(autorisation.defensive(r.expression) for r in regles_du_portail())


def test_toutes_les_regles_du_portail_compilent():
    for regle in regles_du_portail():
        ok, message = autorisation.compile_t_elle(regle.expression)
        assert ok, f"{regle.expression} : {message}"


@pytest.mark.parametrize("claims, outil, attendu", [
    (RH, "offres_chercher", True),
    (RH, "annuaire_verifier", False),
    (DATA, "annuaire_verifier", True),
    (DATA, "offres_chercher", False),
    (None, "offres_chercher", False),
    (None, "annuaire_verifier", False),
    (SANS_TEAM, "offres_chercher", False),
])
def test_la_matrice_du_portail(claims, outil, attendu):
    assert decider(regles_du_portail(), outil, claims).autorise is attendu


def test_c_est_la_regle_require_qui_refuse_l_absence_de_jeton():
    verdict = decider(regles_du_portail(), "offres_chercher", None)
    assert "require" in verdict.motif
    assert "has(jwt.sub)" in verdict.motif


def test_sans_la_regle_require_le_refus_serait_un_effet_de_bord():
    sans_require = [r for r in regles_du_portail() if r.forme != "require"]
    verdict = decider(sans_require, "offres_chercher", None)
    assert verdict.autorise is False
    assert "aucune regle allow" in verdict.motif
