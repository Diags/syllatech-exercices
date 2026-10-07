"""Ce que le verificateur doit attraper, et ce qu'il ne doit pas signaler.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))
sys.path.insert(0, str(RACINE / ".claude" / "skills" / "migration" / "scripts"))

import pytest

from verifier import frontmatter, verifier, verifier_une
from verifier_migration import verifier as verifier_migration


def soucis_de(racine: Path) -> list:
    return verifier(racine)


# ------------------------------------------------- les skills du projet

def test_les_skills_livrees_sont_propres():
    """Si ce test tombe, le projet enseigne ce qu'il denonce."""
    assert soucis_de(RACINE) == [], [s.message for s in soucis_de(RACINE)]


@pytest.mark.parametrize("nom", ["rapport-hebdo", "migration", "captures"])
def test_chaque_skill_a_une_description_qui_dit_QUAND(nom):
    champs, _ = frontmatter((RACINE / ".claude" / "skills" / nom / "SKILL.md")
                            .read_text(encoding="utf-8"))
    d = champs["description"]
    assert len(d) > 60, "une description courte ne declenche jamais la skill"
    assert any(m in d.lower() for m in ("quand", "utiliser", "avant"))


# ------------------------------------------- les skills a corriger

@pytest.fixture(scope="module")
def casse():
    return {(s.skill, s.gravite): s.message for s in soucis_de(RACINE / "skills-a-corriger")}


def test_le_chemin_relatif_du_cours_est_attrape(casse):
    """LE defaut du chapitre 3 : « node scripts/captures.js » est resolu
    depuis le dossier de TRAVAIL, pas depuis la skill. Le script est
    introuvable, et on ne l'apprend qu'a l'execution."""
    msg = casse[("capture-ecrans", "erreur")]
    assert "CLAUDE_SKILL_DIR" in msg


def test_une_description_absente_est_une_erreur(casse):
    assert "description" in casse[("deploie", "erreur")]


def test_une_faute_de_frappe_dans_un_champ_est_signalee():
    """« descriptio » au lieu de « description » : le champ est ignore en
    silence, et la skill ne se declenche jamais. Rien ne le dit.

    Le message doit citer « champ inconnu » : se contenter de chercher
    « descriptio » ferait passer ce test sans rien verifier, puisque c'est
    aussi un prefixe de « description », present dans un autre message.
    """
    messages = [s.message for s in soucis_de(RACINE / "skills-a-corriger")
                if s.skill == "deploie"]
    assert any("champ inconnu" in m and "descriptio »" in m for m in messages), messages


def test_un_nom_different_du_dossier_est_signale():
    messages = [s.message for s in soucis_de(RACINE / "skills-a-corriger")
                if s.skill == "deploie"]
    assert any("/deploie" in m for m in messages)


def test_des_arguments_sans_indice_sont_signales():
    messages = [s.message for s in soucis_de(RACINE / "skills-a-corriger")
                if s.skill == "release"]
    assert any("argument-hint" in m for m in messages)


# ------------------------------------------------------- le frontmatter

def test_le_frontmatter_lit_une_valeur_sur_plusieurs_lignes():
    champs, corps = frontmatter("---\nname: x\ndescription: debut\n  suite\n---\ncorps\n")
    assert champs["description"] == "debut suite"
    assert corps.strip() == "corps"


def test_un_fichier_sans_frontmatter_ne_casse_pas():
    champs, corps = frontmatter("juste du texte")
    assert champs == {} and corps == "juste du texte"


# ------------------------------------------ le script de la skill migration

def test_une_migration_sans_down_est_refusee():
    soucis = verifier_migration("-- up\nALTER TABLE offres ADD COLUMN salaire int;\n")
    assert any("down" in s for s in soucis)


def test_une_migration_complete_est_acceptee():
    assert verifier_migration("-- up\nALTER TABLE t ADD COLUMN c int;\n"
                              "-- down\nALTER TABLE t DROP COLUMN c;\n") == []


def test_un_drop_table_sans_recreation_est_refuse():
    soucis = verifier_migration("-- up\nDROP TABLE offres;\n-- down\n-- rien\n")
    assert any("DROP TABLE" in s for s in soucis)


# ------------------------------------------------- le script de captures

def test_le_script_de_captures_signale_les_echecs():
    script = RACINE / ".claude" / "skills" / "captures" / "scripts" / "captures.py"
    r = subprocess.run([sys.executable, str(script)], capture_output=True,
                       text=True, encoding="utf-8")
    assert r.returncode == 1, "un echec doit se voir dans le code de sortie"
    assert "admin" in r.stdout


# ------------------------------------------------------- le harnais de rendu

from rendre import executer_commandes, tokens  # noqa: E402


def rendu_de(nom: str, arguments: str = "") -> str:
    r = subprocess.run([sys.executable, str(RACINE / "outils" / "rendre.py"), nom, arguments],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_une_commande_injectee_est_executee_et_remplacee():
    """Le point que la video ne montre pas : la commande tourne sur la
    machine AVANT que le modele ne lise quoi que ce soit, et sa sortie est
    collee telle quelle dans le prompt."""
    corps, mesures = executer_commandes("avant !`echo bonjour` apres", RACINE)
    assert corps == "avant bonjour apres"
    assert mesures and mesures[0][0] == "echo bonjour"


def test_l_entree_standard_est_fermee_au_rendu():
    """Une commande qui LIT stdin rend du vide, et ne signale rien. C'est le
    piege de « git shortlog » sans revision — d'ou le HEAD explicite dans la
    skill rapport-hebdo."""
    corps, _ = executer_commandes("[!`cat`]", RACINE)
    assert corps == "[]"


def test_une_commande_qui_echoue_ne_casse_pas_le_rendu():
    corps, _ = executer_commandes("!`commande-qui-nexiste-pas-du-tout`", RACINE)
    assert corps.strip() != "", "un echec doit laisser une trace, pas du vide"


def test_les_arguments_sont_substitues():
    assert "semaine-2025-S37.md" in rendu_de("rapport-hebdo", "2025-S37")


def test_la_variable_de_dossier_est_resolue_vers_un_chemin_reel():
    sortie = rendu_de("captures")
    ligne = [l for l in sortie.splitlines() if "captures.py" in l and "python" in l][0]
    chemin = Path(ligne.split("python", 1)[1].strip().split()[0])
    assert chemin.exists(), f"{chemin} devrait exister : c'est tout l'interet de la variable"


def test_l_index_ne_contient_que_le_frontmatter():
    """La promesse du chapitre 1, verifiee : le corps n'est PAS charge."""
    r = subprocess.run([sys.executable, str(RACINE / "outils" / "rendre.py"), "--index"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    index = r.stdout
    for nom in ("rapport-hebdo", "migration", "captures"):
        champs, corps = frontmatter((RACINE / ".claude" / "skills" / nom / "SKILL.md")
                                    .read_text(encoding="utf-8"))
        assert champs["name"] in index
        for ligne in (l.strip() for l in corps.splitlines()):
            if len(ligne) > 40 and not ligne.startswith(("!`", "#", ">")):
                assert ligne not in index, f"« {ligne[:40]}… » ne devrait pas etre charge"


def test_le_rendu_pese_plus_que_le_fichier_ecrit():
    """Ce que vous relisez n'est pas ce que le modele lit."""
    champs, corps = frontmatter((RACINE / ".claude" / "skills" / "rapport-hebdo" / "SKILL.md")
                                .read_text(encoding="utf-8"))
    rendu, _ = executer_commandes(corps, RACINE)
    assert tokens(rendu) > 2 * tokens(corps), (tokens(corps), tokens(rendu))
