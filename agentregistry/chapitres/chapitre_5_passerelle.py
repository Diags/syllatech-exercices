"""Chapitre 5 — AgentGateway : ce que le catalogue ne sait pas porter.

    uv run python chapitres/chapitre_5_passerelle.py

Le registre répond à « qu'existe-t-il, et dans quelle version ? ». Il ne
répond pas à « qui a le droit d'appeler quoi ? ». Ce chapitre ne décrit pas
agentgateway — il mesure **le trou que la passerelle vient combler**, dans le
schéma du registre lui-même : quels champs savent porter un secret, lequel
ne sait pas, et ce que valide réellement une URL de serveur.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import regles                                      # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    AMONT, CATALOGUE, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import Document, charger                 # noqa: E402
from jobportal.schema_publie import document as openapi           # noqa: E402
from jobportal.schema_publie import verifier as verifier_schema   # noqa: E402

PORTAIL = CATALOGUE / "portail"

BASE = {"apiVersion": "ar.dev/v1alpha1",
        "metadata": {"name": "annuaire-pro", "namespace": "default",
                     "tag": "stable"}}


def remote(**champs) -> Document:
    return Document({**BASE, "kind": "MCPServer", "spec": {"remote": champs}})


def type_du_champ(schema: str, champ: str) -> str:
    """Le type declare d'un champ, lu dans le document publie."""
    propriete = openapi()["components"]["schemas"][schema]["properties"][champ]
    if "$ref" in propriete:
        return propriete["$ref"].rsplit("/", 1)[-1]
    return propriete.get("type", "?")


