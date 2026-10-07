"""La commande derivee, et le piege de `launch`."""

from __future__ import annotations

import pytest

from jobportal import lancement


def paquet(type_: str, identifiant: str, **sous) -> dict:
    origine = {"type": type_, "identifier": identifiant}
    if type_ in ("npm", "pypi"):
        origine[type_] = {"version": sous.get("version", "1.0.0"),
                          "serverName": "io.x/y"}
    if type_ == "oci":
        origine["oci"] = {"serverName": "io.x/y"}
    return {"origin": origine, "transport": {"type": "stdio"}}


@pytest.mark.parametrize("type_, identifiant, attendu", [
    ("npm", "@portail/mcp", "npx -y @portail/mcp@1.0.0"),
    ("pypi", "portail-mcp", "uvx portail-mcp==1.0.0"),
    ("oci", "ghcr.io/p/o:1", "(ENTRYPOINT de ghcr.io/p/o:1)"),
])
def test_commande_derivee(type_, identifiant, attendu):
    assert lancement.derivee(paquet(type_, identifiant)) == (
        attendu, "image" if type_ == "oci" else "derivee")


def test_launch_reprend_la_main_completement():
    """« If Launch is set, the manifest owns Command and Args verbatim — no
    implicit identifier injection. » L'identifiant disparait.
    """
    p = paquet("npm", "@portail/mcp")
    p["launch"] = {"command": "npx",
                   "args": [{"type": "named", "name": "--cache",
                             "value": "/tmp/npm"}]}
    commande, origine = lancement.effective(p)
    assert origine == "launch"
    assert "@portail/mcp" not in commande
    assert commande == "npx --cache /tmp/npm"


def test_launch_avec_argument_positionnel():
    p = paquet("pypi", "portail-mcp")
    p["launch"] = {"command": "portail-serveur",
                   "args": [{"type": "positional",
                             "value": "--config=/etc/s.json"}]}
    assert lancement.effective(p)[0] == "portail-serveur --config=/etc/s.json"


def test_commande_vide_n_est_permise_que_pour_oci():
    """« Command may be empty only for oci » : sur une image, un launch sans
    commande retombe sur l'ENTRYPOINT.
    """
    oci = paquet("oci", "ghcr.io/p/o:1")
    oci["launch"] = {"env": [{"name": "TOKEN", "isRequired": True}]}
    commande, origine = lancement.effective(oci)
    assert origine == "image"
    assert "ENTRYPOINT" in commande


def test_variables_requises():
    p = paquet("oci", "ghcr.io/p/o:1")
    p["launch"] = {"env": [
        {"name": "API_KEY", "isRequired": True},
        {"name": "LOG_LEVEL", "value": "info"},
        {"name": "BASE_URL", "isRequired": True},
    ]}
    assert lancement.variables_requises(p) == ["API_KEY", "BASE_URL"]


def test_aucune_variable_sans_launch():
    assert lancement.variables_requises(paquet("npm", "@x/y")) == []


def test_origine_inconnue_ne_leve_pas():
    """Un manifeste refuse par le validateur passe quand meme ici : les
    chapitres l'affichent, et un chapitre qui plante n'enseigne rien.
    """
    commande, origine = lancement.derivee(
        {"origin": {"type": "uvx", "identifier": "x"}})
    assert commande == ""
    assert "inconnue" in origine
