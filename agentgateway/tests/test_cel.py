"""CEL : ce qui est évalué pour de bon, et ce qui est signalé.

Deux familles de tests ici. Les premiers vérifient que `cel-python` évalue
bien les expressions — c'est ce qui distingue ce projet d'une comparaison de
chaînes. Les seconds fixent le comportement sur les fonctions qu'agentgateway
ajoute au langage : elles sont SIGNALÉES, jamais devinées.
"""

from __future__ import annotations

import pytest

from jobportal import autorisation, modeles
from jobportal.commun import EXEMPLES_AMONT, PORTAIL
from jobportal.config import charger

CONTEXTE_DATA = {"jwt": {"sub": "u1", "team": "data"},
                 "mcp": {"tool": {"name": "postgres_query"}}}


# ── evaluation reelle ───────────────────────────────────────────────────

@pytest.mark.parametrize("expression, attendu", [
    ('jwt.team == "data"', True),
    ('jwt.team == "rh"', False),
    ('mcp.tool.name.startsWith("postgres_")', True),
    ('mcp.tool.name.startsWith("offres_")', False),
    ('jwt.team == "data" && mcp.tool.name.startsWith("postgres_")', True),
    ('has(jwt.team)', True),
    ('has(jwt.absent)', False),
    ('size(jwt.sub) == 2', True),
])
def test_une_expression_est_vraiment_evaluee(expression, attendu):
    assert modeles.evaluer(expression, CONTEXTE_DATA) is attendu


def test_une_revendication_absente_fait_lever():
    """Le coeur du chapitre 5 : ce n'est pas faux, c'est une ERREUR."""
    with pytest.raises(modeles.ErreurDeCEL):
        modeles.evaluer('jwt.team == "data"',
                        {"jwt": {"sub": "u"}, "mcp": {"tool": {"name": "x"}}})


def test_has_protege_de_la_levee():
    assert modeles.evaluer('has(jwt.team) && jwt.team == "data"',
                           {"jwt": {"sub": "u"}, "mcp": {}}) is False


def test_une_expression_qui_ne_compile_pas():
    with pytest.raises(modeles.ErreurDeCEL):
        modeles.evaluer('jwt.team ==== "data"', CONTEXTE_DATA)


def test_compile_t_elle_distingue_compilation_et_evaluation():
    assert autorisation.compile_t_elle('jwt.absent == "x"')[0] is True
    assert autorisation.compile_t_elle('jwt.team ==== "x"')[0] is False


# ── extensions agentgateway ─────────────────────────────────────────────

@pytest.mark.parametrize("expression, attendues", [
    ('default(llmRequest.max_tokens, 1024) <= 512', ["default"]),
    ('coalesce(a, b, "x") == "x"', ["coalesce"]),
    ('json(request.body).id == "1"', ["json"]),
    ('has(jwt.team)', []),
    ('mcp.tool.name.startsWith("x")', []),
])
def test_reperage_des_extensions(expression, attendues):
    assert modeles.extensions_utilisees(expression) == attendues


def test_une_extension_est_signalee_pas_devinee():
    with pytest.raises(modeles.ExtensionAgentgateway):
        modeles.evaluer('default(llmRequest.max_tokens, 1024) <= 512',
                        {"llmRequest": {}})


def test_l_exemple_amont_de_cout_utilise_default():
    """Le cas reel : `amont/exemples/llm-cost-routing.yaml` s'appuie sur
    `default`, que ce projet ne peut pas evaluer — et le dit.
    """
    config = charger(EXEMPLES_AMONT / "llm-cost-routing.yaml")
    expression = modeles.modeles_virtuels(config)[0]["routing"]["conditional"] \
        ["targets"][0]["when"]
    assert "default" in modeles.extensions_utilisees(expression)


# ── les trois formes de routage ─────────────────────────────────────────

def test_conditionnel_premiere_regle_vraie():
    routage = {"conditional": {"targets": [
        {"when": 'has(llmRequest.urgent) && llmRequest.urgent', "model": "a"},
        {"when": 'has(llmRequest.court) && llmRequest.court', "model": "b"},
        {"model": "repli"},
    ]}}
    assert modeles.choisir(routage, {"llmRequest": {"urgent": True}}).modele == "a"
    assert modeles.choisir(routage, {"llmRequest": {"court": True}}).modele == "b"
    assert modeles.choisir(routage, {"llmRequest": {}}).modele == "repli"
    assert modeles.choisir(routage, {"llmRequest": {}}).regle == "(repli)"


def test_conditionnel_sans_repli_ne_choisit_rien():
    routage = {"conditional": {"targets": [
        {"when": 'has(llmRequest.urgent) && llmRequest.urgent', "model": "a"}]}}
    with pytest.raises(modeles.ErreurDeCEL):
        modeles.choisir(routage, {"llmRequest": {}})


def test_la_premiere_vraie_gagne_meme_si_la_suivante_l_est_aussi():
    """« targets are evaluated in order. The first matching condition
    selects the model. »
    """
    routage = {"conditional": {"targets": [
        {"when": "true", "model": "premier"},
        {"when": "true", "model": "second"},
    ]}}
    assert modeles.choisir(routage, {}).modele == "premier"


def test_failover_prend_la_priorite_la_plus_basse():
    routage = {"failover": {"targets": [
        {"model": "secours", "priority": 5},
        {"model": "principal", "priority": 0},
    ]}}
    decision = modeles.choisir(routage, {})
    assert decision.modele == "principal"
    assert decision.forme == "failover"


def test_weighted_rend_la_repartition():
    routage = {"weighted": {"targets": [
        {"model": "a", "weight": 3}, {"model": "b", "weight": 1}]}}
    assert modeles.repartition(routage) == [("a", "75%"), ("b", "25%")]


def test_le_poids_vaut_un_par_defaut():
    routage = {"weighted": {"targets": [{"model": "a"}, {"model": "b"}]}}
    assert modeles.repartition(routage) == [("a", "50%"), ("b", "50%")]


# ── le catalogue du portail ─────────────────────────────────────────────

def test_les_conditions_du_portail_sont_du_cel_standard():
    config = charger(PORTAIL / "02-llm.yaml")
    virtuel = next(m for m in modeles.modeles_virtuels(config)
                   if "conditional" in m["routing"])
    for cible in virtuel["routing"]["conditional"]["targets"]:
        if cible.get("when"):
            assert modeles.extensions_utilisees(cible["when"]) == []


def test_le_portail_choisit_bien():
    config = charger(PORTAIL / "02-llm.yaml")
    virtuel = next(m for m in modeles.modeles_virtuels(config)
                   if "conditional" in m["routing"])
    cas = [
        ({"llmRequest": {"metadata": {"urgence": "haute"}}}, "tri-soigne"),
        ({"llmRequest": {"max_tokens": 200}}, "tri-rapide"),
        ({"llmRequest": {"max_tokens": 4000}}, "tri-soigne"),
        ({"llmRequest": {}}, "tri-soigne"),
    ]
    for contexte, attendu in cas:
        assert modeles.choisir(virtuel["routing"], contexte).modele == attendu


def test_les_modeles_du_portail_sont_internes():
    config = charger(PORTAIL / "02-llm.yaml")
    for nom in modeles.modeles_declares(config):
        assert modeles.visibilite(config, nom) == "internal"
