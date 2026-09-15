"""Les quatre corrections, validées contre le schéma publié.

`test_du_cours.py` établit que les configurations du support sont refusées.
Celui-ci établit la moitié qui manque : que les versions corrigées, elles,
passent. Sans ces tests, une correction serait une opinion.

Ce sont aussi les blocs qui ont été portés dans la page de cours, à la
ponctuation près — si le schéma amont bouge, c'est ici qu'on l'apprend.
"""

from __future__ import annotations

import pytest

from jobportal import schema_publie
from jobportal.config import depuis_texte

CH2 = """
llm:
  gateways: [default]
  models:
  - name: principal
    visibility: internal
    provider: anthropic
    params: { model: claude-sonnet-5, apiKey: $ANTHROPIC_API_KEY }
  - name: secours
    visibility: internal
    provider: openAI
    params: { model: gpt-5.2, apiKey: $OPENAI_API_KEY }
  virtualModels:
  - name: assistant
    routing:
      failover:
        targets:
        - { model: principal, priority: 0 }
        - { model: secours,   priority: 1 }
gateways:
  default: { port: 3000 }
"""

CH3 = """
binds:
- port: 3000
  listeners:
  - routes:
    - backends:
      - mcp:
          targets:
          - name: postgres
            stdio: { cmd: uvx, args: ["mcp-server-postgres"] }
          - name: navigateur
            stdio: { cmd: npx, args: ["@playwright/mcp"] }
          - name: api-interne
            openapi:
              schema: { file: ./openapi.json }
              host: api.jobportal.fr:443
          prefixMode: always
"""

CH4 = """
binds:
- port: 3000
  listeners:
  - routes:
    - name: pair-analyste
      matches: [ { path: { pathPrefix: /a2a } } ]
      policies:
        a2a: {}
      backends:
      - host: agent-analyste:8080
    - name: modele-auto-heberge
      matches: [ { path: { pathPrefix: /v1/chat/completions } } ]
      backends:
      - service: { name: default/vllm, port: 8000 }
        policies:
          inferenceRouting:
            endpointPicker: { host: 127.0.0.1:9002 }
            destinationMode: passthrough
services:
- name: vllm
  namespace: default
  hostname: vllm
  vips: []
  ports: { 8000: 8000 }
"""

CH5 = """
binds:
- port: 3000
  listeners:
  - routes:
    - policies:
        jwtAuth:
          mode: strict
          issuer: https://auth.exemple.fr
          audiences: [agents]
          jwks: { file: ./cles.json }
        mcpAuthorization:
          rules:
          - allow: 'has(jwt.team) && jwt.team == "data"
                    && mcp.tool.name.startsWith("postgres_")'
          - require: 'has(jwt.sub)'
        ai:
          promptGuard:
            request:
            - regex:
                action: reject
                rules:
                - builtin: creditCard
"""

CORRIGES = {"ch2": CH2, "ch3": CH3, "ch4": CH4, "ch5": CH5}


@pytest.mark.parametrize("nom, texte", CORRIGES.items(), ids=list(CORRIGES))
def test_une_correction_passe_le_schema(nom, texte):
    erreurs = schema_publie.verifier(depuis_texte(texte, nom))
    assert erreurs == [], erreurs


def test_ch2_la_bascule_est_bien_une_bascule():
    from jobportal import modeles
    config = depuis_texte(CH2)
    virtuel = modeles.modeles_virtuels(config)[0]
    decision = modeles.choisir(virtuel["routing"], {})
    assert decision.forme == "failover"
    assert decision.modele == "principal"


def test_ch3_le_prefixage_est_explicite():
    config = depuis_texte(CH3)
    backend = config.routes()[0].backends[0]["mcp"]
    assert backend["prefixMode"] == "always"
    assert [t for _, t, _ in config.cibles_mcp()] == ["stdio", "stdio", "openapi"]


def test_ch4_a2a_est_sur_la_route_et_inference_sur_le_backend():
    config = depuis_texte(CH4)
    routes = config.routes()
    assert "a2a" in routes[0].politiques
    assert "inferenceRouting" in routes[1].backends[0]["policies"]
    assert "a2a" not in routes[1].backends[0]


def test_ch5_toutes_les_regles_sont_defensives():
    from jobportal import autorisation
    route = depuis_texte(CH5).routes()[0]
    regles = autorisation.lire(route.politiques["mcpAuthorization"])
    assert len(regles) == 2
    assert all(autorisation.defensive(r.expression) for r in regles)
    assert {r.forme for r in regles} == {"allow", "require"}


def test_ch5_le_garde_refuse_vraiment():
    from jobportal import gardes
    route = depuis_texte(CH5).routes()[0]
    constats = gardes.passer(route.politiques,
                             "Carte 4539 1488 0343 6467 du candidat.")
    assert len(constats) == 1
    assert constats[0].bloque is True


def test_ch5_le_jwt_est_strict_et_a_ses_cles():
    route = depuis_texte(CH5).routes()[0]
    jwt = route.politiques["jwtAuth"]
    assert jwt["mode"] == "strict"
    assert "jwks" in jwt
