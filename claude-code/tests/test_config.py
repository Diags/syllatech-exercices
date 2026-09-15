"""Ce que la configuration d'un projet Claude Code doit garantir.

Lancer :  uv run --extra dev pytest -q

La moitie de ces tests verifie qu'un defaut SILENCIEUX est bien attrape. Une
configuration dont on croit qu'elle protege plus qu'elle ne protege est pire
qu'une configuration absente.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from outils.verifier_config import (EVENEMENTS, OUTILS_CONNUS, _frontmatter,
                                    verifier, verifier_agents,
                                    verifier_claude_md, verifier_hooks,
                                    verifier_mcp, verifier_skills)

RACINE = Path(__file__).resolve().parent.parent
POURRIE = RACINE / "config-pourrie"


def messages(soucis) -> str:
    return "\n".join(f"{s.ou} : {s.message}" for s in soucis)


# --------------------------------------------- la configuration livree

def test_la_configuration_livree_est_coherente():
    """Si ce test tombe, le projet enseigne ce qu'il denonce."""
    assert verifier(RACINE) == [], messages(verifier(RACINE))


def test_la_configuration_pourrie_ne_l_est_pas():
    erreurs = [s for s in verifier(POURRIE) if s.gravite == "erreur"]
    assert len(erreurs) >= 7, messages(erreurs)


# --------------------------------------------------------- les hooks

def test_un_evenement_mal_orthographie_est_une_erreur():
    """« PreToolUsage » est accepte par Claude Code, enregistre, et ne se
    declenche JAMAIS. Aucune erreur, aucun avertissement."""
    casse = {"hooks": {"PreToolUsage": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "echo x"}]}]}}
    soucis = verifier_hooks(RACINE, casse)
    assert any("JAMAIS" in s.message for s in soucis), messages(soucis)


@pytest.mark.parametrize("evenement", sorted(EVENEMENTS))
def test_les_evenements_valides_passent(evenement):
    casse = {"hooks": {evenement: [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "echo x"}]}]}}
    assert not any("evenement inconnu" in s.message
                   for s in verifier_hooks(RACINE, casse))


def test_un_script_de_hook_disparu_est_attrape():
    """Le defaut le plus courant d'un .claude/ ancien : le hook survit au
    script, et l'echec d'un hook ne remonte pas toujours."""
    casse = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python .claude/hooks/parti.py"}]}]}}
    soucis = verifier_hooks(RACINE, casse)
    assert any("n'existe pas" in s.message for s in soucis)


def test_la_variable_de_projet_est_acceptee():
    """$CLAUDE_PROJECT_DIR est la bonne forme : un hook ne s'execute pas
    forcement depuis la racine."""
    bon = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command",
         "command": "python $CLAUDE_PROJECT_DIR/.claude/hooks/formate.py"}]}]}}
    assert verifier_hooks(RACINE, bon) == []


def test_un_matcher_inconnu_est_un_avertissement_pas_une_erreur():
    """OUTILS_CONNUS est un instantane. Un vérificateur qui crie faux finit
    desactive, et il emporte les controles justes avec lui."""
    casse = {"hooks": {"PreToolUse": [{"matcher": "OutilFutur", "hooks": []}]}}
    soucis = verifier_hooks(RACINE, casse)
    assert soucis and all(s.gravite == "attention" for s in soucis)


# ------------------------------------------------------ les sous-agents

def test_un_agent_sans_description_est_une_erreur():
    soucis = verifier_agents(POURRIE)
    assert not any("description" in s.message and s.gravite == "erreur"
                   for s in soucis), "celui-ci en a une"


def test_un_outil_inconnu_dans_tools_est_signale():
    """Un outil dont le nom a change reste dans le « tools: ». Il est
    simplement ignore : l'agent ne l'a pas, et rien ne le dit."""
    soucis = verifier_agents(POURRIE)
    assert any("FileSearch" in s.message for s in soucis), messages(soucis)


def test_l_agent_livre_est_en_lecture_seule():
    """Un reviseur qui peut ecrire reecrit le code qu'il juge."""
    champs, _ = _frontmatter(
        (RACINE / ".claude" / "agents" / "reviseur.md").read_text(encoding="utf-8"))
    outils = {o.strip() for o in champs["tools"].split(",")}
    assert outils == {"Read", "Grep", "Glob"}
    assert not ({"Write", "Edit", "Bash"} & outils)


# ---------------------------------------------------------- les skills

