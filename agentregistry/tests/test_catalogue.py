"""Le catalogue : l'identite, l'ordre, et ce que « epingler » veut dire."""

from __future__ import annotations

import copy

import pytest

from jobportal.catalogue import Catalogue, Identite
from jobportal.commun import CATALOGUE, EXEMPLES_AMONT
from jobportal.manifeste import Document, charger, charger_dossier

PORTAIL = CATALOGUE / "portail"
ORDRE_DE_DEPENDANCE = ["mcp-offres", "mcp-scoring", "mcp-annuaire",
                       "skill-tri", "prompt-entretien", "modele-defaut",
                       "agent-recruteur"]


def portail() -> Catalogue:
    catalogue = Catalogue()
    for nom in ORDRE_DE_DEPENDANCE:
        catalogue.appliquer_tous(charger(PORTAIL / f"{nom}.yaml"))
    return catalogue


def test_le_portail_s_applique_en_entier():
    catalogue = portail()
    assert len(catalogue) == 7
    assert all(r.accepte for r in catalogue.journal), \
        [str(e) for r in catalogue.journal for e in r.erreurs]


def test_le_dossier_en_ordre_alphabetique_casse():
    """Un dossier n'a pas d'ordre, et `agent-recruteur.yaml` vient en tete de
    l'alphabet. Ses cinq references pendouillent, et l'agent est refuse.
    """
    catalogue = Catalogue()
    resultats = catalogue.appliquer_tous(charger_dossier(PORTAIL))
    refuses = [r for r in resultats if not r.accepte]
    assert [r.document.nom for r in refuses] == ["recruteur"]
    assert len(refuses[0].references) == 5
    assert len(catalogue) == 6


# ── identite ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("meta, attendu", [
    ({"name": "offres"}, "MCPServer/default/offres@latest"),
    ({"name": "offres", "tag": "stable"}, "MCPServer/default/offres@stable"),
    ({"name": "offres", "namespace": "rh"}, "MCPServer/rh/offres@latest"),
])
def test_identite_effective(meta, attendu):
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "MCPServer",
                    "metadata": meta, "spec": {}})
    assert str(Catalogue.identite_de(doc)) == attendu


def test_un_objet_mutable_n_a_pas_d_etiquette():
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "Deployment",
                    "metadata": {"name": "prod"}, "spec": {}})
    assert str(Catalogue.identite_de(doc)) == "Deployment/default/prod"


def test_defauts_appliques_est_l_ecart_entre_le_fichier_et_l_objet():
    doc = next(iter(charger(EXEMPLES_AMONT / "model.yaml")))
    assert doc.defauts_appliques() == [
        "metadata.namespace → default", "metadata.tag → latest"]


def test_le_manifeste_du_portail_n_a_qu_un_defaut():
    """Ils posent tous leur etiquette ; aucun ne pose son espace de noms."""
    for nom in ORDRE_DE_DEPENDANCE:
        doc = next(iter(charger(PORTAIL / f"{nom}.yaml")))
        attendus = ["metadata.namespace → default"]
        if nom == "modele-defaut":
            attendus.append("metadata.tag → latest")
        assert doc.defauts_appliques() == attendus, nom


# ── resolution ──────────────────────────────────────────────────────────

def test_les_references_normalisees():
    doc = next(iter(charger(PORTAIL / "agent-recruteur.yaml")))
    cibles = [str(c) for _, c, _ in Catalogue().references_de(doc)]
    assert cibles == [
        "MCPServer/default/offres@stable",
        "MCPServer/default/scoring-cv@stable",
        "MCPServer/default/annuaire-pro@stable",
        "Skill/default/tri-candidatures@stable",
        "Prompt/default/entretien-structure@stable",
    ]


def test_une_reference_sans_etiquette_vise_latest():
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
                    "metadata": {"name": "a", "namespace": "default"},
                    "spec": {"mcpServers": [{"name": "offres"}]}})
    _, cible, _ = Catalogue().references_de(doc)[0]
    assert str(cible) == "MCPServer/default/offres@latest"


def test_une_reference_sans_espace_prend_celui_de_l_agent():
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
                    "metadata": {"name": "a", "namespace": "rh"},
                    "spec": {"mcpServers": [{"name": "offres"}]}})
    _, cible, _ = Catalogue().references_de(doc)[0]
    assert cible.espace == "rh"


def test_le_type_est_pose_dans_l_objet_STOCKE():
    """« The defaulting must persist into the stored spec » — le fichier dit
    `{name: offres}`, la fiche du catalogue dit `{kind: MCPServer, ...}`.
    """
    catalogue = portail()
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
                    "metadata": {"name": "sobre", "namespace": "default",
                                 "tag": "stable"},
                    "spec": {"mcpServers": [{"name": "offres",
                                             "tag": "stable"}]}})
    ecrit = copy.deepcopy(doc.brut)
    resultat = catalogue.appliquer(doc)
    assert resultat.accepte
    stocke = catalogue.obtenir(resultat.identite)
    assert "kind" not in ecrit["spec"]["mcpServers"][0]
    assert stocke["spec"]["mcpServers"][0]["kind"] == "MCPServer"


