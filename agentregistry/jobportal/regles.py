"""Couche B — les regles que le SERVEUR applique, transcrites.

Le schema publie (couche A) dit quelle forme a un manifeste. Il ne dit pas
tout : `pkg/api/v1alpha1/*_validate.go` ajoute une trentaine de regles que
l'OpenAPI ne peut pas exprimer — unions discriminees, exclusions mutuelles,
formats DNS-1123, dependances entre champs.

Ce module les transcrit, une par une, **avec la citation de l'endroit d'ou
elles sortent**. C'est la partie du projet qu'il faut savoir contredire :
elle modelise un programme Go qu'on ne fait pas tourner ici. Le garde-fou est
`tests/test_amont.py`, qui exige que les dix manifestes d'exemple du depot
passent, et le chapitre 3, qui dit ce que la transcription ne couvre pas.

Chaque fonction rend une liste d'`ErreurDeChamp` — la traduction de
`FieldErrors` : un chemin en points, et une cause. Une liste vide = valide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from jobportal.manifeste import (
    GROUPE_VERSION,
    Document,
    etiquetable,
)

# ─────────────────────────────────────────────────────────────────────────
# Les sentinelles de validation.go — reprises pour que le message dise de
# quelle FAMILLE de faute il s'agit, pas seulement laquelle.
# ─────────────────────────────────────────────────────────────────────────
CHAMP_REQUIS = "champ obligatoire absent"
FORMAT_INVALIDE = "format invalide"
ETIQUETTE_INVALIDE = "etiquette invalide"
URL_INVALIDE = "url invalide"
LIBELLE_INVALIDE = "libelle invalide"
REFERENCE_INVALIDE = "reference invalide"

# ─────────────────────────────────────────────────────────────────────────
# Les motifs, copies tels quels de pkg/api/v1alpha1/validation.go.
# Go compare avec MatchString sur un motif ancre ^…$ : sans (?m), `$` ne
# vaut qu'en fin de texte. L'equivalent Python exact est fullmatch, pas
# match — avec match, « nom\nmalveillant » passerait.
# ─────────────────────────────────────────────────────────────────────────
MOTIF_ESPACE = r"^[a-z0-9]([-a-z0-9.]{0,61}[a-z0-9])?$"
MOTIF_CLE_LIBELLE = (
    r"^([a-z0-9]([-a-z0-9.]{0,251}[a-z0-9])?/)?"
    r"[a-zA-Z0-9]([-a-zA-Z0-9._]{0,61}[a-zA-Z0-9])?$")
MOTIF_VALEUR_LIBELLE = r"^([a-zA-Z0-9]([-a-zA-Z0-9._]{0,61}[a-zA-Z0-9])?)?$"
MOTIF_ETIQUETTE = r"^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$"
MOTIF_DNS_1123 = (
    r"^[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?"
    r"(\.[a-z0-9]([-a-z0-9]{0,61}[a-z0-9])?)*$")
MOTIF_NOM_AMONT = r"^[a-zA-Z0-9._/-]+$"

LONGUEUR_MAX_DNS = 253
LONGUEUR_MIN_NOM_AMONT = 1
LONGUEUR_MAX_NOM_AMONT = 200

_ESPACE = re.compile(MOTIF_ESPACE)
_CLE_LIBELLE = re.compile(MOTIF_CLE_LIBELLE)
_VALEUR_LIBELLE = re.compile(MOTIF_VALEUR_LIBELLE)
_ETIQUETTE = re.compile(MOTIF_ETIQUETTE)
_DNS_1123 = re.compile(MOTIF_DNS_1123)
_NOM_AMONT = re.compile(MOTIF_NOM_AMONT)

# mcpserver.go : MCPTransport.Type — « "http" | "stdio" », et le validateur
# le dit deux fois (ensemble ferme). Ce ne sont PAS les valeurs d'un remote.
TRANSPORTS_DE_PAQUET = ("stdio", "http")

# mcpserver.go : MCPPackageOrigin.Type — le discriminant de l'union.
ORIGINES = ("npm", "pypi", "oci")

# agent.go : AgentProtocol.
PROTOCOLES = ("A2A", "HTTP", "OpenAIResponses")

# model_validate.go : KnownModelProviders — « Add a provider only after its
# runtime adapter and end-to-end coverage exist. » La valeur dit si le
# fournisseur sait s'authentifier par identite ambiante.
FOURNISSEURS_DE_MODELE = {"bedrock": True}

# model.go : les trois strategies d'authentification.
STRATEGIES = ("runtime", "secretRef", "passthrough")


@dataclass(frozen=True)
class ErreurDeChamp:
    """La traduction de FieldError : un chemin en points, et une cause."""

    chemin: str
    cause: str

    def __str__(self) -> str:
        return f"{self.chemin}: {self.cause}" if self.chemin else self.cause


def _ajouter(erreurs: list[ErreurDeChamp], chemin: str,
             cause: str | None) -> None:
    """FieldErrors.Append : une cause nulle ne fait rien."""
    if cause:
        erreurs.append(ErreurDeChamp(chemin, cause))


# ─────────────────────────────────────────────────────────────────────────
# Validateurs de champ partages — validation.go
# ─────────────────────────────────────────────────────────────────────────

def valider_nom(nom: str) -> str | None:
    """validateNameField : « the single source of truth for resource-name
    validation across the v1alpha1 surface — both metadata.name and ref.name ».
    """
    # >>> depart: refuser un nom vide, trop long, ou non conforme a MOTIF_DNS_1123
    #     return None
    if not nom:
        return CHAMP_REQUIS
    if len(nom) > LONGUEUR_MAX_DNS:
        return (f"{FORMAT_INVALIDE} : sous-domaine DNS-1123 "
                f"({LONGUEUR_MAX_DNS} car. max), recu {len(nom)}")
    if not _DNS_1123.fullmatch(nom):
        return (f"{FORMAT_INVALIDE} : sous-domaine DNS-1123 (minuscules, "
                f"chiffres, tirets et points ; commence et finit par un "
                f"alphanumerique) : {nom!r}")
    return None
    # <<<


def valider_etiquette(etiquette: str) -> str | None:
    """validateTag."""
    if not etiquette:
        return CHAMP_REQUIS
    if not _ETIQUETTE.fullmatch(etiquette):
        return f"{ETIQUETTE_INVALIDE} : doit correspondre a {MOTIF_ETIQUETTE}"
    return None


def valider_url_site(url: str) -> str | None:
    """validateWebsiteURL : facultatif ; si present, l'hote doit exister.

    ⚠️ Go utilise `net/url.Parse`, Python `urllib.parse.urlparse`. Les deux
    acceptent presque les memes chaines, mais pas exactement : c'est le seul
    endroit de ce module ou la transcription n'est pas mecanique. Le test
    `test_regles.py::test_url_sans_hote` fixe le comportement retenu.
    """
    if not url:
        return None
    try:
        decoupe = urlparse(url)
    except ValueError as erreur:                       # noqa: PERF203
        return f"{URL_INVALIDE} : {erreur}"
    if not decoupe.netloc:
        return f"{URL_INVALIDE} : hote vide"
    return None


def valider_url_icone(url: str) -> str | None:
    """validateIconURL.

    Le commentaire amont dit pourquoi l'ensemble est ferme : « a catalog UI
    renders the value as an image source: plain http:// is blocked as mixed
    content, and javascript:/data: would make the field an injection point. »
    """
    if not url:
        return None
    # « A single leading slash is a path on the UI's own origin. Two is a
    # scheme-relative reference to some other host. »
    if url.startswith("/") and not url.startswith("//"):
        return None
    try:
        decoupe = urlparse(url)
    except ValueError as erreur:                       # noqa: PERF203
        return f"{URL_INVALIDE} : {erreur}"
    if decoupe.scheme != "https" or not decoupe.netloc:
        return (f"{URL_INVALIDE} : une URL https:// absolue ou un chemin "
                f"relatif a la racine")
    return None


def valider_titre(titre: str) -> str | None:
    """validateTitle : facultatif ; interdit seulement le blanc pur."""
    if not titre:
        return None
    if not titre.strip():
        return f"{FORMAT_INVALIDE} : un titre ne peut pas etre vide de sens"
    return None


def valider_nom_amont(nom: str) -> str | None:
    """validateMCPPackageName : le format du catalogue MCP amont.

    « Matches the upstream modelcontextprotocol/registry server.json schema
    for the `name` field. » — c'est ce que le validateur de propriete compare
    au nom embarque dans l'artefact publie (label OCI
    `io.modelcontextprotocol.server.name`, `mcpName` npm, marqueur `mcp-name:`
    PyPI).
    """
    if not nom:
        return None                       # champ facultatif
    if not LONGUEUR_MIN_NOM_AMONT <= len(nom) <= LONGUEUR_MAX_NOM_AMONT:
        return (f"{FORMAT_INVALIDE} : serverName doit faire "
                f"{LONGUEUR_MIN_NOM_AMONT}-{LONGUEUR_MAX_NOM_AMONT} "
                f"caracteres, recu {len(nom)}")
    if not _NOM_AMONT.fullmatch(nom):
        return (f"{FORMAT_INVALIDE} : serverName doit suivre le motif amont "
                f"(p. ex. `io.github.user/server` ou `mon-mcp`) : {nom!r}")
    return None


def valider_depot(depot: Any, prefixe: str) -> list[ErreurDeChamp]:
    """validateRepository — commun a MCPServer, Skill et Agent."""
    erreurs: list[ErreurDeChamp] = []
    if depot is None:
        return erreurs
    if not isinstance(depot, dict):
        _ajouter(erreurs, prefixe, f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs
    ref = depot.get("credentialsRef")
    if isinstance(ref, dict):
        _ajouter(erreurs, f"{prefixe}.credentialsRef.name",
                 valider_nom(ref.get("name") or ""))
    url = depot.get("url") or ""
    if url:
        _ajouter(erreurs, f"{prefixe}.url", valider_url_site(url))
    else:
        # « branch requires repository.url » — une branche sans depot est une
        # precision sur rien, et le message le dit plutot que de l'ignorer.
        if depot.get("branch"):
            _ajouter(erreurs, f"{prefixe}.branch",
                     f"{FORMAT_INVALIDE} : branch exige repository.url")
        if depot.get("commit"):
            _ajouter(erreurs, f"{prefixe}.commit",
                     f"{FORMAT_INVALIDE} : commit exige repository.url")
    return erreurs


def valider_reference(ref: Any, prefixe: str,
                      types_admis: tuple[str, ...] = ()) -> list[ErreurDeChamp]:
    """validateRef : les controles STRUCTURELS d'une reference.

    Ce qui n'est pas ici : l'existence de la cible. Elle demande le registre,
    c'est `catalogue.resoudre`, et c'est la troisieme couche.
    """
    erreurs: list[ErreurDeChamp] = []
    if not isinstance(ref, dict):
        _ajouter(erreurs, prefixe, f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs
    type_ = ref.get("kind") or ""
    if not type_:
        _ajouter(erreurs, f"{prefixe}.kind", CHAMP_REQUIS)
    elif types_admis and type_ not in types_admis:
        _ajouter(erreurs, f"{prefixe}.kind",
                 f"{REFERENCE_INVALIDE} : le type {type_!r} n'est pas admis "
                 f"ici (attendu : {', '.join(types_admis)})")
    espace = ref.get("namespace") or ""
    if espace and not _ESPACE.fullmatch(espace):
        _ajouter(erreurs, f"{prefixe}.namespace",
                 f"{FORMAT_INVALIDE} : {espace!r}")
    _ajouter(erreurs, f"{prefixe}.name", valider_nom(ref.get("name") or ""))
    # « Tag is optional on content refs — blank means "resolve to latest". »
    etiquette = ref.get("tag") or ""
    if etiquette:
        if not etiquetable(type_):
            _ajouter(erreurs, f"{prefixe}.tag",
                     f"{REFERENCE_INVALIDE} : le type {type_!r} n'accepte pas "
                     f"d'epinglage par etiquette")
        else:
            _ajouter(erreurs, f"{prefixe}.tag", valider_etiquette(etiquette))
    return erreurs


def valider_metadonnees(doc: Document) -> list[ErreurDeChamp]:
    """ValidateObjectMeta.

    L'espace de noms est OBLIGATOIRE ici, alors qu'aucun manifeste d'exemple
    du depot n'en pose : le defaut est mis avant, a la frontiere d'apply
    (`Document.avec_defauts`). Valider le fichier tel qu'il est ecrit ne
    valide donc pas ce que le registre valide — le chapitre 3 le mesure.
    """
    erreurs: list[ErreurDeChamp] = []
    meta = doc.metadonnees
    espace = meta.get("namespace") or ""
    if not espace:
        _ajouter(erreurs, "metadata.namespace", CHAMP_REQUIS)
    elif not _ESPACE.fullmatch(espace):
        _ajouter(erreurs, "metadata.namespace",
                 f"{FORMAT_INVALIDE} : {espace!r}")
    _ajouter(erreurs, "metadata.name", valider_nom(meta.get("name") or ""))
    libelles = meta.get("labels") or {}
    if isinstance(libelles, dict):
        for cle, valeur in libelles.items():
            if not _CLE_LIBELLE.fullmatch(str(cle)):
                _ajouter(erreurs, f"metadata.labels[{cle}]",
                         f"{LIBELLE_INVALIDE} : cle {cle!r}")
            if not _VALEUR_LIBELLE.fullmatch(str(valeur)):
                _ajouter(erreurs, f"metadata.labels[{cle}]",
                         f"{LIBELLE_INVALIDE} : valeur {valeur!r}")
    return erreurs


# ─────────────────────────────────────────────────────────────────────────
# MCPServer — mcpserver_validate.go
# ─────────────────────────────────────────────────────────────────────────

def _valider_origine(origine: Any) -> list[ErreurDeChamp]:
    """validateMCPPackageOrigin : l'invariant de l'union discriminee.

    « exactly one of NPM/PyPI/OCI sub-structs is non-nil, matches Origin.Type,
    and carries a non-empty (and well-formed) ServerName. »
    """
    base = "spec.source.package.origin"
    erreurs: list[ErreurDeChamp] = []
    if not isinstance(origine, dict):
        _ajouter(erreurs, base, f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs

    type_ = origine.get("type") or ""
    if not type_:
        _ajouter(erreurs, f"{base}.type", CHAMP_REQUIS)
    if not origine.get("identifier"):
        _ajouter(erreurs, f"{base}.identifier", CHAMP_REQUIS)

    # >>> depart: faire respecter l'union discriminee — un seul sous-objet, et il doit correspondre a origin.type
    #     return erreurs
    poses = [n for n in ORIGINES if isinstance(origine.get(n), dict)]
    if not poses:
        _ajouter(erreurs, base, f"{CHAMP_REQUIS} : une de origin.npm, "
                                f"origin.pypi ou origin.oci")
        return erreurs
    if len(poses) > 1:
        _ajouter(erreurs, base, f"{REFERENCE_INVALIDE} : une SEULE de "
                                f"origin.npm, origin.pypi, origin.oci "
                                f"(posees : {', '.join(poses)})")
        return erreurs

    if not type_:
        return erreurs               # deja signale en CHAMP_REQUIS
    if type_ not in ORIGINES:
        _ajouter(erreurs, f"{base}.type",
                 f"{REFERENCE_INVALIDE} : type d'origine {type_!r} non "
                 f"supporte (attendu : {', '.join(repr(o) for o in ORIGINES)})")
        return erreurs

    sous = origine.get(type_)
    if not isinstance(sous, dict):
        _ajouter(erreurs, f"{base}.{type_}",
                 f"{CHAMP_REQUIS} : obligatoire quand origin.type vaut {type_!r}")
        return erreurs

    # npm et pypi portent leur version ; oci l'encode dans l'identifiant.
    if type_ in ("npm", "pypi") and not sous.get("version"):
        _ajouter(erreurs, f"{base}.{type_}.version", CHAMP_REQUIS)
    nom_amont = sous.get("serverName") or ""
    if not nom_amont:
        _ajouter(erreurs, f"{base}.{type_}.serverName", CHAMP_REQUIS)
    _ajouter(erreurs, f"{base}.{type_}.serverName", valider_nom_amont(nom_amont))
    return erreurs
    # <<<


def _valider_source_mcp(source: Any) -> list[ErreurDeChamp]:
    """validateMCPServerSource."""
    erreurs: list[ErreurDeChamp] = []
    if not isinstance(source, dict):
        _ajouter(erreurs, "spec.source",
                 f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs
    erreurs += valider_depot(source.get("repository"), "spec.source.repository")

    paquet = source.get("package")
    if paquet is None:
        # ⚠️ Le validateur amont sort ICI, sans rien dire. Un
        # `spec.source: {}` decrit donc un serveur dont on ne sait ni ou il
        # est, ni comment lui parler — et il est VALIDE. Le chapitre 3 le
        # compte parmi les trous.
        return erreurs
    if not isinstance(paquet, dict):
        _ajouter(erreurs, "spec.source.package",
                 f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs

    transport = paquet.get("transport")
    transport = transport if isinstance(transport, dict) else {}
    type_t = transport.get("type") or ""
    if not type_t:
        _ajouter(erreurs, "spec.source.package.transport.type", CHAMP_REQUIS)
    elif type_t not in TRANSPORTS_DE_PAQUET:
        _ajouter(erreurs, "spec.source.package.transport.type",
                 f"{REFERENCE_INVALIDE} : doit valoir \"stdio\" ou \"http\" "
                 f"(recu {type_t!r})")
    if type_t == "http" and not transport.get("port"):
        _ajouter(erreurs, "spec.source.package.transport.port",
                 f"{CHAMP_REQUIS} : obligatoire pour le transport http")

    erreurs += _valider_origine(paquet.get("origin"))
    return erreurs


def _valider_remote_mcp(remote: Any) -> list[ErreurDeChamp]:
    """validateMCPServerRemote."""
    erreurs: list[ErreurDeChamp] = []
    if not isinstance(remote, dict):
        _ajouter(erreurs, "spec.remote",
                 f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs
    if not remote.get("type"):
        _ajouter(erreurs, "spec.remote.type", CHAMP_REQUIS)
    url = remote.get("url") or ""
    if not url:
        _ajouter(erreurs, "spec.remote.url", CHAMP_REQUIS)
        return erreurs
    _ajouter(erreurs, "spec.remote.url", valider_url_site(url))
    return erreurs


def valider_mcpserver(doc: Document) -> list[ErreurDeChamp]:
    spec = doc.spec
    erreurs: list[ErreurDeChamp] = []
    _ajouter(erreurs, "spec.title", valider_titre(spec.get("title") or ""))
    _ajouter(erreurs, "spec.iconUrl", valider_url_icone(spec.get("iconUrl") or ""))

    source, remote = spec.get("source"), spec.get("remote")
    # >>> depart: exiger exactement un de spec.source et spec.remote, puis valider celui qui est pose
    #     if source is not None:
    #         erreurs += _valider_source_mcp(source)
    if source is None and remote is None:
        _ajouter(erreurs, "spec",
                 f"{CHAMP_REQUIS} : spec.source ou spec.remote")
    elif source is not None and remote is not None:
        _ajouter(erreurs, "spec",
                 f"{REFERENCE_INVALIDE} : spec.source et spec.remote "
                 f"s'excluent")
    elif source is not None:
        erreurs += _valider_source_mcp(source)
    else:
        erreurs += _valider_remote_mcp(remote)
    # <<<
    return erreurs


# ─────────────────────────────────────────────────────────────────────────
# Skill, Prompt — skill_validate.go, prompt_validate.go
# ─────────────────────────────────────────────────────────────────────────

def valider_skill(doc: Document) -> list[ErreurDeChamp]:
    spec = doc.spec
    erreurs: list[ErreurDeChamp] = []
    _ajouter(erreurs, "spec.title", valider_titre(spec.get("title") or ""))
    _ajouter(erreurs, "spec.iconUrl", valider_url_icone(spec.get("iconUrl") or ""))
    source = spec.get("source")
    if isinstance(source, dict):
        erreurs += valider_depot(source.get("repository"),
                                 "spec.source.repository")
    return erreurs


def valider_prompt(doc: Document) -> list[ErreurDeChamp]:
    """prompt_validate.go, verbatim dans son commentaire :

    « Content MAY be empty (a prompt can be purely descriptive), so we don't
    require it here. »

    Un Prompt sans contenu est donc valide. C'est un choix defendable ; c'est
    aussi le seul artefact dont le vide ne se voit nulle part.
    """
    erreurs: list[ErreurDeChamp] = []
    _ajouter(erreurs, "spec.iconUrl",
             valider_url_icone(doc.spec.get("iconUrl") or ""))
    return erreurs


# ─────────────────────────────────────────────────────────────────────────
# Agent — agent_validate.go
# ─────────────────────────────────────────────────────────────────────────

def _refs(spec: dict[str, Any], champ: str) -> list[Any]:
    valeur = spec.get(champ)
    return valeur if isinstance(valeur, list) else []


def valider_agent(doc: Document) -> list[ErreurDeChamp]:
    spec = doc.spec
    erreurs: list[ErreurDeChamp] = []
    _ajouter(erreurs, "spec.title", valider_titre(spec.get("title") or ""))
    _ajouter(erreurs, "spec.iconUrl", valider_url_icone(spec.get("iconUrl") or ""))

    source = spec.get("source")
    if isinstance(source, dict):
        erreurs += valider_depot(source.get("repository"),
                                 "spec.source.repository")
        protocole = source.get("protocol")
        if protocole is not None and protocole not in PROTOCOLES:
            _ajouter(erreurs, "spec.source.protocol",
                     f"{FORMAT_INVALIDE} : doit valoir "
                     f"{', '.join(repr(p) for p in PROTOCOLES)}, "
                     f"recu {protocole!r}")

    # validateHarnessCompatibility : type obligatoire, pas de doublon.
    vus: set[str] = set()
    for i, harnais in enumerate(_refs(spec, "compatibleHarnesses")):
        chemin = f"spec.compatibleHarnesses[{i}]"
        type_ = harnais.get("type") if isinstance(harnais, dict) else None
        if not type_:
            _ajouter(erreurs, f"{chemin}.type", CHAMP_REQUIS)
            continue
        if type_ in vus:
            _ajouter(erreurs, f"{chemin}.type",
                     f"{FORMAT_INVALIDE} : harnais {type_!r} en double")
            continue
        vus.add(type_)

    for champ, attendu in (("mcpServers", "MCPServer"), ("plugins", "Plugin"),
                           ("skills", "Skill")):
        for i, ref in enumerate(_refs(spec, champ)):
            chemin = f"spec.{champ}[{i}]"
            type_ = ref.get("kind") if isinstance(ref, dict) else None
            # « defaults an empty Kind to expectKind IN PLACE » : un kind
            # absent n'est pas une faute, c'est un defaut — mais un kind
            # PRESENT et different l'est.
            if type_ and type_ != attendu:
                _ajouter(erreurs, f"{chemin}.kind",
                         f"{REFERENCE_INVALIDE} : doit valoir {attendu!r}, "
                         f"recu {type_!r}")
            erreurs += valider_reference(
                {**ref, "kind": type_ or attendu} if isinstance(ref, dict)
                else ref, chemin)

    instructions = spec.get("instructions")
    if instructions is not None:
        type_ = instructions.get("kind") if isinstance(instructions, dict) else None
        if type_ and type_ != "Prompt":
            _ajouter(erreurs, "spec.instructions.kind",
                     f"{REFERENCE_INVALIDE} : doit valoir 'Prompt', "
                     f"recu {type_!r}")
        erreurs += valider_reference(
            {**instructions, "kind": type_ or "Prompt"}
            if isinstance(instructions, dict) else instructions,
            "spec.instructions")

    # « plugins/skills/instructions require compatibleHarnesses » — « a
    # prebuilt Image cannot consume injected files by itself ».
    compose = (_refs(spec, "plugins") or _refs(spec, "skills")
               or instructions is not None)
    if compose and not _refs(spec, "compatibleHarnesses"):
        _ajouter(erreurs, "spec",
                 f"{FORMAT_INVALIDE} : plugins/skills/instructions exigent "
                 f"compatibleHarnesses")
    return erreurs


# ─────────────────────────────────────────────────────────────────────────
# Model — model_validate.go
# ─────────────────────────────────────────────────────────────────────────

def _valider_ref_secret(ref: Any, chemin: str) -> list[ErreurDeChamp]:
    erreurs: list[ErreurDeChamp] = []
    if not isinstance(ref, dict):
        _ajouter(erreurs, chemin, f"{FORMAT_INVALIDE} : une table attendue")
        return erreurs
    _ajouter(erreurs, f"{chemin}.name", valider_nom(ref.get("name") or ""))
    espace = ref.get("namespace") or ""
    if espace and not _ESPACE.fullmatch(espace):
        _ajouter(erreurs, f"{chemin}.namespace",
                 f"{FORMAT_INVALIDE} : {espace!r}")
    return erreurs


def valider_model(doc: Document) -> list[ErreurDeChamp]:
    spec = doc.spec
    erreurs: list[ErreurDeChamp] = []
    _ajouter(erreurs, "spec.iconUrl", valider_url_icone(spec.get("iconUrl") or ""))

    fournisseur = spec.get("provider") or ""
    connu = fournisseur in FOURNISSEURS_DE_MODELE
    if not fournisseur:
        _ajouter(erreurs, "spec.provider", CHAMP_REQUIS)
    elif not connu:
        _ajouter(erreurs, "spec.provider",
                 f"{FORMAT_INVALIDE} : {fournisseur!r} (connus : "
                 f"{sorted(FOURNISSEURS_DE_MODELE)})")
    if not str(spec.get("model") or "").strip():
        _ajouter(erreurs, "spec.model", CHAMP_REQUIS)

    auth = spec.get("auth")
    strategie = ""
    if isinstance(auth, dict):
        strategie = auth.get("strategy") or ""
        secret = auth.get("secretRef")
        if strategie in ("runtime", "passthrough"):
            if secret is not None:
                _ajouter(erreurs, "spec.auth.secretRef",
                         f"{FORMAT_INVALIDE} : secretRef n'a de sens qu'avec "
                         f"la strategie 'secretRef'")
        elif strategie == "secretRef":
            if secret is None:
                _ajouter(erreurs, "spec.auth.secretRef",
                         f"{CHAMP_REQUIS} : exige par la strategie 'secretRef'")
            else:
                erreurs += _valider_ref_secret(secret, "spec.auth.secretRef")
        elif not strategie:
            _ajouter(erreurs, "spec.auth.strategy", CHAMP_REQUIS)
        else:
            _ajouter(erreurs, "spec.auth.strategy",
                     f"{FORMAT_INVALIDE} : {strategie!r} (attendu "
                     f"{', '.join(repr(s) for s in STRATEGIES)})")

    # « Omitted auth means the provider default: "runtime" for
    # ambient-identity providers; key-based providers must declare a strategy. »
    if connu:
        ambiante = FOURNISSEURS_DE_MODELE[fournisseur]
        if auth is None and not ambiante:
            _ajouter(erreurs, "spec.auth",
                     f"{CHAMP_REQUIS} : le fournisseur {fournisseur!r} exige "
                     f"une strategie explicite ('secretRef' ou 'passthrough')")
        elif strategie == "runtime" and not ambiante:
            _ajouter(erreurs, "spec.auth.strategy",
                     f"{FORMAT_INVALIDE} : 'runtime' n'est valable que pour "
                     f"les fournisseurs a identite ambiante")

    point = spec.get("endpoint")
    if isinstance(point, dict):
        tls = point.get("tls")
        if isinstance(tls, dict) and tls.get("caCertSecretRef") is not None:
            erreurs += _valider_ref_secret(tls["caCertSecretRef"],
                                           "spec.endpoint.tls.caCertSecretRef")
    return erreurs


# ─────────────────────────────────────────────────────────────────────────
# L'entree
# ─────────────────────────────────────────────────────────────────────────

PAR_TYPE = {
    "MCPServer": valider_mcpserver,
    "Skill": valider_skill,
    "Prompt": valider_prompt,
    "Agent": valider_agent,
    "Model": valider_model,
}


def verifier(doc: Document) -> list[ErreurDeChamp]:
    """Object.Validate() : les controles structurels, SANS entree/sortie.

    « No network I/O; ref existence is covered by ResolveRefs. » L'existence
    des cibles est la couche C.
    """
    erreurs: list[ErreurDeChamp] = []
    # Ce controle-ci n'est PAS dans Validate() : il est dans Scheme.Decode
    # (scheme.go), donc AVANT — « v1alpha1: unsupported apiVersion %q (want
    # %q) ». Un manifeste a la mauvaise apiVersion n'atteint jamais le
    # validateur de son type ; il est refuse au decodage. Le resultat est le
    # meme, l'etage ne l'est pas.
    if not doc.api:
        _ajouter(erreurs, "apiVersion", CHAMP_REQUIS)
    elif doc.api != GROUPE_VERSION:
        _ajouter(erreurs, "apiVersion",
                 f"{FORMAT_INVALIDE} : attendu {GROUPE_VERSION!r}, "
                 f"recu {doc.api!r}")
    if doc.type not in PAR_TYPE:
        _ajouter(erreurs, "kind",
                 f"{REFERENCE_INVALIDE} : aucun validateur pour {doc.type!r} "
                 f"(ce projet couvre {', '.join(sorted(PAR_TYPE))})")
        return erreurs
    erreurs += valider_metadonnees(doc)
    erreurs += PAR_TYPE[doc.type](doc)
    # « Tag is meaningful only for taggable registry artifacts. »
    if doc.etiquette and not etiquetable(doc.type):
        _ajouter(erreurs, "metadata.tag",
                 f"{REFERENCE_INVALIDE} : le type {doc.type!r} n'accepte pas "
                 f"d'etiquette")
    elif doc.etiquette:
        _ajouter(erreurs, "metadata.tag", valider_etiquette(doc.etiquette))
    return erreurs
