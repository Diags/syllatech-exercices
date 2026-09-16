"""La fiche que le catalogue PUBLIE pour un serveur MCP.

AgentRegistry expose ses serveurs MCP sous l'API du registre MCP amont
(`GET /v0.1/servers`). Cette route ne rend pas le manifeste : elle rend une
projection, et la projection remplit les champs que la specification amont
declare obligatoires — `description` et `version` — meme quand le manifeste ne
les donne pas.

Transcrit de `pkg/mcpregistry/translate.go`. C'est le module le plus court du
projet et le plus surprenant : trois cascades de repli, aucune trace dans la
fiche de savoir si la valeur vient du manifeste ou d'un defaut.
"""

from __future__ import annotations

from typing import Any

from jobportal.manifeste import ESPACE_PAR_DEFAUT, ETIQUETTE_PAR_DEFAUT, Document

# translate.go : « defaultVersion is emitted when a server has no derivable
# version. The spec requires a non-empty version string; this is a
# deterministic placeholder. »
VERSION_DE_REPLI = "0.0.0"

SEPARATEUR = "/"


def nom_de_catalogue(espace: str, nom: str) -> str:
    """ServerName : « <namespace>/<name> », toujours qualifie."""
    return f"{espace or ESPACE_PAR_DEFAUT}{SEPARATEUR}{nom}"


def version_depuis_identifiant_oci(identifiant: str) -> str:
    """ociVersionFromIdentifier.

    « A digest ("repo@sha256:...") wins; otherwise the tag after the final ":"
    in the last path segment is used. Returns "" when neither is present. »

    Le detail qui compte : le « : » n'est cherche que dans le DERNIER segment,
    « so registry ports like "ghcr.io:443/foo/bar" aren't mistaken for tags ».
    """
    # >>> depart: rendre le digest s'il y en a un, sinon le tag du DERNIER segment
    #     return ""
    if "@" in identifiant:
        return identifiant[identifiant.rindex("@") + 1:]
    dernier = identifiant.rsplit(SEPARATEUR, 1)[-1]
    if ":" in dernier:
        return dernier[dernier.rindex(":") + 1:]
    return ""
    # <<<


def version_de_paquet(paquet: dict[str, Any]) -> str:
    """packageVersionOf : npm et pypi la portent, oci l'encode."""
    origine = paquet.get("origin")
    if not isinstance(origine, dict):
        return ""
    type_ = origine.get("type")
    if type_ in ("npm", "pypi"):
        sous = origine.get(type_)
        return (sous.get("version") or "") if isinstance(sous, dict) else ""
    if type_ == "oci":
        return version_depuis_identifiant_oci(origine.get("identifier") or "")
    return ""


def version(doc: Document) -> tuple[str, str]:
    """versionOf, et D'OU la valeur sort.

    La cascade amont :
        1. la version du paquet (npm/pypi explicite, oci depuis l'identifiant)
        2. sinon `metadata.tag`, s'il n'est ni vide ni « latest »
        3. sinon « 0.0.0 »

    Le second element rendu ici n'existe pas dans l'amont : c'est l'etage
    de la cascade. La fiche publiee, elle, ne dit pas lequel a repondu.
    """
    # >>> depart: derouler la cascade a trois etages — paquet, puis etiquette, puis repli
    #     return VERSION_DE_REPLI, "repli"
    source = doc.spec.get("source")
    if isinstance(source, dict) and isinstance(source.get("package"), dict):
        v = version_de_paquet(source["package"])
        if v:
            return v, "paquet"
    etiquette = doc.etiquette
    if etiquette and etiquette != ETIQUETTE_PAR_DEFAUT:
        return etiquette, "etiquette"
    return VERSION_DE_REPLI, "repli"
    # <<<


def description(doc: Document) -> tuple[str, str]:
    """descriptionOf : « The spec marks description as required, so fall back
    to the title and then a generated string when the source resource left it
    blank. »
    """
    spec = doc.spec
    if spec.get("description"):
        return spec["description"], "manifeste"
    if spec.get("title"):
        return spec["title"], "titre"
    return f"MCP server {doc.nom}", "genere"


def est_la_derniere(doc: Document) -> bool:
    """officialMetaOf : `isLatest` vaut vrai pour l'etiquette vide OU
    litterale « latest ». La liste par defaut ne sert que celle-la.
    """
    return doc.etiquette in ("", ETIQUETTE_PAR_DEFAUT)


def fiche(doc: Document) -> dict[str, Any]:
    """FromMCPServer, reduit aux champs que ce projet a verifies."""
    v, origine_v = version(doc)
    d, origine_d = description(doc)
    return {
        "name": nom_de_catalogue(doc.espace, doc.nom),
        "title": doc.spec.get("title") or "",
        "description": d,
        "version": v,
        "isLatest": est_la_derniere(doc),
        # Hors specification amont : la tracabilite que la fiche n'a pas.
        "_origine": {"version": origine_v, "description": origine_d},
    }
