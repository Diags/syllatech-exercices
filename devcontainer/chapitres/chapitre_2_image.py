"""Chapitre 2 — Construire l'image : le contexte, et ce qu'il cache.

    uv run python chapitres/chapitre_2_image.py

`build.context` est relatif au **fichier**, pas au dépôt. Comme le fichier
vit dans `.devcontainer/`, la racine s'écrit `".."`. Écrire `"."` donne une
configuration parfaitement valide où le `pom.xml` n'existe pas — et le
message d'erreur parle de fichiers introuvables.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import chemins, schema_publie                      # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, PORTAIL, RACINE, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import charger                              # noqa: E402


def principal() -> None:
    utf8()
    portail = charger(PORTAIL / "devcontainer.json")
    fautif = charger(A_CORRIGER / "01-contexte-point.json")

    titre(1, "CE QUE LE SCHEMA DIT DU CHEMIN")
    construction = schema_publie.definitions()["buildOptions"]["properties"]
    dockerfile = schema_publie.definitions()["dockerfileContainer"]["oneOf"][0] \
        ["properties"]["build"]["allOf"][0]["properties"]["dockerfile"]
    for l in plier(" ".join(dockerfile["description"].split()), 62):
        print(f"      {l}")
    print()
    for champ in ("target", "cacheFrom", "args", "options"):
        if champ in construction:
            ligne(f"build.{champ}",
                  " ".join((construction[champ].get("description") or "").split()),
                  20)

    titre(2, "LES DEUX ECRITURES, RESOLUES")
    print("   Les deux fichiers sont lus comme s'ils etaient dans")
    print("   .devcontainer/ — c'est de la que partent les chemins.\n")
    tableau(["configuration", "context", "resolu vers", "pom.xml visible ?"],
            [[c.nom[:22], str(c.construction.get("context")),
              ("la racine du projet"
               if (PORTAIL / c.construction["context"]).resolve() == RACINE
               else ".devcontainer/"),
              "oui" if chemins.visible_dans_le_contexte(c, "pom.xml", PORTAIL)
              else "NON"]
             for c in (portail, fautif)], [24, 10, 22, 20])
    print()
    ligne("le schema refuse-t-il le fautif ?",
          "non — c'est une chaine bien formee" if
          schema_publie.valide(fautif) else "oui", 36)
    print()
    for l in plier(
        "Le contexte fautif EXISTE : `.devcontainer/` est un dossier bien "
        "reel. C'est ce qui rend l'erreur deroutante — Docker ne dit pas "
        "« mauvais contexte », il dit qu'il ne trouve pas `pom.xml`, et on va "
        "chercher du cote du Dockerfile."):
        print(f"   {l}")

    titre(3, "CE QUE LE CONTEXTE CONTIENT, DES DEUX COTES")
    for etiquette, dossier in [("context: \"..\"", RACINE),
                               ("context: \".\"", PORTAIL)]:
        contenu = sorted(p.name for p in dossier.iterdir()
                         if not p.name.startswith((".venv", "__pycache__")))
        ligne(etiquette, ", ".join(contenu[:7]) + ("…" if len(contenu) > 7 else ""), 16)
    print()
    for l in plier(
        "La seconde ligne est le dossier `.devcontainer/` : il contient le "
        "Dockerfile et la surcharge Compose, et rien du projet. Un `COPY "
        "pom.xml .` n'y trouve rien."):
        print(f"   {l}")

    titre(4, "LE DOCKERFILE MULTI-ETAPES, ET `build.target`")
    lignes = (PORTAIL / "Dockerfile").read_text(encoding="utf-8").splitlines()
    etapes = [l.split(" AS ")[-1] for l in lignes if " AS " in l]
    ligne("etapes du Dockerfile", ", ".join(etapes), 30)
    ligne("build.target du portail",
          str(portail.construction.get("target")), 30)
    print()
    for l in plier(
        "Une seule base, deux cibles : l'image de developpement est la meme "
        "que celle qui part en production, augmentee des outils. C'est ce qui "
        "evite la derive la plus couteuse — deux Dockerfile qui divergent en "
        "six mois, et un bogue qui n'existe qu'en production."):
        print(f"   {l}")

    titre(5, "CE QUI AGIT A LA CONSTRUCTION, ET CE QUI AGIT AU LANCEMENT")
    tableau(["propriete", "quand", "ce qu'elle fait"], [
        ["build.args", "construction", "des ARG du Dockerfile"],
        ["build.target", "construction", "quelle etape on s'arrete"],
        ["build.cacheFrom", "construction", "d'ou repart le cache"],
        ["runArgs", "LANCEMENT", "passe au moteur de conteneurs"],
        ["appPort", "LANCEMENT", "publie un port a l'hote"],
    ], [20, 16, 40])
    print()
    non_compose = schema_publie.definitions()["nonComposeBase"]["properties"]
    for champ in ("runArgs", "appPort"):
        ligne(f"  {champ}",
              " ".join((non_compose[champ].get("description") or "").split())[:56], 14)
    print()
    for l in plier(
        "La distinction n'est pas academique : changer `runArgs` ne "
        "reconstruit rien, et changer `build.args` ne sert a rien tant que "
        "l'image n'est pas reconstruite. Un « ca ne prend pas mes "
        "modifications » vient presque toujours de la."):
        print(f"   {l}")

    titre(6, "CE QUE LE VERIFICATEUR EN DIT")
    print("   $ uv run python outils/verifier_devcontainer.py \\")
    print("         configs/a-corriger/01-contexte-point.json --base .devcontainer\n")
    from outils.verifier_devcontainer import avertissements
    avis = avertissements(fautif, PORTAIL)
    for a in avis:
        for l in plier(a, 62):
            print(f"      {l}")
    print()
    for l in plier(
        "Cette ligne ne peut pas venir d'un schema : elle compare deux "
        "chemins et regarde le disque. C'est une moitie du travail qu'un "
        "`devcontainer.json` ne peut pas porter tout seul — l'autre moitie "
        "est le cycle de vie, au chapitre 4."):
        print(f"   {l}")
    print()
    for l in plier(
        "Noter ce que l'outil ne dit PAS : `build.dockerfile` vaut "
        "« Dockerfile », et il est bien la — a cote du `devcontainer.json`. "
        "Les deux chemins partent du meme endroit et designent des choses "
        "differentes, et c'est normal. C'est cela qui surprend."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : les Features, et leur ordre.\n")


if __name__ == "__main__":
    principal()
