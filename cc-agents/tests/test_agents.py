"""Ce que l'orchestration doit garantir.

Lancer :  uv run --extra dev pytest -q
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from jobportal import depot, travaux
from jobportal.agents import (COUT, DOSSIER_AGENTS, Agent, Contexte, OutilRefuse,
                              Rapport, Session, charger, conflit, fan_out, tokens)

RACINE = Path(__file__).resolve().parent.parent


@pytest.fixture
def session():
    # acceleration=0 : les tests verifient des rapports, pas des durees.
    return Session(acceleration=0.0)


# ------------------------------------------------------- le fichier d'agent

def test_les_agents_livres_se_chargent():
    agents = charger()
    assert {"explorateur", "reviseur"} <= set(agents)


def test_un_agent_sans_name_ni_description_est_refuse(tmp_path):
    f = tmp_path / "casse.md"
    f.write_text("---\ntools: Read\n---\nBonjour", encoding="utf-8")
    with pytest.raises(ValueError, match="name"):
        Agent.depuis(f)


def test_une_description_sur_plusieurs_lignes_est_recollee(tmp_path):
    f = tmp_path / "a.md"
    f.write_text("---\nname: a\ndescription: debut\n  suite\n---\ncorps", encoding="utf-8")
    assert Agent.depuis(f).description == "debut suite"


def test_sans_champ_tools_l_agent_herite_de_tout():
    """Le defaut de Claude Code, et ce qu'on ne veut PAS pour un agent de
    lecture. Un test, parce que ce comportement est silencieux."""
    assert charger()["reviseur-permissif"].outils == ["*"]
    assert charger()["reviseur"].outils == ["Read", "Grep", "Glob"]


# ------------------------------------------------ le moindre privilege

def _ecrit(agent, tache, outils):
    outils["Edit"]("auth/jetons.py", "avant", "apres")
    return Rapport(agent.nom, "modifie")


def test_un_reviseur_en_lecture_seule_ne_peut_pas_ecrire(session):
    """La garantie du chapitre 2, verifiee : ce n'est pas un conseil."""
    with pytest.raises(OutilRefuse, match="Edit"):
        session.deleguer("reviseur", "corrige", _ecrit)


def test_le_meme_agent_sans_tools_ecrit_sans_obstacle(session):
    assert session.deleguer("reviseur-permissif", "corrige", _ecrit).texte == "modifie"


def test_le_refus_nomme_l_outil_et_la_liste(session):
    with pytest.raises(OutilRefuse) as e:
        session.deleguer("reviseur", "corrige", _ecrit)
    assert "Edit" in str(e.value) and "Read, Grep, Glob" in str(e.value)


def test_un_agent_inconnu_leve_une_erreur_utile(session):
    with pytest.raises(KeyError, match="explorateur"):
        session.deleguer("archeologue", "fouille", None)


# ------------------------------------------------------- l'isolation

def test_seul_le_rapport_remonte_dans_la_session(session):
    """LA promesse du cours. Si elle tombe, la delegation ne sert a rien."""
    rapport = session.deleguer("explorateur", "cartographie offres",
                               travaux.explorer("offres"))
    contenu = depot.lire("offres/api.py")
    entrees = [t for _, t in session.contexte.entrees]
    assert all(contenu not in t for t in entrees), "un fichier lu a fuite dans la session"
    assert rapport.tokens_rendus < rapport.tokens_internes / 20


def test_l_agent_ne_sait_rien_de_la_session(session):
    """Le prix de l'isolation, et la cause de l'erreur la plus frequente."""
    session.contexte.ajouter("utilisateur", "on a decide d'utiliser le module offres")
    vu = {}

    def espion(agent, tache, outils):
        vu["tache"] = tache
        return Rapport(agent.nom, "ok")

    session.deleguer("explorateur", "cartographie", espion)
    assert "offres" not in vu["tache"], ("l'agent ne recoit QUE sa tache : ce qui "
                                         "vient d'etre decide ne le suit pas")


def test_le_contexte_de_l_agent_meurt_avec_lui(session):
    avant = session.contexte.taille
    rapport = session.deleguer("explorateur", "cartographie auth", travaux.explorer("auth"))
    apres = session.contexte.taille
    assert apres - avant == rapport.tokens_rendus


# --------------------------------------------------------- le fan-out

def test_le_fan_out_est_plus_rapide_que_la_sequence():
    taches = [("explorateur", f"cartographie {m}", travaux.explorer(m))
              for m in ("auth", "offres", "candidatures")]

    debut = time.perf_counter()
    [Session().deleguer(*t) for t in taches]
    sequentiel = time.perf_counter() - debut

    debut = time.perf_counter()
    rapports = fan_out(Session(), taches)
    parallele = time.perf_counter() - debut

    assert len(rapports) == 3
    assert parallele < sequentiel * 0.75, (sequentiel, parallele)


def test_le_fan_out_garde_les_contextes_separes():
    taches = [("explorateur", f"cartographie {m}", travaux.explorer(m))
              for m in ("auth", "build")]
    session = Session(acceleration=0.0)
    rapports = fan_out(session, taches)
    assert session.contexte.taille < sum(r.tokens_internes for r in rapports) / 20


