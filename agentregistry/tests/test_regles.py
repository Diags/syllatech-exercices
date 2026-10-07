"""Les regles, une par une — y compris celles qui ne disent rien.

Un validateur se juge autant sur ce qu'il laisse passer que sur ce qu'il
refuse. Les tests marques « trou » fixent un comportement qu'on aimerait
different : ils sont la pour que le jour ou l'amont le change, ce projet le
voie.
"""

from __future__ import annotations

import pytest

from jobportal import regles, schema_publie
from jobportal.commun import CATALOGUE
from jobportal.manifeste import Document, charger

A_CORRIGER = list(charger(CATALOGUE / "a-corriger.yaml"))


def doc(brut: dict) -> Document:
    """Un manifeste minimal, defauts de serveur poses."""
    base = {"apiVersion": "ar.dev/v1alpha1", "metadata": {"name": "x"},
            "spec": {}}
    base.update(brut)
    return Document(base).avec_defauts()


def chemins(erreurs) -> list[str]:
    return [e.chemin for e in erreurs]


# ── metadata ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("nom, valide", [
    ("offres", True),
    ("io.example.mcp", True),
    ("mcp-offres-2", True),
    ("Tri_Candidatures", False),      # majuscules et souligne
    ("-offres", False),               # ne commence pas par un alphanumerique
    ("offres-", False),
    ("offres..scoring", False),        # segment vide
    ("", False),
    ("a" * 64, False),                 # un segment de plus de 63 caracteres
    ("a" * 63, True),
    (".".join(["a" * 63] * 3 + ["a" * 61]), True),      # 253 caracteres pile
    (".".join(["a" * 63] * 3 + ["a" * 62]), False),     # 254
])
def test_nom_dns_1123(nom, valide):
    assert (regles.valider_nom(nom) is None) is valide


def test_nom_avec_retour_a_la_ligne_est_refuse():
    """Go ancre ^…$ sans (?m) : `$` ne vaut qu'en fin de texte. Avec
    re.match au lieu de re.fullmatch, « offres\\nrm -rf » passerait.
    """
    assert regles.valider_nom("offres\nmalveillant") is not None


@pytest.mark.parametrize("espace, valide", [
    ("default", True), ("equipe-rh", True), ("Equipe", False), ("", False),
])
def test_espace_de_noms(espace, valide):
    erreurs = regles.valider_metadonnees(
        Document({"kind": "Prompt", "metadata": {"name": "p",
                                                 "namespace": espace}}))
    assert ("metadata.namespace" in chemins(erreurs)) is not valide


@pytest.mark.parametrize("etiquette, valide", [
    ("stable", True), ("v1.2.0", True), ("latest", True), ("_interne", True),
    ("-debut", False), (".debut", False), ("a" * 128, True),
    ("a" * 129, False), ("", False),
])
def test_format_d_etiquette(etiquette, valide):
    assert (regles.valider_etiquette(etiquette) is None) is valide


def test_etiquette_sur_un_type_non_etiquetable():
    """validateRef : « kind %q does not support tag pinning ». Deployment et
    Runtime sont des objets mutables, pas des artefacts.
    """
    erreurs = regles.valider_reference(
        {"kind": "Deployment", "name": "prod", "tag": "stable"}, "ref")
    assert "ref.tag" in chemins(erreurs)


def test_libelle_mal_forme():
    erreurs = regles.valider_metadonnees(doc(
        {"kind": "Prompt", "metadata": {"name": "p", "namespace": "default",
                                        "labels": {"Equipe RH": "oui"}}}))
    assert any("labels" in c for c in chemins(erreurs))


# ── url et icone ────────────────────────────────────────────────────────

def test_url_sans_hote():
    """La seule regle non mecanique de la transcription : Go parse avec
    net/url, Python avec urllib. Le comportement retenu est « hote vide =
    refus », et ce test le fixe.
    """
    assert regles.valider_url_site("pas-une-url") is not None
    assert regles.valider_url_site("https://exemple.test/x") is None
    assert regles.valider_url_site("") is None          # facultatif


@pytest.mark.parametrize("url, valide", [
    ("https://cdn.test/i.svg", True),
    ("/images/i.svg", True),                 # chemin sur l'origine de l'UI
    ("//autre.test/i.svg", False),           # relatif au schema : un AUTRE hote
    ("http://cdn.test/i.svg", False),        # contenu mixte
    ("javascript:alert(1)", False),          # le champ est un src d'image
    ("data:image/svg+xml,<svg/>", False),
    ("", True),
])
def test_url_d_icone(url, valide):
    assert (regles.valider_url_icone(url) is None) is valide


