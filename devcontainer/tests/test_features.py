"""L'algorithme d'ordre — (B1), (B2), (B3), sur les vrais manifestes."""

from __future__ import annotations

import pytest

from jobportal import features
from jobportal.commun import A_CORRIGER, PORTAIL
from jobportal.config import charger

G = "ghcr.io/devcontainers/features/"
INDEX = features.catalogue()


def ordre(demandees, impose=None):
    resultat, _ = features.resoudre(demandees, impose or [], INDEX)
    return [str(f) for f in resultat]


def noms(demandees, impose=None):
    resultat, _ = features.resoudre(demandees, impose or [], INDEX)
    return [f.qualifie.rsplit("/", 1)[-1] for f in resultat]


# ── identifiants ────────────────────────────────────────────────────────

@pytest.mark.parametrize("identifiant, qualifie, tag", [
    (f"{G}node:1", f"{G}node", "1"),
    (f"{G}node", f"{G}node", "latest"),
    (f"{G}node:latest", f"{G}node", "latest"),
    (f"{G}node@sha256:abc", f"{G}node", "sha256:abc"),
    ("./ma-feature", "./ma-feature", "latest"),
    ("localhost:5000/moi/f:2", "localhost:5000/moi/f", "2"),
])
def test_nom_qualifie_et_etiquette(identifiant, qualifie, tag):
    assert features.nom_qualifie(identifiant) == qualifie
    assert features.etiquette(identifiant) == tag


def test_une_feature_locale_est_reconnue():
    assert features.Feature("./ma-feature").locale is True
    assert features.Feature(f"{G}node:1").locale is False


def test_deux_features_locales_ne_sont_jamais_egales():
    """« For local Features, each Feature is considered unique. »"""
    a, b = features.Feature("./f"), features.Feature("./f")
    assert a.cle() != b.cle()
    assert len(features.construire({"./f": {}}, INDEX)) == 1


# ── (B1) le graphe ──────────────────────────────────────────────────────

def test_dependson_est_dur_et_recursif():
    """Deux demandees, trois installees : terraform tire github-cli."""
    resultat = features.construire({f"{G}terraform:1": {}}, INDEX)
    assert len(resultat) == 2
    assert {f.qualifie.rsplit("/", 1)[-1] for f in resultat} == {
        "terraform", "github-cli"}
    assert [f.demandee for f in resultat] == [True, False]


def test_installsafter_ne_tire_rien():
    """« installsAfter is not recursive. »"""
    resultat = features.construire({f"{G}python:1": {}}, INDEX)
    assert len(resultat) == 1


def test_une_arete_molle_vers_une_absente_est_retiree():
    """python installsAfter oryx — mais oryx n'est pas demande."""
    assert noms({f"{G}python:1": {}}) == ["python"]


def test_la_meme_arete_compte_si_la_cible_est_la():
    assert noms({f"{G}python:1": {}, f"{G}oryx:1": {}, f"{G}dotnet:1": {}}) \
        == ["dotnet", "oryx", "python"]


# ── (B2) roundPriority ──────────────────────────────────────────────────

def test_la_priorite_vaut_n_moins_l_index():
    liste = features.construire(
        {f"{G}node:1": {}, f"{G}git:1": {}, f"{G}go:1": {}}, INDEX)
    features.prioriser(liste, [f"{G}node", f"{G}git"])
    priorites = {f.qualifie.rsplit("/", 1)[-1]: f.priorite for f in liste}
    assert priorites == {"node": 2, "git": 1, "go": 0}


def test_une_feature_hors_liste_garde_zero():
    liste = features.construire({f"{G}go:1": {}}, INDEX)
    features.prioriser(liste, [f"{G}node"])
    assert liste[0].priorite == 0


def test_l_ordre_impose_s_ecrit_sans_version():
    """« l'identifiant s'ecrit sans la version »."""
    liste = features.construire({f"{G}node:1": {}}, INDEX)
    features.prioriser(liste, [f"{G}node"])
    assert liste[0].priorite == 1


# ── (B3) le tri par tours ───────────────────────────────────────────────

def test_la_priorite_n_agit_qu_a_l_interieur_d_un_tour():
    base = {f"{G}github-cli:1": {}, f"{G}git:1": {},
            f"{G}node:1": {}, f"{G}common-utils:2": {}}
    sans = noms(base)
    avec_node = noms(base, [f"{G}node"])
    avec_gh = noms(base, [f"{G}github-cli"])
    assert sans == ["common-utils", "git", "node", "github-cli"]
    assert avec_node == ["common-utils", "node", "git", "github-cli"]
    # github-cli ne peut PAS passer devant git : il l'installsAfter.
    assert avec_gh == sans


def test_le_tri_stable_est_alphabetique_a_priorite_egale():
    resultat = noms({f"{G}rust:1": {}, f"{G}go:1": {}, f"{G}php:1": {}})
    assert resultat == sorted(resultat)


def test_le_journal_dit_le_tour_de_chacune():
    _, journal = features.resoudre(
        {f"{G}python:1": {}, f"{G}oryx:1": {}, f"{G}dotnet:1": {}}, [], INDEX)
    assert [t.numero for t in journal] == [1, 2, 3]
    assert [len(t.retenues) for t in journal] == [1, 1, 1]


def test_un_cycle_est_une_erreur():
    faux = {
        "a/x": {"id": "x", "installsAfter": ["a/y"]},
        "a/y": {"id": "y", "installsAfter": ["a/x"]},
    }
    with pytest.raises(features.CycleDeDependances):
        features.resoudre({"a/x:1": {}, "a/y:1": {}}, [], faux)


# ── egalite et doublons ─────────────────────────────────────────────────

def test_deux_jeux_d_options_donnent_deux_features():
    """« the options executed against the Feature are equal »."""
    resultat = noms({f"{G}terraform:1": {}, f"{G}github-cli:1": {}})
    assert resultat.count("github-cli") == 2


def test_la_meme_option_ne_donne_qu_une_feature():
    resultat = noms({f"{G}terraform:1": {},
                     f"{G}github-cli:1": {"version": "latest"}})
    assert resultat.count("github-cli") == 1


# ── sur les fichiers du projet ──────────────────────────────────────────

def test_le_portail_s_ordonne_en_deux_tours():
    portail = charger(PORTAIL / "devcontainer.json")
    resultat, journal = features.resoudre(portail.features,
                                          portail.ordre_impose, INDEX)
    assert [f.qualifie.rsplit("/", 1)[-1] for f in resultat] == [
        "common-utils", "docker-in-docker", "github-cli", "java"]
    assert len(journal) == 2
    assert len(journal[0].retenues) == 1


def test_l_ordre_impose_impossible_ne_change_rien():
    impossible = charger(A_CORRIGER / "11-ordre-impossible.json")
    avec = noms(impossible.features, impossible.ordre_impose)
    sans = noms(impossible.features)
    assert avec == sans
    assert avec[-1] == "terraform"
