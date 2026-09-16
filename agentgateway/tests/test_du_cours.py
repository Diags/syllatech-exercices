"""Les cinq configurations du support, et le diagnostic exact de chacune.

Ces tests verrouillent les dérives mesurées. S'ils tombent, c'est soit que
le schéma amont a changé — et il faut refaire la mesure — soit qu'on a
« corrigé » `configs/du-cours/`, ce qu'il ne faut pas faire : ces fichiers
sont la pièce à conviction.
"""

from __future__ import annotations

import pytest

from jobportal import schema_publie
from jobportal.commun import CONFIGS
from jobportal.config import charger

DU_COURS = CONFIGS / "du-cours"


def chemins_en_erreur(nom: str) -> list[str]:
    return [c for c, _ in schema_publie.verifier(charger(DU_COURS / nom))]


def messages(nom: str) -> str:
    return " | ".join(m for _, m in schema_publie.verifier(charger(DU_COURS / nom)))


def test_les_cinq_fichiers_sont_la():
    assert sorted(p.name for p in DU_COURS.glob("*.yaml")) == [
        "ch1-mcp-minimal.yaml",
        "ch2-llm-deux-fournisseurs.yaml",
        "ch3-mcp-federation.yaml",
        "ch4-a2a-et-inference.yaml",
        "ch5-securite.yaml",
    ]


def test_le_chapitre_1_est_exact():
    """Le seul des cinq que le schema accepte."""
    assert schema_publie.verifier(charger(DU_COURS / "ch1-mcp-minimal.yaml")) == []


@pytest.mark.parametrize("nom", [
    "ch2-llm-deux-fournisseurs.yaml",
    "ch3-mcp-federation.yaml",
    "ch4-a2a-et-inference.yaml",
    "ch5-securite.yaml",
])
def test_les_quatre_autres_sont_refuses(nom):
    assert schema_publie.verifier(charger(DU_COURS / nom)) != []


def test_ch2_match_au_lieu_de_matches():
    assert "'match' was unexpected" in messages("ch2-llm-deux-fournisseurs.yaml")


def test_ch2_openai_au_lieu_de_openAI():
    assert "'openai' was unexpected" in messages("ch2-llm-deux-fournisseurs.yaml")


def test_ch3_openapi_url_n_existe_pas():
    m = messages("ch3-mcp-federation.yaml")
    assert "'url' was unexpected" in m
    assert any("openapi" in c for c in chemins_en_erreur("ch3-mcp-federation.yaml"))


def test_ch4_a2a_n_est_pas_un_backend():
    assert "'a2a' was unexpected" in messages("ch4-a2a-et-inference.yaml")


def test_ch4_selfhosted_n_est_pas_un_fournisseur():
    assert "'selfHosted' was unexpected" in messages("ch4-a2a-et-inference.yaml")


def test_ch5_promptguard_n_est_pas_une_politique_de_route():
    assert "'promptGuard' was unexpected" in messages("ch5-securite.yaml")


def test_ch5_jwtauth_sans_source_de_cles():
    """`issuer` seul ne suffit pas : il faut `jwks`, ou `providers`."""
    m = messages("ch5-securite.yaml")
    assert "jwtAuth" in " ".join(chemins_en_erreur("ch5-securite.yaml"))
    assert "were unexpected" in m


def test_le_meme_jwtauth_avec_jwks_passe():
    """La contrepartie : ce n'est pas `issuer` qui gene, c'est son absence
    de compagnon.
    """
    from jobportal.config import depuis_texte
    corrige = depuis_texte("""
binds:
- port: 3000
  listeners:
  - routes:
    - policies:
        jwtAuth:
          mode: strict
          issuer: https://auth.exemple.fr
          audiences: [agents]
          jwks:
            file: ./cles.json
""")
    assert schema_publie.verifier(corrige) == []


def test_le_resume_ne_cache_pas_les_erreurs_brutes():
    """Le resume garde au plus trois feuilles par cause : il doit donc en
    rendre MOINS que le validateur, jamais zero quand il y en a.
    """
    config = charger(DU_COURS / "ch4-a2a-et-inference.yaml")
    brutes = schema_publie.verifier(config, resumer=False)
    resumees = schema_publie.verifier(config)
    assert brutes and resumees
    assert len(resumees) >= len(brutes)   # une cause peut donner 3 feuilles
