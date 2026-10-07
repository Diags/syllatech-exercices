"""Chapitre 2 — Les artefacts du registre, et leur nombre exact.

    uv run python chapitres/chapitre_2_artefacts.py

Le cours en annonce quatre. Le registre en enregistre neuf. Les deux sont
défendables, et la différence qui compte n'est pas le compte : c'est la
**sémantique de persistance**, qui décide si un artefact a des versions ou
seulement un état.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import lancement, regles, schema_publie           # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    AMONT, EXEMPLES_AMONT, ligne, plier, tableau, titre, utf8,
)
from jobportal.manifeste import (                                # noqa: E402
    ARTEFACT_ETIQUETE, ARTEFACTS_DU_COURS, TYPES, Document, charger,
)

BASE = {"apiVersion": "ar.dev/v1alpha1", "metadata": {"name": "offres",
                                                      "namespace": "default"}}


def serveur(source: dict) -> Document:
    return Document({**BASE, "kind": "MCPServer", "spec": {"source": source}})


def principal() -> None:
    utf8()

    titre(1, "QUATRE, OU NEUF ?")
    tableau(["kind", "persistance", "du cours ?", "ce que c'est"], [
        ["MCPServer", TYPES["MCPServer"], "oui", "des outils pour les agents"],
        ["Skill", TYPES["Skill"], "oui", "un savoir-faire, en depot git"],
        ["Agent", TYPES["Agent"], "oui", "une image + ses dependances"],
        ["Prompt", TYPES["Prompt"], "oui", "des instructions versionnees"],
        ["Model", TYPES["Model"], "non", "un modele et sa posture d'auth"],
        ["Plugin", TYPES["Plugin"], "non", "une extension de harnais"],
        ["Deployment", TYPES["Deployment"], "non", "une mise en service"],
        ["Runtime", TYPES["Runtime"], "non", "ou ca tourne"],
        ["Secret", TYPES["Secret"], "non", "du materiel d'authentification"],
    ], [13, 18, 12, 34])
    print()
    etiquetes = [t for t, s in TYPES.items() if s == ARTEFACT_ETIQUETE]
    ligne("types enregistres", str(len(TYPES)), 30)
    ligne("dont artefacts etiquetes", f"{len(etiquetes)} — {', '.join(sorted(etiquetes))}", 30)
    ligne("dont objets mutables",
          f"{len(TYPES) - len(etiquetes)} — "
          f"{', '.join(sorted(set(TYPES) - set(etiquetes)))}", 30)
    print()
    for l in plier(
        "Les quatre du cours sont bien les quatre qu'une EQUIPE publie. Mais "
        "Model et Plugin sont des artefacts etiquetes comme eux : ils ont des "
        "versions, on les epingle, ils se resolvent en « latest ». Les "
        "presenter comme de la plomberie fait rater que `Model/default@latest` "
        "est une dependance implicite de tout deploiement de harnais — le "
        "chapitre 4 y revient."):
        print(f"   {l}")

    titre(2, "CE QU'UN ARTEFACT DECLARE OBLIGATOIRE")
    print("   Lu dans amont/openapi.yaml, pas resume :\n")
    tableau(["kind", "champs de spec", "obligatoires"],
            [[t,
              str(len(schema_publie.document()["components"]["schemas"]
                      [f"{t}Spec"]["properties"])),
              ", ".join(schema_publie.requis(t, "spec")) or "(aucun)"]
             for t in [*ARTEFACTS_DU_COURS, "Model"]], [13, 18, 40])
    print()
    for l in plier(
        "Trois des cinq n'exigent RIEN. Un MCPServer sans source ni remote, "
        "un Skill sans depot, un Prompt sans contenu passent le contrat "
        "publie. Ce qui les refuse est ailleurs, et le chapitre 3 mesure "
        "exactement ou."):
        print(f"   {l}")

    titre(3, "DEUX AXES, ET LE COURS LES CONFOND")
    tableau(["axe", "champ", "valeurs"], [
        ["ou trouver le paquet", "source.package.origin.type",
         ", ".join(regles.ORIGINES)],
        ["comment lui parler", "source.package.transport.type",
         ", ".join(regles.TRANSPORTS_DE_PAQUET)],
        ["serveur deja en place", "remote.type", "sse, streamable-http"],
    ], [24, 34, 24])
    print()
    print("   Ce que le support de cours ecrit :\n")
    print("      spec:")
    print("        runtime: uvx              # ou npx, oci, http")
    print("        package: mcp-server-postgres")
    print("        transport: stdio          # ou sse, streamable-http")
    print()
    for l in plier(
        "Trois champs qui n'existent pas, et deux ensembles de valeurs "
        "melanges. `npx` et `uvx` ne sont pas des origines : ce sont les "
        "commandes que le resolveur DERIVE d'une origine npm ou pypi. La doc "
        "amont le dit en une phrase :"):
        print(f"   {l}")
    print()
    doc_cli = (AMONT / "declarative-cli.md").read_text(encoding="utf-8")
    phrase = next(p for p in doc_cli.split("\n\n") if "derives sensible" in p)
    for l in plier(phrase.replace("\n", " "), 66):
        print(f"      {l}")

    titre(4, "LE MEME SERVEUR, TROIS PACKAGINGS")
    paquets = {
        "npm": {"origin": {"type": "npm", "identifier": "@portail/mcp-offres",
                           "npm": {"version": "1.4.0",
                                   "serverName": "io.github.portail/offres"}},
                "transport": {"type": "stdio"}},
        "pypi": {"origin": {"type": "pypi", "identifier": "portail-mcp-offres",
                            "pypi": {"version": "1.4.0",
                                     "serverName": "io.github.portail/offres"}},
                 "transport": {"type": "stdio"}},
        "oci": {"origin": {"type": "oci",
                           "identifier": "ghcr.io/portail/mcp-offres:1.4.0",
                           "oci": {"serverName": "io.github.portail/offres"}},
                "transport": {"type": "stdio"}},
    }
    tableau(["origine", "valide ?", "ce qui serait lance"],
            [[nom,
              "oui" if not regles.verifier(serveur({"package": p})) else "NON",
              lancement.effective(p)[0]]
             for nom, p in paquets.items()], [12, 12, 48])
    print()
    for l in plier(
        "C'est cela, « normaliser » : la fiche du catalogue est la meme, le "
        "consommateur ne choisit pas une methode d'installation, et le "
        "resolveur derive la commande. Trois manifestes differents, une seule "
        "facon de les consommer."):
        print(f"   {l}")

    titre(5, "ET CE QUI ARRIVE QUAND ON DECLARE `launch` SOI-MEME")
    npm = paquets["npm"]
    avec = {**npm, "launch": {"command": "npx",
                              "args": [{"type": "named", "name": "--cache",
                                        "value": "/tmp/npm"}]}}
    ligne("sans launch", lancement.effective(npm)[0], 16)
    ligne("avec launch", lancement.effective(avec)[0], 16)
    print()
    for l in plier(
        "Le manifeste voulait seulement ajouter une option. « If Launch is "
        "set, the manifest owns Command and Args verbatim — no implicit "
        "identifier injection » : l'identifiant du paquet a disparu de la "
        "commande. Le serveur demarre, npx demande quoi lancer, et le "
        "manifeste reste parfaitement valide — aucune des trois couches du "
        "chapitre 3 ne regarde cela."):
        print(f"   {l}")

    titre(6, "LE MANIFESTE VALIDE LE PLUS COURT, PAR TYPE")
    minimaux = [
        ("MCPServer", {"source": {"package": {
            "origin": {"type": "oci", "identifier": "ghcr.io/p/o:1",
                       "oci": {"serverName": "io.p/o"}},
            "transport": {"type": "stdio"}}}},
         "une origine complete et un transport"),
        ("Skill", {}, "spec: {}"),
        ("Prompt", {}, "spec: {}"),
        ("Agent", {}, "spec: {}"),
        ("Model", {"provider": "bedrock",
                   "model": "us.anthropic.claude-opus-4-8"},
         "provider + model"),
    ]
    tableau(["kind", "le spec le plus court", "verdict"],
            [[type_, description,
              "valide" if not (regles.verifier(
                  doc := Document({**BASE, "kind": type_, "spec": spec}))
                  + [1] * len(schema_publie.verifier(doc)))
              else "refuse"]
             for type_, spec, description in minimaux], [13, 40, 12])
    print()
    for l in plier(
        "Un Skill, un Prompt et un Agent dont le `spec` est VIDE sont des "
        "artefacts valides du catalogue. Ils ont un nom, une etiquette, une "
        "fiche — et ne designent rien. C'est le point de depart du chapitre "
        "suivant : la validation dit si un manifeste est bien FORME, pas s'il "
        "sert a quelque chose."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : trois couches, et ce qu'elles ratent.\n")


if __name__ == "__main__":
    principal()