def principal() -> None:
    utf8()

    titre(1, "CE QUE LE CATALOGUE SAIT D'UN SERVEUR, ET CE QU'IL IGNORE")
    tableau(["question", "champ du schema"], [
        ["ou est-il ?", "remote.url  /  source.package.origin.identifier"],
        ["comment lui parler ?", "remote.type  /  package.transport.type"],
        ["quelle version ?", "metadata.tag  /  origin.<type>.version"],
        ["qui peut l'appeler ?", "— aucun champ"],
        ["quels outils expose-t-il ?", "— aucun champ"],
        ["combien d'appels par minute ?", "— aucun champ"],
    ], [34, 48])
    print()
    for l in plier(
        "Les trois dernieres lignes ne sont pas des oublis : ce sont des "
        "questions d'EXECUTION, et le registre est un catalogue. Un catalogue "
        "qui repondrait a « qui peut appeler » devrait etre consulte a chaque "
        "appel — il deviendrait la passerelle."):
        print(f"   {l}")

    titre(2, "LES CHAMPS QUI SAVENT PORTER UN SECRET")
    tableau(["ou", "champ", "type declare"], [
        ["un depot git prive", "Repository.credentialsRef",
         type_du_champ("Repository", "credentialsRef")],
        ["un modele a cle", "ModelAuthConfig.secretRef",
         type_du_champ("ModelAuthConfig", "secretRef")],
        ["une CA privee", "ModelTLSConfig.caCertSecretRef",
         type_du_champ("ModelTLSConfig", "caCertSecretRef")],
        ["un en-tete de remote", "HTTPHeader.value",
         type_du_champ("HTTPHeader", "value")],
        ["une variable de paquet", "MCPKeyValueInput.value",
         type_du_champ("MCPKeyValueInput", "value")],
    ], [26, 34, 24])
    print()
    for l in plier(
        "Trois renvois vers un Secret, et deux chaines. La difference n'est "
        "pas cosmetique : un renvoi est un NOM, que le registre stocke et "
        "qu'il ne resout pas — « OSS stores SecretRef opaquely and never "
        "resolves it ». Une chaine, elle, est la valeur."):
        print(f"   {l}")

    titre(3, "CE QUE CELA DONNE SUR UN SERVEUR DISTANT")
    avec_jeton = remote(
        type="streamable-http", url="https://annuaire.exemple.test/mcp",
        headers=[{"name": "Authorization", "value": "Bearer sk-portail-7f3a"}])
    ligne("couche A — schema publie",
          f"{len(verifier_schema(avec_jeton))} erreur(s)", 34)
    ligne("couche B — validateur",
          f"{len(regles.verifier(avec_jeton))} erreur(s)", 34)
    print()
    print("   Le manifeste est accepte, et voici ce qui part au registre :\n")
    print("      remote:")
    print("        type: streamable-http")
    print("        url: https://annuaire.exemple.test/mcp")
    print("        headers:")
    print("          - name: Authorization")
    print("            value: Bearer sk-portail-7f3a")
    print()
    for l in plier(
        "Ce jeton est desormais dans le manifeste, donc dans git, et dans la "
        "base du registre. Le schema de reponse de `GET /v0/mcpservers` "
        "declare `headers[].value` comme une chaine : le CONTRAT autorise "
        "donc a le renvoyer."):
        print(f"   {l}")
    print()
    for l in plier(
        "⚠️ Ce que ce projet ne peut pas verifier : si l'implementation le "
        "renvoie vraiment. Il existe un point d'extension `Prepare` — « used "
        "to mutate the decoded object before persistence (e.g. strip "
        "sensitive spec fields) » — qu'une distribution peut utiliser pour "
        "l'effacer. Ce qui est certain tient au manifeste : la valeur est "
        "ecrite en clair dans le fichier qu'on versionne."):
        print(f"   {l}")
    print()
    for l in plier(
        "C'est exactement l'argument de la passerelle, pris par l'autre bout : "
        "il n'y a pas de bonne facon de mettre une authentification dans un "
        "catalogue. Il faut un point de passage a l'execution — et c'est "
        "agentgateway. Le commentaire du type le dit d'ailleurs : "
        "« remote headers carry only static name/value pairs - no "
        "templating »."):
        print(f"   {l}")

    titre(4, "L'ASYMETRIE QUI SURPREND")
    cas = [
        ("remote.url", "http://annuaire.interne:8080/mcp"),
        ("remote.url", "https://annuaire.exemple.test/mcp"),
    ]
    for champ, url in cas:
        doc = remote(type="streamable-http", url=url)
        ligne(f"{champ} = {url}",
              "accepte" if not regles.verifier(doc) else "REFUSE", 48)
    for icone in ["http://cdn.interne/i.svg", "https://cdn.test/i.svg"]:
        doc = Document({**BASE, "kind": "MCPServer", "spec": {
            "iconUrl": icone,
            "remote": {"type": "sse", "url": "https://x.test/mcp"}}})
        ligne(f"spec.iconUrl = {icone}",
              "accepte" if not regles.verifier(doc) else "REFUSE", 48)
    print()
    for l in plier(
        "L'URL de l'ICONE doit etre en https ; l'URL du SERVEUR MCP peut "
        "etre en http. Le validateur d'icone explique pourquoi il est strict "
        "— « a catalog UI renders the value as an image source: plain http:// "
        "is blocked as mixed content, and javascript:/data: would make the "
        "field an injection point » — et la raison est bonne."):
        print(f"   {l}")
    print()
    for l in plier(
        "Mais la consequence pratique reste celle-ci : le seul champ d'URL "
        "sur lequel le registre impose un chiffrement est celui d'une image "
        "decorative. L'adresse par laquelle transiteront les appels d'outils "
        "n'a, elle, qu'une seule exigence — un hote non vide."):
        print(f"   {l}")

    titre(5, "TROIS TRANSPORTS, ET CELUI QUI N'A PAS D'ADRESSE")
    tableau(["forme", "type", "a-t-il une URL ?"], [
        ["remote", "sse", "oui — spec.remote.url"],
        ["remote", "streamable-http", "oui — spec.remote.url"],
        ["paquet", "http", "non — un port, l'hote vient du deploiement"],
        ["paquet", "stdio", "AUCUNE — des tubes, pas un socket"],
    ], [12, 20, 46])
    print()
    for l in plier(
        "Un serveur `stdio` ne se met pas derriere un proxy : il n'a pas "
        "d'adresse. Ce qui lui en donne une, c'est le deploiement — et c'est "
        "ce que dit le README : « When you run `arctl apply -f "
        "deployment.yaml`, agentregistry automatically configures the "
        "gateway routing ». Le catalogue seul ne branche rien."):
        print(f"   {l}")
    print()
    for fichier, forme in [("mcp-annuaire", "remote"),
                           ("mcp-offres", "paquet stdio")]:
        doc = next(iter(charger(PORTAIL / f"{fichier}.yaml")))
        url = (doc.spec.get("remote") or {}).get("url")
        ligne(f"{doc.nom} ({forme})", url or "aucune URL dans le manifeste", 30)

    titre(6, "CE QUE LE PROJET NE PEUT PAS MONTRER")
    for limite in [
        "agentgateway n'est pas ici : c'est un autre binaire, un autre",
        "  depot, et le cours qui lui est consacre le traite ;",
        "aucun appel MCP ne circule : ce projet lit des manifestes, il",
        "  n'ouvre pas de connexion ;",
        "la configuration que `arctl configure` ecrit n'est pas reproduite —",
        "  elle depend de l'adresse de la passerelle deployee.",
    ]:
        print(f"   {limite}" if limite.startswith("  ") else f"   · {limite}")
    print()
    for l in plier(
        "Ce qui EST mesure tient en une phrase : dans le schema que le "
        "registre publie, il n'existe aucun champ pour dire qui peut appeler "
        "un serveur, et un seul endroit pour mettre un jeton — une chaine en "
        "clair. La passerelle n'est pas un confort d'architecture."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : la curation, et la version publiee.\n")


if __name__ == "__main__":
    principal()
