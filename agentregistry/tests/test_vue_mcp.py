"""La fiche publiee : trois cascades, et ce qu'elles ne disent pas."""

from __future__ import annotations

import pytest

from jobportal import vue_mcp
from jobportal.commun import CATALOGUE
from jobportal.manifeste import Document, charger

PORTAIL = CATALOGUE / "portail"


def serveur(spec: dict, meta: dict | None = None) -> Document:
    return Document({"apiVersion": "ar.dev/v1alpha1", "kind": "MCPServer",
                     "metadata": meta or {"name": "offres"}, "spec": spec})


# ── l'identifiant OCI ───────────────────────────────────────────────────

@pytest.mark.parametrize("identifiant, attendu", [
    ("ghcr.io/portail/mcp:1.4.0", "1.4.0"),
    ("ghcr.io/portail/mcp@sha256:abc123", "sha256:abc123"),
    ("ghcr.io/portail/mcp", ""),
    ("localhost:5001/acme/fetch:1.0.0", "1.0.0"),
    # Le port du registre n'est PAS une version : le « : » n'est cherche que
    # dans le dernier segment.
    ("ghcr.io:443/portail/mcp", ""),
    ("ghcr.io:443/portail/mcp:2.0", "2.0"),
    ("mcp:3.1", "3.1"),
])
def test_version_depuis_l_identifiant_oci(identifiant, attendu):
    assert vue_mcp.version_depuis_identifiant_oci(identifiant) == attendu


def test_le_digest_gagne_sur_le_tag():
    assert vue_mcp.version_depuis_identifiant_oci(
        "ghcr.io/x/y:1.0.0@sha256:deadbeef") == "sha256:deadbeef"


# ── la cascade de version ───────────────────────────────────────────────

def test_version_depuis_le_paquet_oci():
    doc = serveur({"source": {"package": {
        "origin": {"type": "oci", "identifier": "ghcr.io/x/y:1.4.0",
                   "oci": {"serverName": "io.x/y"}},
        "transport": {"type": "stdio"}}}},
        {"name": "offres", "tag": "stable"})
    assert vue_mcp.version(doc) == ("1.4.0", "paquet")


def test_version_depuis_le_paquet_pypi():
    doc = serveur({"source": {"package": {
        "origin": {"type": "pypi", "identifier": "p",
                   "pypi": {"version": "0.6.2", "serverName": "io.x/y"}},
        "transport": {"type": "stdio"}}}},
        {"name": "s", "tag": "stable"})
    assert vue_mcp.version(doc) == ("0.6.2", "paquet")


def test_version_depuis_l_etiquette_quand_il_n_y_a_pas_de_paquet():
    """Un serveur REMOTE n'a pas de paquet : sa version publiee est son
    etiquette. « stable » devient donc un numero de version.
    """
    doc = serveur({"remote": {"type": "streamable-http",
                              "url": "https://x.test/mcp"}},
                  {"name": "annuaire", "tag": "stable"})
    assert vue_mcp.version(doc) == ("stable", "etiquette")


def test_version_de_repli():
    """Une image sans tag et une etiquette « latest » : plus rien a deriver."""
    doc = serveur({"source": {"package": {
        "origin": {"type": "oci", "identifier": "ghcr.io/x/y",
                   "oci": {"serverName": "io.x/y"}},
        "transport": {"type": "stdio"}}}},
        {"name": "offres", "tag": "latest"})
    assert vue_mcp.version(doc) == ("0.0.0", "repli")


def test_l_etiquette_latest_ne_sert_pas_de_version():
    """« fall back to a non-"latest" tag » : latest est explicitement exclu."""
    doc = serveur({"remote": {"type": "sse", "url": "https://x.test/mcp"}},
                  {"name": "a", "tag": "latest"})
    assert vue_mcp.version(doc) == ("0.0.0", "repli")


def test_un_remote_sans_etiquette_publie_zero():
    doc = serveur({"remote": {"type": "sse", "url": "https://x.test/mcp"}},
                  {"name": "a"})
    assert vue_mcp.version(doc) == ("0.0.0", "repli")


# ── la cascade de description ───────────────────────────────────────────

def test_description_du_manifeste():
    doc = serveur({"description": "Les offres", "title": "Offres"})
    assert vue_mcp.description(doc) == ("Les offres", "manifeste")


def test_description_repliee_sur_le_titre():
    doc = serveur({"title": "Offres"})
    assert vue_mcp.description(doc) == ("Offres", "titre")


def test_description_generee():
    doc = serveur({}, {"name": "offres"})
    assert vue_mcp.description(doc) == ("MCP server offres", "genere")


# ── le nom de catalogue ─────────────────────────────────────────────────

@pytest.mark.parametrize("espace, nom, attendu", [
    ("default", "offres", "default/offres"),
    ("", "offres", "default/offres"),
    ("rh", "offres", "rh/offres"),
])
def test_nom_de_catalogue(espace, nom, attendu):
    assert vue_mcp.nom_de_catalogue(espace, nom) == attendu


def test_est_la_derniere():
    assert vue_mcp.est_la_derniere(serveur({}, {"name": "a"}))
    assert vue_mcp.est_la_derniere(serveur({}, {"name": "a", "tag": "latest"}))
    assert not vue_mcp.est_la_derniere(
        serveur({}, {"name": "a", "tag": "stable"}))


# ── sur le vrai catalogue ───────────────────────────────────────────────

def test_les_trois_serveurs_du_portail_publient_une_vraie_version():
    attendu = {
        "default/offres": ("1.4.0", "paquet"),
        "default/scoring-cv": ("0.6.2", "paquet"),
        # Un remote n'a pas de paquet : son etiquette fait office de version.
        "default/annuaire-pro": ("stable", "etiquette"),
    }
    for chemin in sorted(PORTAIL.glob("mcp-*.yaml")):
        doc = next(iter(charger(chemin)))
        f = vue_mcp.fiche(doc)
        assert (f["version"], f["_origine"]["version"]) == attendu[f["name"]]


def test_cinq_serveurs_d_a_corriger_publient_un_repli():
    documents = [d for d in charger(CATALOGUE / "a-corriger.yaml")
                 if d.type == "MCPServer"]
    assert len(documents) == 6
    replis = [vue_mcp.fiche(d) for d in documents]
    assert sum(1 for f in replis
               if f["_origine"]["version"] == "repli"
               or f["_origine"]["description"] == "genere") == 5


def test_la_fiche_ne_distingue_pas_une_version_derivee_d_un_repli():
    """Le point du chapitre 6 : « 1.4.0 » et « 0.0.0 » sont deux chaines dans
    le meme champ. Rien dans la fiche PUBLIEE ne dit laquelle est un aveu.
    """
    vraie = vue_mcp.fiche(next(iter(charger(PORTAIL / "mcp-offres.yaml"))))
    fausse = vue_mcp.fiche([d for d in charger(CATALOGUE / "a-corriger.yaml")
                            if d.nom == "sans-version"][0])
    vraie.pop("_origine")
    fausse.pop("_origine")
    assert set(vraie) == set(fausse)
    assert isinstance(vraie["version"], str) and isinstance(fausse["version"], str)
