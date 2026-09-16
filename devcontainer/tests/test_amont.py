"""Le garde-fou : ce que les fichiers d'`amont/` disent, et qu'on cite.

Chaque affirmation de ce projet sur la spécification est verrouillée ici.
Si l'un de ces tests tombe, c'est que la spécification a bougé — et c'est
exactement ce qu'on veut apprendre par un test plutôt que par un ticket.
"""

from __future__ import annotations

import json

import pytest

from jobportal import schema_publie
from jobportal.commun import AMONT, FEATURES_AMONT, SCHEMA, SCHEMA_FEATURE
from jobportal.config import COMMANDES, POINTS_DE_DEPART

MANIFESTES = sorted(FEATURES_AMONT.glob("*.json"))


def test_les_fichiers_amont_sont_la():
    attendus = {"devContainer.base.schema.json", "devContainerFeature.schema.json",
                "feature-dependencies.md", "devcontainer-features.md",
                "devcontainerjson-reference.md", "devcontainer-reference.md",
                "features-user-env-variables.md",
                "parallel-lifecycle-script-execution.md", "PROVENANCE.md"}
    assert attendus <= {p.name for p in AMONT.iterdir() if p.is_file()}


def test_vingt_huit_manifestes():
    assert len(MANIFESTES) == 28


def test_le_schema_est_bien_celui_de_la_specification():
    document = schema_publie.document()
    assert document["$schema"] == "https://json-schema.org/draft/2019-09/schema"
    assert document["description"] == "Defines a dev container"
    assert SCHEMA.stat().st_size > 20_000


def test_jsonc_les_deux_drapeaux_different():
    """Le point du chapitre 1 : commentaires oui, virgules finales NON."""
    document = schema_publie.document()
    assert document["allowComments"] is True
    assert document["allowTrailingCommas"] is False


def test_la_racine_est_un_oneof_a_deux_branches():
    assert len(schema_publie.document()["oneOf"]) == 2
    assert schema_publie.document()["unevaluatedProperties"] is False


def test_les_trois_points_de_depart():
    d = schema_publie.definitions()
    assert d["imageContainer"]["required"] == ["image"]
    assert set(d["composeContainer"]["required"]) == {
        "dockerComposeFile", "service", "workspaceFolder"}
    assert set(POINTS_DE_DEPART) == {"image", "build", "dockerComposeFile"}


def test_shutdownaction_a_deux_enumerations():
    """Le point du chapitre 6 : la meme propriete, deux valeurs possibles."""
    assert schema_publie.enum_de("nonComposeBase", "shutdownAction") == [
        "none", "stopContainer"]
    assert schema_publie.enum_de("composeContainer", "shutdownAction") == [
        "none", "stopCompose"]


def test_workspacemount_n_existe_que_hors_compose():
    d = schema_publie.definitions()
    assert "workspaceMount" in d["nonComposeBase"]["properties"]
    assert "workspaceMount" not in d["composeContainer"]["properties"]


# ── le cycle de vie ─────────────────────────────────────────────────────

@pytest.mark.parametrize("commande, voisine", [
    ("initializeCommand", "onCreateCommand"),
    ("onCreateCommand", "updateContentCommand"),
    ("updateContentCommand", "postCreateCommand"),
    ("postCreateCommand", "postStartCommand"),
    ("postStartCommand", "postAttachCommand"),
])
def test_chaque_commande_cite_sa_voisine(commande, voisine):
    """L'ordre n'est pas une convention : il est dans les descriptions."""
    assert f'before "{voisine}"' in schema_publie.description(commande)


def test_l_ordre_des_six_commandes():
    assert COMMANDES == ("initializeCommand", "onCreateCommand",
                         "updateContentCommand", "postCreateCommand",
                         "postStartCommand", "postAttachCommand")


def test_initialize_tourne_sur_l_hote():
    assert "run locally" in schema_publie.description("initializeCommand")


def test_waitfor_vaut_updatecontent_par_defaut():
    assert 'The default is "updateContentCommand"' in \
        schema_publie.description("waitFor")


def test_waitfor_ne_peut_pas_attendre_la_derniere():
    """Cinq valeurs seulement : `postAttachCommand` n'en fait pas partie."""
    valeurs = schema_publie.enum("waitFor")
    assert len(valeurs) == 5
    assert "postAttachCommand" not in valeurs


