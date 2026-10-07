"""Le garde-fou : ce projet transcrit un validateur Go qu'il ne fait pas
tourner. `amont/exemples/` contient les manifestes d'exemple du depot,
copies verbatim. S'ils cessent de passer, c'est la transcription qui a
tort — pas eux.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from jobportal import regles, schema_publie
from jobportal.catalogue import Catalogue
from jobportal.commun import EXEMPLES_AMONT, SCHEMA
from jobportal.manifeste import GROUPE_VERSION, TYPES, charger

AMONT = EXEMPLES_AMONT


def documents_amont():
    for chemin in sorted(AMONT.glob("*.yaml")):
        for doc in charger(chemin):
            yield pytest.param(doc, id=f"{chemin.stem}[{doc.rang}]")


TOUS = list(documents_amont())


def test_les_sept_fichiers_sont_la():
    assert sorted(p.name for p in AMONT.glob("*.yaml")) == [
        "agent.yaml", "full-stack.yaml", "mcp-remote.yaml", "mcp.yaml",
        "model.yaml", "prompt.yaml", "skill.yaml",
    ]


def test_dix_documents():
    """full-stack.yaml en porte quatre a lui seul."""
    assert len(TOUS) == 10


@pytest.mark.parametrize("doc", TOUS)
def test_amont_passe_le_schema_publie(doc):
    assert schema_publie.verifier(doc) == []


@pytest.mark.parametrize("doc", TOUS)
def test_amont_passe_le_validateur(doc):
    """Avec les defauts du serveur : aucun exemple amont ne pose d'espace de
    noms, et ValidateObjectMeta l'exige. Le defaut vient d'avant.
    """
    assert regles.verifier(doc.avec_defauts()) == []


@pytest.mark.parametrize("doc", TOUS)
def test_amont_sans_defauts_echoue_sur_l_espace(doc):
    """La contrepartie : valider le FICHIER, ce n'est pas valider l'objet."""
    erreurs = regles.verifier(doc)
    chemins = [e.chemin for e in erreurs]
    assert chemins == ["metadata.namespace"], erreurs


@pytest.mark.parametrize("doc", TOUS)
def test_amont_porte_la_bonne_api(doc):
    assert doc.api == GROUPE_VERSION


def test_full_stack_s_applique_dans_son_ordre():
    """« Resources are applied in document order, so define dependencies
    first » — le fichier amont respecte sa propre consigne.
    """
    catalogue = Catalogue()
    resultats = catalogue.appliquer_tous(charger(AMONT / "full-stack.yaml"))
    assert all(r.accepte for r in resultats), \
        [str(e) for r in resultats for e in r.erreurs]
    assert len(catalogue) == 4


def test_full_stack_a_l_envers_pendouille():
    """Le meme fichier, documents renverses : l'agent arrive avant ses
    dependances et sa reference ne resout rien.
    """
    catalogue = Catalogue()
    documents = list(charger(AMONT / "full-stack.yaml"))[::-1]
    resultats = catalogue.appliquer_tous(documents)
    refuses = [r for r in resultats if not r.accepte]
    assert len(refuses) == 1
    assert refuses[0].document.type == "Agent"
    assert len(refuses[0].references) == 1
    assert len(catalogue) == 3


def test_le_schema_est_bien_celui_du_depot():
    """Trois reperes qu'aucune copie approximative n'aurait."""
    document = schema_publie.document()
    assert document["openapi"] == "3.1.0"
    assert "/v0/mcpservers" in document["paths"]
    assert "/v0.1/servers" in document["paths"]


def test_le_schema_publie_couvre_les_neuf_types():
    """Les neuf `kind` de kinds.go ont chacun un schema d'enveloppe."""
    assert set(schema_publie.types_publies()) == set(TYPES)


def test_le_fichier_de_schema_n_a_pas_ete_retouche():
    """Un repere de taille : le document est copie, pas resume."""
    lignes = SCHEMA.read_text(encoding="utf-8").splitlines()
    assert len(lignes) > 3_000


def test_mcp_yaml_amont_est_bien_du_stdio_oci():
    """Le manifeste que le cours cite, tel qu'il est vraiment."""
    doc = next(iter(charger(AMONT / "mcp.yaml")))
    origine = doc.spec["source"]["package"]["origin"]
    assert origine["type"] == "oci"
    assert doc.spec["source"]["package"]["transport"]["type"] == "stdio"
    assert "runtime" not in doc.spec and "package" not in doc.spec


def test_mcp_remote_amont_porte_un_type_de_remote():
    """`streamable-http` est un type de REMOTE. Pose sur un transport de
    paquet, il est refuse — c'est le document 5 d'a-corriger.yaml.
    """
    doc = next(iter(charger(AMONT / "mcp-remote.yaml")))
    assert doc.spec["remote"]["type"] == "streamable-http"
    assert "source" not in doc.spec


def test_model_amont_omet_son_etiquette():
    """« tag omitted: stored and resolved as the literal "latest" tag »."""
    doc = next(iter(charger(AMONT / "model.yaml")))
    assert doc.etiquette == ""
    assert str(Catalogue.identite_de(doc)) == "Model/default/default@latest"
