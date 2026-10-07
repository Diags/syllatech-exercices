"""Le prédicat d'une route, et la détection d'ambiguïté.

Le prédicat est entièrement spécifié par le schéma (RouteMatch, PathMatch,
HeaderMatch). Un seul point ne l'est pas : `pathPrefix` est-il un préfixe de
SEGMENT ou de chaîne ? Ce fichier fixe le choix retenu — segment — pour qu'il
se conteste, et non pour qu'on l'oublie.
"""

from __future__ import annotations

import pytest

from jobportal.commun import PORTAIL
from jobportal.config import charger, depuis_texte
from jobportal.routage import (
    Requete, candidates, chemin_correspond, chevauchements,
    correspondance_correspond, route_correspond, routes_fourre_tout,
)


def config(routes: str):
    return depuis_texte(f"""
binds:
- port: 3000
  listeners:
  - routes:
{routes}
""")


# ── PathMatch ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("regle, chemin, attendu", [
    ({"exact": "/v1"}, "/v1", True),
    ({"exact": "/v1"}, "/v1/chat", False),
    ({"pathPrefix": "/v1"}, "/v1", True),
    ({"pathPrefix": "/v1"}, "/v1/chat", True),
    ({"pathPrefix": "/v1"}, "/v10", False),          # prefixe de SEGMENT
    ({"pathPrefix": "/v1"}, "/v1chat", False),
    ({"pathPrefix": "/"}, "/nimporte/quoi", True),
    ({"pathPrefix": "/v1/"}, "/v1/chat", True),
    ({"regex": "^/v[0-9]+/chat$"}, "/v2/chat", True),
    ({"regex": "^/v[0-9]+/chat$"}, "/v2/chat/x", False),
])
def test_forme_de_chemin(regle, chemin, attendu):
    assert chemin_correspond(regle, chemin) is attendu


def test_le_prefixe_de_segment_est_un_choix_de_ce_projet():
    """Ni le schema ni `amont/` ne tranchent. La Gateway API, si — et c'est
    la convention retenue. Ce test EXISTE pour rendre le choix visible.
    """
    assert chemin_correspond({"pathPrefix": "/mcp"}, "/mcpvoisin") is False


# ── RouteMatch : un ET ──────────────────────────────────────────────────

def test_tous_les_champs_doivent_passer():
    regle = {"path": {"pathPrefix": "/v1"},
             "method": {"method": "POST"},
             "headers": [{"name": "x-equipe", "value": {"exact": "rh"}}]}
    bonne = Requete("/v1/chat", "POST", {"x-equipe": "rh"})
    assert correspondance_correspond(regle, bonne)[0] is True
    for mauvaise in [
        Requete("/v2/chat", "POST", {"x-equipe": "rh"}),
        Requete("/v1/chat", "GET", {"x-equipe": "rh"}),
        Requete("/v1/chat", "POST", {"x-equipe": "data"}),
        Requete("/v1/chat", "POST", {}),
    ]:
        ok, raisons = correspondance_correspond(regle, mauvaise)
        assert ok is False and raisons


def test_les_entetes_sont_insensibles_a_la_casse():
    regle = {"headers": [{"name": "X-Equipe", "value": {"exact": "rh"}}]}
    assert correspondance_correspond(regle, Requete("/", entetes={"x-equipe": "rh"}))[0]


def test_les_pseudo_entetes():
    """« HTTP header or pseudo-header name (such as `:method`) »."""
    regle = {"headers": [{"name": ":method", "value": {"exact": "POST"}}]}
    assert correspondance_correspond(regle, Requete("/", "POST"))[0] is True
    assert correspondance_correspond(regle, Requete("/", "GET"))[0] is False


def test_les_parametres_de_requete():
    regle = {"query": [{"name": "stream", "value": {"exact": "true"}}]}
    assert correspondance_correspond(regle, Requete("/v1?stream=true"))[0] is True
    assert correspondance_correspond(regle, Requete("/v1?stream=false"))[0] is False
    assert correspondance_correspond(regle, Requete("/v1"))[0] is False


# ── LocalRoute.matches : un OU ──────────────────────────────────────────

def test_plusieurs_matches_sont_un_ou():
    c = config("""    - name: deux-chemins
      matches:
      - path: {exact: /v1/chat}
      - path: {exact: /v1/completions}
      backends: [{host: x:80}]
""")
    route = c.routes()[0]
    assert route_correspond(route, Requete("/v1/chat"))[0] is True
    assert route_correspond(route, Requete("/v1/completions"))[0] is True
    assert route_correspond(route, Requete("/v1/embeddings"))[0] is False


def test_une_route_sans_matches_attrape_tout():
    c = config("""    - name: fourre-tout
      backends: [{host: x:80}]
""")
    route = c.routes()[0]
    assert route.correspondances_ecrites is False
    for chemin in ("/", "/v1/chat", "/admin", "/mcp/tools"):
        assert route_correspond(route, Requete(chemin))[0] is True
    assert routes_fourre_tout(c) == [route]


def test_un_matches_vide_vaut_absent():
    c = config("""    - name: vide
      matches: []
      backends: [{host: x:80}]
""")
    assert route_correspond(c.routes()[0], Requete("/x"))[0] is True


# ── hostnames ───────────────────────────────────────────────────────────

def test_les_noms_d_hote():
    c = config("""    - name: rh
      hostnames: ["rh.portail.test"]
      backends: [{host: x:80}]
    - name: joker
      hostnames: ["*.portail.test"]
      backends: [{host: y:80}]
""")
    pris = [x.route.nom for x in candidates(c, Requete("/", hote="rh.portail.test"))]
    assert pris == ["rh", "joker"]
    assert [x.route.nom for x in
            candidates(c, Requete("/", hote="autre.exemple.test"))] == []


# ── ambiguite ───────────────────────────────────────────────────────────

def test_deux_routes_qui_se_chevauchent():
    c = config("""    - name: precise
      matches: [{path: {pathPrefix: /mcp}}]
      backends: [{host: x:80}]
    - name: fourre-tout
      backends: [{host: y:80}]
""")
    requetes = [Requete("/mcp"), Requete("/autre")]
    ambigues = chevauchements(c, requetes)
    assert len(ambigues) == 1
    assert [r.nom for r in ambigues[0][1]] == ["precise", "fourre-tout"]


def test_le_portail_n_est_pas_ambigu():
    c = charger(PORTAIL / "01-mcp.yaml")
    requetes = [Requete("/mcp"), Requete("/mcp/tools"), Requete("/v1/chat"),
                Requete("/")]
    assert chevauchements(c, requetes) == []
    assert routes_fourre_tout(c) == []


def test_l_ordre_des_routes_est_celui_du_fichier():
    c = config("""    - name: a
      backends: [{host: x:80}]
    - name: b
      backends: [{host: y:80}]
    - name: c
      backends: [{host: z:80}]
""")
    assert [r.nom for r in c.routes()] == ["a", "b", "c"]
    assert [x.route.nom for x in candidates(c, Requete("/"))] == ["a", "b", "c"]


def test_la_position_dit_ou_chercher():
    c = charger(PORTAIL / "03-securite.yaml")
    assert c.routes()[0].position() == "binds[0].listeners[0].routes[0]"