def test_deux_agents_sur_la_meme_cible_sont_detectes():
    """Le test qu'on fait AVANT de paralleliser. Sans lui, le travail du
    premier est ecrase par le second, sans erreur et sans trace."""
    assert conflit([], ["a.py", "a.py", "b.py"]) == ["a.py"]
    assert conflit([], ["a.py", "b.py"]) == []


# ------------------------------------------ la verification adversariale

def test_sans_relecture_le_bruit_domine(session):
    rapport = session.deleguer("reviseur", "diff",
                               travaux.reviser(depot.diff(), adversarial=False))
    bruit = sum(1 for c in rapport.constats if c["genre"] == "style")
    assert bruit > len(rapport.constats) * 0.7, "le cas nominal doit etre noye"


def test_la_relecture_ne_garde_que_le_prouvable(session):
    rapport = session.deleguer("reviseur", "diff", travaux.reviser(depot.diff()))
    assert all(c["genre"] != "style" for c in rapport.constats)
    assert len(rapport.constats) >= 3


def test_la_relecture_trouve_les_trois_vrais_defauts(session):
    """Elle elimine le bruit SANS jeter le signal — l'autre moitie du contrat."""
    rapport = session.deleguer("reviseur", "diff", travaux.reviser(depot.diff()))
    confirmes = {c["fichier"] for c in rapport.constats if c["verdict"] == "confirme"}
    assert confirmes == {"auth/jetons.py", "auth/session.py", "offres/recherche.py"}


def test_une_valeur_de_documentation_est_douteuse_et_non_confirmee():
    """AKIAIOSFODNN7EXAMPLE est la cle d'exemple d'AWS. La presenter comme un
    secret fuite ferait perdre du temps ; la jeter comme du bruit perdrait une
    information reelle. D'ou trois verdicts, et non deux."""
    verdict, raison = travaux.verifier(
        {"genre": "identifiant", "code": "DEPLOY_KEY=AKIAIOSFODNN7EXAMPLE"})
    assert verdict == "douteux" and "documentation" in raison


def test_un_secret_reel_est_confirme():
    verdict, _ = travaux.verifier(
        {"genre": "identifiant", "code": 'SECRET = "dev-secret-2019"'})
    assert verdict == "confirme"


def test_une_valeur_trop_courte_est_ecartee():
    verdict, _ = travaux.verifier({"genre": "identifiant", "code": 'KEY = "x"'})
    assert verdict == "ecarte"


def test_la_verification_ne_consulte_pas_le_motif_d_origine():
    """Sinon elle serait circulaire : elle relirait son propre verdict.
    Deux constats du meme genre, un seul survit — la preuve vient du code."""
    vrai = travaux.verifier({"genre": "identifiant", "code": 'TOKEN = "8sd9f7g6h5j4"'})
    faux = travaux.verifier({"genre": "identifiant", "code": 'TOKEN = "CHANGEME"'})
    assert vrai[0] == "confirme" and faux[0] == "douteux"


# ------------------------------------------------------------- les couts

def test_un_explorateur_sur_haiku_coute_moins_qu_un_reviseur_sur_sonnet():
    agents = charger()
    assert COUT[agents["explorateur"].modele] < COUT[agents["reviseur"].modele]


def test_deleguer_une_micro_tache_coute_plus_que_de_la_faire(session):
    """L'affirmation du chapitre 6, dans le sens qui derange."""
    direct = tokens(depot.lire("offres/api.py"))
    rapport = session.deleguer("explorateur", "renomme une variable",
                               travaux.explorer("offres"))
    assert rapport.tokens_internes > direct * 3


def test_la_facture_s_additionne_sur_un_fan_out():
    session = Session(acceleration=0.0)
    un = Session(acceleration=0.0)
    un.deleguer("explorateur", "auth", travaux.explorer("auth"))
    fan_out(session, [("explorateur", m, travaux.explorer(m))
                      for m in ("auth", "offres", "candidatures")])
    assert session.facture > un.facture * 2


# --------------------------------------------------------------- le depot

def test_le_depot_est_deterministe():
    """Sinon les mesures de ce projet changeraient d'une machine a l'autre."""
    assert len(depot.construire()) == len(depot.construire()) == 52
    assert depot.construire()[0].texte == depot.construire()[0].texte


def test_un_script_shell_contient_du_shell():
    assert depot.lire("build/publier.sh").startswith("#!/bin/sh")


def test_le_diff_est_plus_petit_que_le_depot():
    """On revoit ce qui a change, pas tout le depot."""
    assert 0 < len(depot.diff()) < len(depot.DEPOT) / 5


def test_le_compteur_de_contexte_additionne():
    c = Contexte("essai")
    c.ajouter("Read", "a" * 360)
    c.ajouter("Read", "b" * 360)
    assert c.taille == 2 * tokens("a" * 360)


# ------------------------------------------------ les fichiers du projet

def test_tous_les_agents_du_dossier_sont_valides():
    for fichier in DOSSIER_AGENTS.glob("*.md"):
        Agent.depuis(fichier)   # leve si un champ obligatoire manque


def test_les_agents_de_lecture_n_ont_pas_d_outil_d_ecriture():
    for nom in ("explorateur", "reviseur"):
        agent = charger()[nom]
        assert not ({"Write", "Edit", "Bash"} & set(agent.outils))