def test_une_skill_sans_description_est_une_erreur():
    soucis = verifier_skills(POURRIE)
    assert any("jamais toute seule" in s.message for s in soucis)


def test_un_chemin_de_script_relatif_est_une_erreur():
    """Resolu depuis le dossier de TRAVAIL, pas depuis la skill. On ne
    l'apprend qu'a l'instant ou la skill s'execute."""
    soucis = verifier_skills(POURRIE)
    assert any("CLAUDE_SKILL_DIR" in s.message for s in soucis)


def test_un_script_de_skill_reference_doit_exister():
    assert verifier_skills(RACINE) == [], messages(verifier_skills(RACINE))
    chemin = (RACINE / ".claude" / "skills" / "changelog" / "scripts"
              / "verifier_changelog.py")
    assert chemin.exists()


def test_le_script_de_la_skill_fonctionne():
    import sys
    sys.path.insert(0, str(RACINE / ".claude" / "skills" / "changelog" / "scripts"))
    from verifier_changelog import verifier as verifier_changelog

    assert verifier_changelog("## [Unreleased]\n\n### Ajoute\n- x\n") == []
    assert verifier_changelog("### Ajoute\n- x\n")          # pas d'Unreleased
    assert verifier_changelog("## [Unreleased]\n### Bidule\n")   # rubrique inconnue


# -------------------------------------------------------------- MCP

def test_un_secret_en_clair_est_une_erreur():
    soucis = verifier_mcp(POURRIE, {})
    assert any("secret en clair" in s.message for s in soucis)


def test_une_variable_n_est_pas_prise_pour_un_secret():
    """Sinon le vérificateur refuserait la BONNE forme."""
    assert not any("secret en clair" in s.message
                   for s in verifier_mcp(RACINE, {}))


def test_une_regle_qui_nomme_un_serveur_absent_est_une_erreur():
    """Elle est acceptee, elle a l'air de proteger, et elle ne protege rien."""
    casse = {"permissions": {"deny": ["mcp__analytics__export"]}}
    soucis = verifier_mcp(RACINE, casse)
    assert any("n'est pas dans .mcp.json" in s.message for s in soucis)


def test_une_regle_sur_un_serveur_present_passe():
    bon = {"permissions": {"deny": ["mcp__db__execute"]}}
    assert verifier_mcp(RACINE, bon) == []


def test_la_version_du_serveur_est_epinglee():
    """La description d'un outil MCP est du texte que le modele lit : une
    montee de version silencieuse change ce que l'agent croit devoir faire."""
    config = json.loads((RACINE / ".mcp.json").read_text(encoding="utf-8"))
    args = config["mcpServers"]["db"]["args"]
    assert any("@" in a and a.count(".") >= 2 for a in args), args


# --------------------------------------------------------- CLAUDE.md

def test_une_commande_npm_inexistante_est_une_erreur():
    """CLAUDE.md est relu a CHAQUE session : une commande fausse y est
    repetee a l'agent des centaines de fois."""
    soucis = verifier_claude_md(POURRIE)
    assert any("npm run check" in s.message for s in soucis)


def test_un_sous_agent_documente_mais_absent_est_une_erreur():
    soucis = verifier_claude_md(POURRIE)
    assert any("explorateur" in s.message for s in soucis)


def test_un_serveur_mcp_documente_mais_absent_est_une_erreur():
    casse = POURRIE
    # « github » EST dans le .mcp.json pourri : on verifie donc l'inverse.
    assert not any("github" in s.message and "absent de .mcp.json" in s.message
                   for s in verifier_claude_md(casse))


def test_le_claude_md_livre_ne_ment_pas():
    assert verifier_claude_md(RACINE) == [], messages(verifier_claude_md(RACINE))


def test_toutes_les_commandes_du_claude_md_existent():
    texte = (RACINE / "CLAUDE.md").read_text(encoding="utf-8")
    scripts = set(json.loads(
        (RACINE / "package.json").read_text(encoding="utf-8"))["scripts"])
    import re
    for m in re.finditer(r"npm run ([\w:-]+)", texte):
        assert m.group(1) in scripts, m.group(1)


# ------------------------------------------------------- le vérificateur

def test_le_verificateur_rend_1_quand_il_reste_une_erreur():
    import subprocess
    import sys
    r = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "verifier_config.py"),
         str(POURRIE), "--ci"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 1

    r = subprocess.run(
        [sys.executable, str(RACINE / "outils" / "verifier_config.py"),
         str(RACINE), "--ci"],
        capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stdout