def test_titre_blanc_pur():
    assert regles.valider_titre("   ") is not None
    assert regles.valider_titre("") is None


# ── MCPServer ───────────────────────────────────────────────────────────

def test_source_et_remote_s_excluent():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {
        "source": {}, "remote": {"type": "sse", "url": "https://x.test"}}}))
    assert chemins(erreurs) == ["spec"]
    assert "s'excluent" in erreurs[0].cause


def test_ni_source_ni_remote():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {}}))
    assert chemins(erreurs) == ["spec"]


def test_trou_source_vide():
    """TROU : `spec.source: {}` decrit un serveur sans adresse ni transport,
    et il est valide. validateMCPServerSource sort si Package est nil, sans
    rien exiger.
    """
    assert regles.verifier(doc({"kind": "MCPServer",
                                "spec": {"source": {}}})) == []


@pytest.mark.parametrize("transport, chemin_attendu", [
    ({"type": "stdio"}, None),
    ({"type": "http", "port": 8931}, None),
    ({"type": "http"}, "spec.source.package.transport.port"),
    ({"type": "sse"}, "spec.source.package.transport.type"),
    ({"type": "streamable-http"}, "spec.source.package.transport.type"),
    ({}, "spec.source.package.transport.type"),
])
def test_transport_de_paquet(transport, chemin_attendu):
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": transport, "origin": {
            "type": "oci", "identifier": "ghcr.io/x/y:1.0.0",
            "oci": {"serverName": "io.x/y"}}}}}}))
    assert (chemin_attendu in chemins(erreurs)) if chemin_attendu \
        else erreurs == []


def test_union_d_origine_une_seule():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"}, "origin": {
            "type": "oci", "identifier": "x",
            "oci": {"serverName": "io.x/y"},
            "npm": {"version": "1", "serverName": "io.x/y"}}}}}}))
    assert "spec.source.package.origin" in chemins(erreurs)


def test_origine_sans_sous_objet():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"},
                    "origin": {"type": "oci", "identifier": "x"}}}}}))
    assert "spec.source.package.origin" in chemins(erreurs)


def test_origine_qui_ne_correspond_pas_au_discriminant():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"}, "origin": {
            "type": "npm", "identifier": "x",
            "oci": {"serverName": "io.x/y"}}}}}}))
    assert "spec.source.package.origin.npm" in chemins(erreurs)


def test_npm_exige_sa_version():
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"}, "origin": {
            "type": "npm", "identifier": "@x/y",
            "npm": {"serverName": "io.x/y"}}}}}}))
    assert "spec.source.package.origin.npm.version" in chemins(erreurs)


@pytest.mark.parametrize("type_", ["npx", "uvx", "http", "docker"])
def test_les_origines_du_support_de_cours_n_existent_pas(type_):
    """npx et uvx ne sont pas des origines : ce sont les commandes que le
    resolveur DERIVE d'une origine npm ou pypi quand `launch` est absent.
    """
    erreurs = regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"}, "origin": {
            "type": type_, "identifier": "x",
            "oci": {"serverName": "io.x/y"}}}}}}))
    assert "spec.source.package.origin.type" in chemins(erreurs)


def test_trou_oci_sans_tag():
    """TROU : l'exemple amont dit « OCI identifier must include an explicit
    tag or digest » ; la validation structurelle ne le verifie pas. Le test
    amont TestMCPServerValidate_HTTPPortRange fait meme passer un « :latest ».
    """
    assert regles.verifier(doc({"kind": "MCPServer", "spec": {"source": {
        "package": {"transport": {"type": "stdio"}, "origin": {
            "type": "oci", "identifier": "ghcr.io/x/y",
            "oci": {"serverName": "io.x/y"}}}}}})) == []


def test_remote_sans_url():
    erreurs = regles.verifier(doc({"kind": "MCPServer",
                                   "spec": {"remote": {"type": "sse"}}}))
    assert "spec.remote.url" in chemins(erreurs)


# ── Skill, Prompt ───────────────────────────────────────────────────────

def test_branche_sans_depot():
    erreurs = regles.verifier(doc({"kind": "Skill", "spec": {
        "source": {"repository": {"branch": "production"}}}}))
    assert "spec.source.repository.branch" in chemins(erreurs)


def test_trou_prompt_sans_contenu():
    """TROU, assume par l'amont : « Content MAY be empty (a prompt can be
    purely descriptive), so we don't require it here. »
    """
    assert regles.verifier(doc({"kind": "Prompt",
                                "spec": {"description": "des consignes"}})) == []