@pytest.mark.parametrize("commande", COMMANDES)
def test_les_trois_formes_sont_documentees(commande):
    description = schema_publie.description(commande)
    assert "run in a shell" in description
    assert "without shell" in description
    assert "in parallel" in description


# ── les Features ────────────────────────────────────────────────────────

@pytest.mark.parametrize("chemin", MANIFESTES, ids=lambda p: p.stem)
def test_un_manifeste_passe_son_propre_schema(chemin):
    manifeste = json.loads(chemin.read_text(encoding="utf-8"))
    assert schema_publie.verifier_feature(manifeste) == []


def test_les_deux_schemas_ne_sont_pas_au_meme_brouillon():
    """Une subtilite qui coute cher si on l'ignore : appliquer les regles de
    2019-09 a un document draft-07 change le sens de `$ref`.
    """
    base = schema_publie.document(SCHEMA)
    feature = schema_publie.document(SCHEMA_FEATURE)
    assert base["$schema"].endswith("2019-09/schema")
    assert feature["$schema"].endswith("draft-07/schema#")
    assert feature["title"] == "Development Container Feature Metadata"
    assert set(feature["definitions"]) == {"Feature", "FeatureOption", "Mount"}


def test_les_relations_reelles_du_graphe():
    """Les quatre Features sur lesquelles l'ordre se joue vraiment."""
    lire = lambda n: json.loads((FEATURES_AMONT / f"{n}.json")   # noqa: E731
                                .read_text(encoding="utf-8"))
    G = "ghcr.io/devcontainers/features/"
    assert lire("github-cli")["installsAfter"] == [f"{G}common-utils", f"{G}git"]
    assert lire("oryx")["installsAfter"] == [f"{G}common-utils", f"{G}dotnet"]
    assert lire("python")["installsAfter"] == [f"{G}common-utils", f"{G}oryx"]
    assert lire("terraform")["dependsOn"] == {
        f"{G}github-cli:1": {"version": "latest"}}


def test_terraform_est_le_seul_a_declarer_une_dependance_dure():
    durs = [p.stem for p in MANIFESTES
            if json.loads(p.read_text(encoding="utf-8")).get("dependsOn")]
    assert durs == ["terraform"]


# ── ce que la specification ecrit noir sur blanc ────────────────────────

def test_la_regle_de_nommage_est_donnee_en_javascript():
    texte = (AMONT / "devcontainer-features.md").read_text(encoding="utf-8")
    assert r"replace(/[^\w_]/g, '_')" in texte
    assert r"replace(/^[\d_]+/g, '_')" in texte
    assert ".toUpperCase()" in texte


def test_une_option_omise_est_exportee_quand_meme():
    texte = (AMONT / "devcontainer-features.md").read_text(encoding="utf-8")
    assert "implicitly exported as its default value" in texte


def test_l_algorithme_est_specifie_en_trois_etapes():
    texte = (AMONT / "feature-dependencies.md").read_text(encoding="utf-8")
    assert "(B1) Building dependency graph" in texte
    assert "(B2) Assigning `roundPriority`" in texte
    assert "(B3) Round-based sorting" in texte
    assert "`roundPriority` of `n - idx`" in texte


def test_installsafter_est_mou_et_non_recursif():
    texte = (AMONT / "feature-dependencies.md").read_text(encoding="utf-8")
    assert "`installsAfter` is not recursive" in texte
    assert "remove all `installsAfter` directed edges that do not correspond" \
        in texte


def test_la_meme_feature_peut_tourner_plusieurs_fois():
    """Ce que le chapitre 3 mesure sur `11-ordre-impossible.json`."""
    texte = (AMONT / "feature-dependencies.md").read_text(encoding="utf-8")
    assert "the same Feature may be run multiple times" in texte


def test_l_egalite_compte_les_options():
    texte = (AMONT / "feature-dependencies.md").read_text(encoding="utf-8")
    assert "the options executed against the Feature are equal" in texte


def test_une_feature_locale_n_est_jamais_egale_a_une_autre():
    texte = (AMONT / "feature-dependencies.md").read_text(encoding="utf-8")
    assert "each Feature is considered unique" in texte
