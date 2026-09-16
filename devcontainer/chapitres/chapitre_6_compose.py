"""Chapitre 6 — Compose, et l'équipe.

    uv run python chapitres/chapitre_6_compose.py

Dès qu'il y a une base de données, le dev container n'est plus qu'un service
parmi d'autres — et le schéma change de branche. Trois propriétés
obligatoires au lieu d'une, une valeur de `shutdownAction` qui n'est plus la
même, et des chemins qui partent toujours du fichier.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import chemins, schema_publie                      # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, FEATURES_AMONT, PORTAIL, RACINE, ligne, plier, tableau,
    titre, utf8,
)
from jobportal.config import charger, depuis_texte                # noqa: E402

COMPOSE = """{
  "name": "Portail de l'emploi — pile complete",
  "dockerComposeFile": ["../compose.yaml", "compose.dev.yaml"],
  "service": "app",
  "runServices": ["app", "db", "cache"],
  "workspaceFolder": "/workspaces",
  "shutdownAction": "stopCompose"
}"""

CROISEMENT = """{
  "dockerComposeFile": "c.yaml",
  "service": "app",
  "workspaceFolder": "/w",
  "workspaceMount": "source=..,target=/w,type=bind"
}"""


def principal() -> None:
    utf8()
    pile = depuis_texte(COMPOSE, PORTAIL / "devcontainer.json")

    titre(1, "LA BRANCHE COMPOSE EXIGE TROIS PROPRIETES")
    compose = schema_publie.definitions()["composeContainer"]
    ligne("obligatoires", ", ".join(compose["required"]), 26)
    ligne("facultatives",
          ", ".join(c for c in compose["properties"]
                    if c not in compose["required"]), 26)
    print()
    incomplet = charger(A_CORRIGER / "04-compose-incomplet.json")
    ligne("le fichier incomplet passe ?",
          "oui" if schema_publie.valide(incomplet) else "NON", 30)
    for cible, message in schema_publie.verifier(incomplet):
        print(f"      {cible} — {message}")
    print()
    for l in plier(
        "`workspaceFolder` n'a pas d'equivalent obligatoire en mode image : "
        "c'est la propriete qu'on oublie en passant a Compose. Et sa raison "
        "est simple — en mode Compose, le montage est decrit par le fichier "
        "Compose, donc l'outil ne peut pas deviner quel dossier ouvrir."):
        print(f"   {l}")

    titre(2, "LA MEME PROPRIETE, DEUX ENUMERATIONS")
    tableau(["branche", "shutdownAction accepte"],
            [["image / build",
              ", ".join(schema_publie.enum_de("nonComposeBase", "shutdownAction"))],
             ["dockerComposeFile",
              ", ".join(schema_publie.enum_de("composeContainer", "shutdownAction"))]],
            [22, 34])
    print()
    croise = charger(A_CORRIGER / "03-shutdown-croise.json")
    ligne("`stopCompose` sur une image",
          "accepte" if schema_publie.valide(croise) else "REFUSE", 30)
    for cible, message in schema_publie.verifier(croise):
        print(f"      {cible} — {message[:72]}")
    print()
    for l in plier(
        "Deux enumerations pour un meme nom de propriete : c'est le schema "
        "qui empeche d'ecrire une intention impossible — arreter une pile "
        "Compose quand il n'y en a pas. La verification a lieu au demarrage, "
        "pas au moment ou l'on ferme la fenetre."):
        print(f"   {l}")

    titre(3, "UNE LISTE ORDONNEE DE FICHIERS")
    ligne("dockerComposeFile", str(pile.fichiers_compose()), 24)
    print()
    tableau(["fichier", "resolu depuis .devcontainer/", "existe ?"],
            [[r.ecrit, str(r.resolu.relative_to(RACINE.parent)), r.verdict]
             for r in chemins.resoudre(pile, base=PORTAIL)], [24, 46, 14])
    print()
    for l in plier(
        "Le premier remonte d'un cran — c'est le fichier du projet ; le "
        "second est nu — c'est la surcharge, rangee a cote du "
        "`devcontainer.json`. Les deux chemins partent du meme endroit et "
        "s'ecrivent differemment, et c'est la meme regle qu'au chapitre 2."):
        print(f"   {l}")
    print()
    ligne("l'ordre compte", "chaque fichier complete le precedent", 24)

    titre(4, "CE QUI DEMARRE, ET CE A QUOI L'OUTIL SE CONNECTE")
    for champ in ("service", "runServices"):
        description = schema_publie.definitions()["composeContainer"] \
            ["properties"][champ].get("description", "")
        for l in plier(f"{champ} — {' '.join(description.split())}", 62):
            print(f"      {l}")
        print()
    services = [l.strip().rstrip(":")
                for l in (RACINE / "compose.yaml").read_text(encoding="utf-8")
                .splitlines()
                if l.startswith("  ") and not l.startswith("    ")
                and l.rstrip().endswith(":")]
    ligne("services du compose.yaml", ", ".join(services), 32)
    ligne("runServices demande",
          ", ".join(pile.brut.get("runServices", [])), 32)
    ligne("service ou l'outil se connecte", pile.brut.get("service", ""), 32)
    print()
    for l in plier(
        "Sans `runServices`, TOUS les services du Compose demarrent. Sur une "
        "pile a huit services dont trois ne servent qu'a l'integration, c'est "
        "plusieurs gigaoctets de memoire pour rien — et c'est le genre de "
        "reglage qu'on ajoute le jour ou la machine rame, pas le jour ou on "
        "ecrit le fichier."):
        print(f"   {l}")

    titre(5, "LES DEUX PROPRIETES VOISINES QU'ON CONFOND")
    for champ in ("workspaceMount", "workspaceFolder"):
        description = schema_publie.definitions()["nonComposeBase"] \
            ["properties"][champ].get("description", "")
        for l in plier(f"{champ} — {' '.join(description.split())}", 62):
            print(f"      {l}")
        print()
    for l in plier(
        "En mode Compose, seul `workspaceFolder` compte : le montage est "
        "decrit par le fichier Compose lui-meme. C'est d'ailleurs pourquoi "
        "`workspaceMount` n'existe que dans la branche non-Compose du "
        "schema — le poser a cote de `dockerComposeFile` serait refuse."):
        print(f"   {l}")
    print()
    croisement = depuis_texte(CROISEMENT)
    ligne("`workspaceMount` avec Compose",
          "accepte" if schema_publie.valide(croisement) else "REFUSE", 32)

    titre(6, "LA MEME DESCRIPTION, HORS DE L'EDITEUR")
    tableau(["ce qui lit le fichier", "ce qu'il en fait"], [
        ["un editeur", "ouvre le conteneur, lance postAttachCommand"],
        ["le CLI `devcontainer`", "rejoue la meme description, sans editeur"],
        ["ce projet", "applique les regles, ne construit rien"],
    ], [26, 46])
    print()
    for l in plier(
        "Le point qui en fait un outil d'equipe : la ligne de commande rejoue "
        "exactement cette description. C'est ce qui permet de faire tourner "
        "l'integration continue dans le meme environnement que les "
        "developpeurs — et de supprimer la derniere source d'ecart entre "
        "« chez moi » et « sur le serveur »."):
        print(f"   {l}")

    titre(7, "CE QUE CE PROJET NE PROUVE PAS")
    for limite in [
        "aucune image n'est construite : Docker est absent. Ce qui est",
        "  verifie n'est pas la construction, c'est ce que les chemins",
        "  DESIGNENT ;",
        "aucune Feature n'est installee : leurs `install.sh` ne tournent",
        "  pas. L'ordre est calcule, pas observe ;",
        "aucune commande du cycle de vie n'est executee : leur ordre et leur",
        "  frequence viennent du schema, pas d'une mesure ;",
        "les motifs de resolution de variables (localEnv, containerEnv) sont",
        "  affiches tels quels, pas substitues.",
    ]:
        print(f"   {limite}" if limite.startswith("  ") else f"   · {limite}")
    print()
    ligne("configurations du projet",
          str(len(list(A_CORRIGER.glob("*.json"))) + 1), 36)
    ligne("manifestes de Features officiels",
          str(len(list(FEATURES_AMONT.glob("*.json")))), 36)
    print()
    for l in plier(
        "Ce qui EST reel : `amont/devContainer.base.schema.json` est le "
        "schema que la specification publie, copie sans retouche, et la "
        "validation ne transcrit rien. L'algorithme d'ordre des Features est "
        "celui de `amont/feature-dependencies.md`, applique aux manifestes "
        "officiels. La regle de nommage des variables est celle de la "
        "specification, transcrite substitution par substitution."):
        print(f"   {l}")

    print("\n   uv run python outils/verifier_devcontainer.py VOTRE.json\n")


if __name__ == "__main__":
    principal()
