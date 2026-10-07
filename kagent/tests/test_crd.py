"""L'admission : ce qui est refuse, ce qui est elague, ce qui est ajoute.

Le test central est `test_une_faute_de_frappe_est_elaguee_en_silence` : il
fige la mesure du chapitre 2.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import controleur, crd, schemas, yaml_minimal

MANIFESTES = Path(__file__).resolve().parent.parent / "manifestes"


def charger(nom: str) -> list[dict]:
    return yaml_minimal.charger_fichier_tous(MANIFESTES / nom)


# ── ce qui est refuse ────────────────────────────────────────────────────

def test_un_type_hors_enumeration_est_refuse():
    verdict = crd.admettre(schemas.AGENT, charger("agent-invalide.yaml")[0])

    assert not verdict.valide
    assert any("enumeration" in str(p) for p in verdict.problemes)


def test_la_regle_transverse_exige_un_corps():
    """⚠️ Une union discriminee : `oneOf` est interdit dans un schema
    structurel, donc Kubernetes l'ecrit en CEL."""
    verdict = crd.admettre(schemas.AGENT, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "x"}, "spec": {"type": "Declarative"}})

    assert not verdict.valide
    assert any("declarative" in str(p) for p in verdict.problemes)


def test_les_deux_corps_ensemble_sont_refuses():
    verdict = crd.admettre(schemas.AGENT, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "x"},
        "spec": {"type": "Declarative",
                 "declarative": {"modelConfig": "m"},
                 "byo": {"deployment": {}}}})

    assert not verdict.valide
    assert any("exclusifs" in str(p) for p in verdict.problemes)


def test_un_champ_obligatoire_absent_est_refuse():
    verdict = crd.admettre(schemas.MODEL_CONFIG, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "ModelConfig",
        "metadata": {"name": "x"}, "spec": {"provider": "Anthropic"}})

    assert not verdict.valide
    assert any("model" in str(p) and "obligatoire" in str(p)
               for p in verdict.problemes)


@pytest.mark.parametrize("valeur, valide", [
    (0.0, True), (1.5, True), (2.0, True), (2.5, False), (-0.1, False),
])
def test_les_bornes_numeriques(valeur: float, valide: bool):
    verdict = crd.admettre(schemas.MODEL_CONFIG, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "ModelConfig",
        "metadata": {"name": "x"},
        "spec": {"provider": "Anthropic", "model": "m",
                 "temperature": valeur}})

    assert verdict.valide is valide


def test_un_booleen_nest_pas_un_entier():
    """En Python, `True` EST un `int`. Le schema ne doit pas s'y laisser
    prendre."""
    verdict = crd.admettre(schemas.AGENT, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "x"},
        "spec": {"type": "Declarative",
                 "declarative": {"modelConfig": "m", "maxIterations": True}}})

    assert not verdict.valide


def test_une_url_est_exigee_en_http():
    sans_url = {"apiVersion": "kagent.dev/v1alpha2", "kind": "RemoteMCPServer",
                "metadata": {"name": "x"},
                "spec": {"protocol": "STREAMABLE_HTTP"}}

    assert not crd.admettre(schemas.REMOTE_MCP_SERVER, sans_url).valide
    sans_url["spec"]["url"] = "http://x:8080/mcp"
    assert crd.admettre(schemas.REMOTE_MCP_SERVER, sans_url).valide


# ── ce qui est elague ────────────────────────────────────────────────────

def test_une_faute_de_frappe_est_elaguee_en_silence():
    """⚠️ LA MESURE DU CHAPITRE 2 : admis, Ready, et sans prompt."""
    verdict = crd.admettre(schemas.AGENT,
                           charger("agent-faute-de-frappe.yaml")[0])

    assert verdict.valide                      # aucune erreur
    assert verdict.silencieux                  # et pourtant ampute
    assert verdict.elagues == ["spec.declarative.systemMesssage",
                               "spec.declarative.maxIteration"]
    corps = verdict.objet["spec"]["declarative"]
    assert corps["systemMessage"] == ""        # le defaut, pas le texte voulu
    assert corps["maxIterations"] == 10


def test_un_manifeste_correct_nest_pas_elague():
    verdict = crd.admettre(schemas.AGENT, charger("agent-sre.yaml")[0])

    assert verdict.valide
    assert verdict.elagues == []
    assert not verdict.silencieux


def test_lelagage_descend_dans_les_listes():
    verdict = crd.admettre(schemas.AGENT, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "x"},
        "spec": {"type": "Declarative", "declarative": {
            "modelConfig": "m",
            "tools": [{"type": "McpServer", "inconnu": 1,
                       "mcpServer": {"name": "s", "kind": "RemoteMCPServer",
                                     "toolNames": ["a"]}}]}}})

    assert verdict.valide
    assert "spec.declarative.tools[0].inconnu" in verdict.elagues


# ── ce qui est ajoute ────────────────────────────────────────────────────

def test_les_valeurs_par_defaut_sont_ecrites():
    verdict = crd.admettre(schemas.AGENT, {
        "apiVersion": "kagent.dev/v1alpha2", "kind": "Agent",
        "metadata": {"name": "agent-minimal"},
        "spec": {"type": "Declarative",
                 "declarative": {"modelConfig": "claude-config"}}})
    corps = verdict.objet["spec"]["declarative"]

    assert verdict.valide
    assert corps["maxIterations"] == 10
    assert corps["stream"] is False
    assert corps["tools"] == []
    assert verdict.objet["metadata"]["namespace"] == "kagent"


# ── ce que le validateur refuse de faire ─────────────────────────────────

@pytest.mark.parametrize("cle", ["oneOf", "anyOf", "allOf", "$ref"])
def test_un_schema_non_gere_leve(cle: str):
    with pytest.raises(crd.ErreurSchema, match=cle.replace("$", r"\$")):
        crd.valider({"type": "object", cle: []}, {})


def test_une_regle_inconnue_leve():
    with pytest.raises(crd.ErreurSchema, match="regle inconnue"):
        crd.valider({"type": "object", "properties": {},
                     "x-kubernetes-validations": ["regle-imaginaire"]}, {})


def test_un_genre_sans_crd_leve():
    api = controleur.Api()

    with pytest.raises(controleur.ErreurApi, match="genre inconnu"):
        api.appliquer({"kind": "Machin", "metadata": {"name": "x"}})
