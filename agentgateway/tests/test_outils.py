"""Les deux outils, appelés comme en ligne de commande.

Un outil dont le code de sortie ment ne sert à rien en CI : c'est ce que
ces tests fixent.
"""

from __future__ import annotations

from pathlib import Path

from jobportal.commun import CONFIGS, EXEMPLES_AMONT, PORTAIL
from outils import essayer_route, verifier_config

DU_COURS = CONFIGS / "du-cours"


def fichiers(dossier: Path) -> list[str]:
    return [str(p) for p in sorted(dossier.glob("*.yaml"))]


def test_le_portail_passe(capsys):
    assert verifier_config.principal(fichiers(PORTAIL)) == 0
    sortie = capsys.readouterr().out
    assert sortie.count("le schema publie accepte cette configuration") == 3
    assert "⚠" not in sortie


def test_les_exemples_amont_passent(capsys):
    assert verifier_config.principal(fichiers(EXEMPLES_AMONT)) == 0
    capsys.readouterr()


def test_quatre_configurations_du_support_sur_cinq_sont_refusees(capsys):
    assert verifier_config.principal(fichiers(DU_COURS)) == 4
    sortie = capsys.readouterr().out
    assert "4 fichier(s) refuse(s) sur 5" in sortie


def test_les_avertissements_ne_sont_pas_des_refus(capsys):
    """Le chapitre 1 du support est VALIDE, et sa route attrape tout."""
    code = verifier_config.principal([str(DU_COURS / "ch1-mcp-minimal.yaml")])
    sortie = capsys.readouterr().out
    assert code == 0
    assert "n'ecrit aucun `matches`" in sortie
    assert "REFUS" not in sortie


def test_l_avertissement_sur_le_mode_jwt(capsys):
    verifier_config.principal([str(DU_COURS / "ch5-securite.yaml")])
    assert "le defaut est `optional`" in capsys.readouterr().out


def test_le_mode_brut_montre_la_cascade(capsys):
    """Un backend mal ecrit echoue contre les dix branches du `oneOf` : le
    mode brut le montre, le resume le ramene a ce qui se lit.
    """
    from jobportal import schema_publie
    from jobportal.config import charger
    config = charger(DU_COURS / "ch4-a2a-et-inference.yaml")
    brutes = schema_publie.verifier(config, resumer=False)
    resumees = schema_publie.verifier(config)
    # Deux backends fautifs, et le validateur remonte pour chacun le refus
    # de l'union PUIS celui de la definition qui l'englobe.
    assert len(brutes) == 4
    assert len(resumees) > len(brutes)
    assert sum("Unevaluated properties" in m for _, m in brutes) == 2
    # Le resume, lui, nomme le champ fautif — ce que le brut ne fait pas.
    assert any("'selfHosted' was unexpected" in m for _, m in resumees)
    assert not any("'selfHosted' was unexpected" in m for _, m in brutes)
    capsys.readouterr()


def test_le_mode_muet(capsys):
    verifier_config.principal(fichiers(DU_COURS) + ["--muet"])
    assert capsys.readouterr().out.strip() == "4 fichier(s) refuse(s) sur 5"


# ── essayer_route ───────────────────────────────────────────────────────

def test_une_seule_route_correspond(capsys):
    code = essayer_route.principal([str(PORTAIL / "01-mcp.yaml"), "/mcp/tools"])
    assert code == 0
    assert "Une seule route correspond" in capsys.readouterr().out


def test_aucune_route_ne_correspond(capsys):
    code = essayer_route.principal([str(PORTAIL / "01-mcp.yaml"), "/v1/chat"])
    assert code == 1
    assert "Aucune route ne correspond" in capsys.readouterr().out


def test_la_route_fourre_tout_est_marquee(capsys):
    code = essayer_route.principal(
        [str(DU_COURS / "ch1-mcp-minimal.yaml"), "/admin/tout-casser"])
    sortie = capsys.readouterr().out
    assert code == 0
    assert "PREND" in sortie
    assert "n'ecrit aucun `matches`" in sortie


def test_les_entetes_et_la_methode(capsys):
    import tempfile
    texte = """
binds:
- port: 3000
  listeners:
  - routes:
    - name: rh-seulement
      matches:
      - path: {pathPrefix: /v1}
        method: {method: POST}
        headers:
        - name: x-equipe
          value: {exact: rh}
      backends: [{host: x:80}]
"""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False,
                                     encoding="utf-8") as f:
        f.write(texte)
        chemin = f.name
    try:
        assert essayer_route.principal(
            [chemin, "/v1/chat", "--methode", "POST",
             "--entete", "x-equipe: rh"]) == 0
        capsys.readouterr()
        assert essayer_route.principal(
            [chemin, "/v1/chat", "--methode", "POST",
             "--entete", "x-equipe: data"]) == 1
        capsys.readouterr()
    finally:
        Path(chemin).unlink()