# ── Agent ───────────────────────────────────────────────────────────────

def test_composition_sans_harnais():
    erreurs = regles.verifier(doc({"kind": "Agent", "spec": {
        "skills": [{"kind": "Skill", "name": "tri"}]}}))
    assert "spec" in chemins(erreurs)


def test_composition_avec_harnais():
    assert regles.verifier(doc({"kind": "Agent", "spec": {
        "compatibleHarnesses": [{"type": "claude-code"}],
        "skills": [{"kind": "Skill", "name": "tri"}]}})) == []


def test_harnais_en_double():
    erreurs = regles.verifier(doc({"kind": "Agent", "spec": {
        "compatibleHarnesses": [{"type": "claude-code"},
                                {"type": "claude-code"}]}}))
    assert "spec.compatibleHarnesses[1].type" in chemins(erreurs)


def test_reference_sans_kind_est_toleree():
    """Le validateur pose le type depuis le CHAMP. Le schema publie, lui,
    declare `kind` obligatoire sur ResourceRef — les deux contrats different.
    """
    sans_kind = doc({"kind": "Agent", "spec": {
        "mcpServers": [{"name": "offres"}]}})
    assert regles.verifier(sans_kind) == []
    assert schema_publie.verifier(sans_kind) != []


def test_reference_avec_le_mauvais_kind():
    erreurs = regles.verifier(doc({"kind": "Agent", "spec": {
        "mcpServers": [{"kind": "Skill", "name": "tri"}]}}))
    assert "spec.mcpServers[0].kind" in chemins(erreurs)


def test_protocole_hors_ensemble():
    erreurs = regles.verifier(doc({"kind": "Agent", "spec": {
        "source": {"image": "ghcr.io/x/y:1", "protocol": "grpc"}}}))
    assert "spec.source.protocol" in chemins(erreurs)


# ── Model ───────────────────────────────────────────────────────────────

def test_fournisseur_inconnu():
    erreurs = regles.verifier(doc({"kind": "Model", "spec": {
        "provider": "openai", "model": "gpt-x"}}))
    assert "spec.provider" in chemins(erreurs)


def test_bedrock_sans_auth_est_valide():
    """« Omitted auth means the provider default: "runtime" for
    ambient-identity providers. »
    """
    assert regles.verifier(doc({"kind": "Model", "spec": {
        "provider": "bedrock", "model": "us.anthropic.claude-opus-4-8"}})) == []


def test_secret_ref_sans_secret():
    erreurs = regles.verifier(doc({"kind": "Model", "spec": {
        "provider": "bedrock", "model": "m",
        "auth": {"strategy": "secretRef"}}}))
    assert "spec.auth.secretRef" in chemins(erreurs)


def test_secret_ref_avec_strategie_runtime():
    erreurs = regles.verifier(doc({"kind": "Model", "spec": {
        "provider": "bedrock", "model": "m",
        "auth": {"strategy": "runtime", "secretRef": {"name": "cle"}}}}))
    assert "spec.auth.secretRef" in chemins(erreurs)


# ── le fichier a corriger, en entier ────────────────────────────────────

def test_a_corriger_porte_onze_documents():
    assert len(A_CORRIGER) == 11


@pytest.mark.parametrize("rang, couches", [
    (0,  ("B",)),        # apiVersion du support de cours
    (1,  ("B",)),        # spec vide
    (2,  ()),            # source vide — TROU
    (3,  ("A", "B")),    # runtime/package/transport a plat
    (4,  ("B",)),        # transport de remote sur un paquet
    (5,  ()),            # image OCI sans version — TROU
    (6,  ("B",)),        # nom non DNS-1123
    (7,  ("B",)),        # branche sans depot
    (8,  ()),            # prompt sans contenu — TROU
    (9,  ("A", "B")),    # kind absent (A) + skills sans harnais (B)
    (10, ()),            # tout est bien forme, rien n'existe — couche C
])
def test_quelle_couche_attrape_quoi(rang, couches):
    document = A_CORRIGER[rang]
    attrape = set()
    if schema_publie.verifier(document):
        attrape.add("A")
    if regles.verifier(document.avec_defauts()):
        attrape.add("B")
    assert attrape == set(couches)


def test_trois_documents_passent_les_deux_premieres_couches():
    muets = [d for d in A_CORRIGER
             if not schema_publie.verifier(d)
             and not regles.verifier(d.avec_defauts())]
    assert [d.nom for d in muets] == [
        "source-vide", "sans-version", "consignes-entretien",
        "recruteur-fantome"]