def test_reference_pendante_sur_une_etiquette_absente():
    catalogue = portail()
    doc = Document({"apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
                    "metadata": {"name": "b", "namespace": "default"},
                    "spec": {"compatibleHarnesses": [{"type": "claude-code"}],
                             "skills": [{"kind": "Skill",
                                         "name": "tri-candidatures",
                                         "tag": "v2"}]}})
    resultat = catalogue.appliquer(doc)
    assert not resultat.accepte
    assert resultat.structure == []
    assert "v2" in resultat.references[0].cause


def test_un_agent_refuse_n_est_pas_ecrit():
    catalogue = portail()
    avant = len(catalogue)
    catalogue.appliquer(Document({
        "apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
        "metadata": {"name": "c", "namespace": "default"},
        "spec": {"mcpServers": [{"kind": "MCPServer", "name": "absent"}]}}))
    assert len(catalogue) == avant


# ── l'etiquette qui bouge ───────────────────────────────────────────────

def test_reappliquer_la_meme_etiquette_remplace():
    """Le coeur du chapitre 4 : « stable » n'est pas une version, c'est un
    NOM. Le republier ne casse aucune reference — il change ce qu'elles
    designent, et l'agent n'a pas bouge d'un octet.
    """
    catalogue = portail()
    identite = Identite("Skill", "default", "tri-candidatures", "stable")
    avant = catalogue.obtenir(identite)["spec"]["source"]["repository"]

    nouveau = next(iter(charger(PORTAIL / "skill-tri.yaml")))
    nouveau.brut["spec"]["source"]["repository"]["subfolder"] = \
        "skills/tri-candidatures-v2"
    resultat = catalogue.appliquer(nouveau)

    assert resultat.accepte
    assert resultat.remplace == identite
    assert len(catalogue) == 7              # rien n'a ete ajoute
    apres = catalogue.obtenir(identite)["spec"]["source"]["repository"]
    assert avant["subfolder"] != apres["subfolder"]

    agent = next(iter(charger(PORTAIL / "agent-recruteur.yaml")))
    assert catalogue.resoudre(agent.avec_defauts()) == []


def test_deux_etiquettes_cohabitent():
    catalogue = portail()
    autre = next(iter(charger(PORTAIL / "skill-tri.yaml")))
    autre.brut["metadata"]["tag"] = "v2"
    catalogue.appliquer(autre)
    assert catalogue.etiquettes("Skill", "tri-candidatures") == ["stable", "v2"]
    assert len(catalogue) == 8


def test_un_agent_epingle_sur_latest_suit_la_derniere_publication():
    """Deux agents identiques a une ligne pres. Celui qui n'epingle pas
    reference `latest` ; republier le skill sous `latest` change ce qu'il
    consomme, sans que sa fiche change.
    """
    catalogue = portail()
    flottant = next(iter(charger(PORTAIL / "skill-tri.yaml")))
    flottant.brut["metadata"].pop("tag")
    flottant.brut["spec"]["source"]["repository"]["subfolder"] = "v-du-jour"
    catalogue.appliquer(flottant)

    agent = Document({
        "apiVersion": "ar.dev/v1alpha1", "kind": "Agent",
        "metadata": {"name": "flottant", "namespace": "default"},
        "spec": {"compatibleHarnesses": [{"type": "claude-code"}],
                 "skills": [{"kind": "Skill", "name": "tri-candidatures"}]}})
    assert catalogue.appliquer(agent).accepte

    _, cible, _ = catalogue.references_de(agent.avec_defauts())[0]
    assert cible.etiquette == "latest"
    assert catalogue.obtenir(cible)["spec"]["source"]["repository"][
        "subfolder"] == "v-du-jour"


# ── a-corriger ──────────────────────────────────────────────────────────

def test_a_corriger_sur_un_catalogue_peuple():
    catalogue = portail()
    documents = list(charger(CATALOGUE / "a-corriger.yaml"))
    resultats = catalogue.appliquer_tous(documents)
    refuses = [r.document.nom for r in resultats if not r.accepte]
    assert refuses == ["mauvaise-api", "spec-vide", "forme-a-plat",
                       "transport-croise", "Tri_Candidatures",
                       "entretien-guide", "recruteur-nu",
                       "recruteur-fantome"]
    assert len(refuses) == 8


def test_les_trois_trous_entrent_dans_le_catalogue():
    """Ils ne sont pas « tolerés » : ils sont ECRITS, et se presentent dans
    l'interface comme les autres.
    """
    catalogue = portail()
    catalogue.appliquer_tous(charger(CATALOGUE / "a-corriger.yaml"))
    noms = {i.nom for i in catalogue.objets}
    assert {"source-vide", "sans-version", "consignes-entretien"} <= noms
    assert len(catalogue) == 7 + 3
