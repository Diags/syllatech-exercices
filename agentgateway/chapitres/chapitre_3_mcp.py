"""Chapitre 3 — MCP Gateway : fédérer, et ce que la fédération renomme.

    uv run python chapitres/chapitre_3_mcp.py

Un endpoint, plusieurs serveurs : l'agent ne voit qu'un catalogue. La partie
que le support ne dit pas est celle qui casse les agents en production — ce
catalogue unique oblige à **renommer les outils**, et la règle de renommage
dépend du NOMBRE de cibles.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import schema_publie                              # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    CONFIGS, EXEMPLES_AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import TYPES_DE_CIBLE_MCP, charger          # noqa: E402


def noms_exposes(cibles: list[str], outils: dict[str, list[str]],
                 mode: str) -> list[str]:
    """Les noms d'outils qu'un agent voit, selon `prefixMode`.

    Transcrit des trois descriptions du schema (McpPrefixMode) :
      always      « Always prefix names, even with a single target. »
      conditional « Prefix names with the target name only when there are
                    multiple targets. »
      never       « Never prefix names; with multiple targets, calls are
                    routed by looking up which target serves the name.
                    Requires names to be unique across targets. »
    """
    plusieurs = len(cibles) > 1
    prefixer = mode == "always" or (mode == "conditional" and plusieurs)
    sorties = []
    for cible in cibles:
        for outil in outils.get(cible, []):
            sorties.append(f"{cible}_{outil}" if prefixer else outil)
    return sorties


def principal() -> None:
    utf8()

    titre(1, "LA CONFIGURATION DU SUPPORT, PASSEE AU SCHEMA")
    du_cours = charger(CONFIGS / "du-cours" / "ch3-mcp-federation.yaml")
    erreurs = schema_publie.verifier(du_cours)
    ligne("erreurs", str(len(erreurs)), 26)
    print()
    for chemin, message in erreurs:
        print(f"      {chemin}")
        print(f"        {message.split('  [dans')[0]}")
    print()
    for l in plier(
        "Deux cibles sur trois passent — les deux `stdio`. C'est la "
        "troisieme, celle qui derive des outils d'une API REST, qui est "
        "ecrite avec un champ qui n'existe pas."):
        print(f"   {l}")

    titre(2, "QUATRE FACONS D'ATTEINDRE UN SERVEUR MCP")
    cible = schema_publie.definitions()["LocalMcpTarget"]
    tableau(["branche", "ce qu'elle demande"],
            [[t, ", ".join(_champs(cible, t))] for t in TYPES_DE_CIBLE_MCP],
            [14, 60])
    print()
    ligne("champs communs a toutes",
          ", ".join(cible.get("properties", {})), 30)
    ligne("obligatoires", ", ".join(cible.get("required", [])), 30)
    print()
    for l in plier(
        "Les trois dernieres branches offrent deux facons d'atteindre l'hote "
        "— par son nom, ou par un `backend` declare ailleurs. Les champs "
        "ci-dessus sont donc une REUNION : il n'en faut pas la moitie."):
        print(f"   {l}")
    print()
    for l in plier(
        "`name` est obligatoire, et ce n'est pas de la decoration : c'est "
        "lui qui prefixe les noms d'outils, et c'est lui que `mcp.tool.target` "
        "rend a une regle d'autorisation. Le renommer renomme les outils."):
        print(f"   {l}")

    titre(3, "LA CIBLE `openapi`, TELLE QU'ELLE S'ECRIT VRAIMENT")
    print("   Ce que le support ecrit :\n")
    print("      openapi:")
    print("        url: https://api.jobportal.fr/openapi.json\n")
    print("   Ce que `amont/exemples/mcp-openapi.yaml` ecrit :\n")
    amont = charger(EXEMPLES_AMONT / "mcp-openapi.yaml")
    for nom, type_, corps in amont.cibles_mcp():
        for cle, valeur in corps.get(type_, {}).items():
            print(f"      {cle}: {valeur}")
    print()
    for l in plier(
        "La specification n'est pas RECUPEREE depuis une URL : elle est "
        "FOURNIE — un fichier ou un contenu en ligne — et l'hote de l'API est "
        "un champ a part. La difference compte : le proxy ne va pas chercher "
        "un document au demarrage, donc il ne depend pas de sa disponibilite, "
        "et la liste des outils qu'il expose ne change pas sans qu'on "
        "redeploie."):
        print(f"   {l}")

    titre(4, "LE PREFIXAGE, ET CE QU'IL CASSE")
    for mode in schema_publie.constantes("McpPrefixMode"):
        print(f"   {mode}")
        for l in plier(schema_publie.description("McpPrefixMode", mode), 60):
            print(f"        {l}")
    print()
    outils = {"offres": ["chercher", "lire"], "annuaire": ["verifier"]}
    print("   Un agent branche sur UNE cible, puis sur DEUX :\n")
    tableau(["prefixMode", "1 cible (offres)", "2 cibles"],
            [[mode,
              ", ".join(noms_exposes(["offres"], outils, mode)),
              ", ".join(noms_exposes(["offres", "annuaire"], outils, mode))]
             for mode in ("conditional", "always", "never")], [14, 30, 50])
    print()
    for l in plier(
        "La premiere ligne est le defaut, et c'est le piege : avec "
        "`conditional`, ajouter un second serveur RENOMME les outils du "
        "premier. Un agent qui appelait `chercher` appelle desormais un outil "
        "qui n'existe plus, et la configuration qui l'a casse ne mentionne "
        "meme pas son nom."):
        print(f"   {l}")
    print()
    for l in plier(
        "`always` coute deux mots de plus et ne bouge jamais. C'est ce que "
        "`configs/portail/01-mcp.yaml` pose, et c'est la seule ligne de ce "
        "fichier qui existe pour une raison qu'on ne voit pas en la lisant."):
        print(f"   {l}")

    titre(5, "CE QUI ARRIVE QUAND UNE CIBLE NE REPOND PAS")
    for valeur in schema_publie.constantes("McpBackendFailureMode"):
        ligne(f"  {valeur}",
              " ".join(schema_publie.description("McpBackendFailureMode",
                                                 valeur).split())[:58], 20)
    defaut = schema_publie.definitions()["LocalMcpBackend"]["properties"] \
        ["failureMode"]["description"]
    print()
    for l in plier(" ".join(defaut.split()), 62):
        print(f"   {l}")
    print()
    for l in plier(
        "Federer, c'est aussi mutualiser les pannes : par defaut, une cible "
        "qui n'initialise pas fait echouer tout le backend. C'est le bon "
        "choix — un catalogue incomplet est pire qu'un catalogue absent, "
        "parce que l'agent ne sait pas qu'il lui manque un outil."):
        print(f"   {l}")

    titre(6, "LE CATALOGUE DU PORTAIL")
    portail = charger(PORTAIL / "01-mcp.yaml")
    ligne("erreurs du schema", str(len(schema_publie.verifier(portail))), 30)
    print()
    tableau(["cible", "type", "ce qui la lance ou l'atteint"],
            [[nom, type_, _resume(type_, corps)]
             for nom, type_, corps in portail.cibles_mcp()], [16, 12, 48])
    print()
    backend = portail.routes()[0].backends[0]["mcp"]
    ligne("prefixMode", backend.get("prefixMode", "(defaut : conditional)"), 30)
    ligne("failureMode", backend.get("failureMode", "(defaut : failClosed)"), 30)
    print()
    for l in plier(
        "Trois cibles, trois mecanismes de distribution, un seul endpoint. "
        "C'est exactement la promesse du chapitre — et les deux lignes de "
        "reglage sous le tableau sont celles qui decident si elle tient dans "
        "six mois."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : A2A, et le routage d'inference.\n")


def _champs(definition: dict, branche: str) -> list[str]:
    """Les champs d'une branche, `anyOf` interne compris.

    Trois des quatre branches sont elles-memes un `anyOf` : on atteint
    l'hote par son nom, ou par un `backend` nomme. Les champs ne sont donc
    pas tous compatibles entre eux — on les REUNIT ici, sans pretendre
    qu'il faut les poser tous.
    """
    for b in definition.get("oneOf", []):
        if branche not in (b.get("required") or []):
            continue
        corps = b.get("properties", {}).get(branche, {})
        champs: dict[str, None] = {}
        for source in [corps, *corps.get("anyOf", [])]:
            for nom in source.get("properties", {}):
                champs[nom] = None
        return list(champs)
    return []


def _resume(type_: str, corps: dict) -> str:
    bloc = corps.get(type_, {})
    if type_ == "stdio":
        return f"{bloc.get('cmd', '')} {' '.join(bloc.get('args') or [])}"
    if type_ == "openapi":
        return f"host={bloc.get('host', '')}  schema={list(bloc.get('schema', {}))}"
    return str(bloc)[:46]


if __name__ == "__main__":
    principal()
