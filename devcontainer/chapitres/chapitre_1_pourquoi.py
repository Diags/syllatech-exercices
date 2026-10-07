"""Chapitre 1 — Ce qu'un dev container résout, et ce que le fichier est.

    uv run python chapitres/chapitre_1_pourquoi.py

Construire l'image demande Docker, et un cours ne peut pas l'exiger. Ce que
ce projet a, c'est **le schéma que la spécification publie** — celui que
votre éditeur applique — et les manifestes des Features officielles. Tout ce
qui suit se lit dans ces fichiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import jsonc, schema_publie                        # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, FEATURES_AMONT, PORTAIL, SCHEMA, ligne, plier, tableau,
    titre, utf8,
)
from jobportal.config import charger, depuis_texte              # noqa: E402


def _lisible(chemin) -> bool:
    """Le lecteur JSONC de ce projet vient-il a bout de ce fichier ?"""
    try:
        jsonc.charger(chemin)
        return True
    except Exception:                        # noqa: BLE001
        return False


def principal() -> None:
    utf8()

    titre(1, "CE QUI EST INSTALLE, ET CE QUI NE L'EST PAS")
    for quoi, etat in [
        ("Docker", "absent — ce projet ne construit aucune image"),
        ("le CLI `devcontainer`", "absent — c'est un paquet Node"),
        ("le schema publie", f"{SCHEMA.stat().st_size // 1024} Kio, ici"),
        ("les Features officielles",
         f"{len(list(FEATURES_AMONT.glob('*.json')))} manifestes, ici"),
        ("un vrai devcontainer.json", ".devcontainer/ de ce projet"),
    ]:
        ligne(quoi, etat, 26)
    print()
    for l in plier(
        "Ce projet ne construit rien : il lit des descriptions et applique "
        "leurs regles. C'est moins que ce qu'un dev container fait, et c'est "
        "exactement ce qu'on ne peut pas verifier en le lancant — parce que "
        "quand on le lance, on n'a qu'un message d'erreur."):
        print(f"   {l}")

    titre(2, "`devcontainer.json` N'EST PAS DU JSON")
    document = schema_publie.document()
    ligne("allowComments", str(document.get("allowComments")), 26)
    ligne("allowTrailingCommas", str(document.get("allowTrailingCommas")), 26)
    print()
    for l in plier(
        "Les deux cles ne disent pas la meme chose, et c'est la premiere "
        "surprise : les commentaires sont autorises, les virgules finales ne "
        "le sont PAS. La plupart des editeurs les tolerent quand meme — le "
        "fichier s'ouvre chez vous, et il est refuse ailleurs."):
        print(f"   {l}")
    print()
    print("   Ce que `json.load` fait de nos fichiers :\n")
    fichiers = [PORTAIL / "devcontainer.json", *sorted(A_CORRIGER.glob("*.json"))]
    strictes = sum(1 for f in fichiers
                   if jsonc.est_du_json_strict(f.read_text(encoding="utf-8")))
    ligne("fichiers du projet", str(len(fichiers)), 34)
    ligne("lisibles par `json.load`", str(strictes), 34)
    ligne("lisibles en JSONC",
          str(sum(1 for f in fichiers if _lisible(f))), 34)
    avec_virgule = [f.name for f in fichiers
                    if jsonc.virgules_finales(f.read_text(encoding="utf-8"))]
    ligne("avec une virgule finale",
          ", ".join(avec_virgule) or "aucun", 34)
    print()
    for l in plier(
        "Le schema le declare dans ses deux premieres cles, et pourtant "
        "c'est la panne la plus banale d'une CI qui veut relire ce fichier : "
        "le premier script qu'on ecrit appelle `json.load`, et il echoue sur "
        "un fichier que l'editeur ouvre sans broncher."):
        print(f"   {l}")
    print()
    print("   Le detail qui compte dans un lecteur JSONC :\n")
    piege = '{"image": "x", "postCreateCommand": "curl https://a.test//b"}'
    try:
        verdict = f"lu correctement : {jsonc.charger_texte(piege)['postCreateCommand']}"
    except Exception as erreur:              # noqa: BLE001
        verdict = f"ILLISIBLE — {type(erreur).__name__}"
    ligne("  une URL contient `//`", verdict, 34)
    print()
    for l in plier(
        "Un lecteur qui couperait bêtement a `//` amputerait cette URL et "
        "rendrait le fichier illisible. C'est pourquoi `jobportal/jsonc.py` "
        "tient un automate a trois etats plutot qu'un `split`."):
        print(f"   {l}")

    titre(3, "TROIS POINTS DE DEPART, ET UN `oneOf`")
    tableau(["propriete", "definition du schema", "exige aussi"], [
        ["image", "imageContainer", "rien"],
        ["build", "dockerfileContainer", "build.dockerfile"],
        ["dockerComposeFile", "composeContainer",
         ", ".join(schema_publie.definitions()["composeContainer"]["required"])],
    ], [22, 26, 34])
    print()
    for l in plier(
        "La troisieme ligne est celle qu'on oublie : en mode Compose, le "
        "schema exige TROIS proprietes, dont `workspaceFolder` — qui n'a pas "
        "d'equivalent obligatoire en mode image. Le chapitre 6 y revient."):
        print(f"   {l}")
    print()
    essais = [
        ('{"image": "x"}', "image seule"),
        ('{"build": {"dockerfile": "D"}}', "build seul"),
        ('{"image": "x", "build": {"dockerfile": "D"}}', "les deux"),
        ('{"name": "x"}', "aucun des trois"),
    ]
    tableau(["configuration", "le schema publie"],
            [[etiquette,
              "accepte" if schema_publie.valide(depuis_texte(texte))
              else "REFUSE"]
             for texte, etiquette in essais], [24, 20])

    titre(4, "UN VERDICT JUSTE, ET UN MESSAGE INUTILISABLE")
    croisee = depuis_texte('{"image": "x", "build": {"dockerfile": "D"}}')
    print("   Ce que `jsonschema` rend, tel quel :\n")
    for cible, message in schema_publie.erreurs_brutes(croisee)[:4]:
        print(f"      {cible} — {message[:64]}")
    print()
    print("   Ce que ce projet en fait :\n")
    for cible, message in schema_publie.verifier(croisee):
        print(f"      {cible} — {message}")
    print()
    for l in plier(
        "La racine du schema est un `oneOf` de deux branches, dont l'une "
        "contient un `oneOf` imbrique. Un fichier qui declare `image` ET "
        "`build` echoue donc contre TOUTES les branches, et le validateur "
        "remonte les reproches de la branche Compose — qui n'a rien a voir "
        "avec ce que l'auteur voulait ecrire."):
        print(f"   {l}")
    print()
    for l in plier(
        "⚠️ La seconde passe est une aide de CE projet, pas la "
        "specification : elle devine l'intention aux cles presentes, puis "
        "n'applique que la branche correspondante. Le verdict, lui, vient "
        "toujours du schema tel quel."):
        print(f"   {l}")

    titre(5, "LE DEV CONTAINER DE CE PROJET")
    portail = charger(PORTAIL / "devcontainer.json")
    ligne("nom", portail.nom, 26)
    ligne("point de depart", portail.depart, 26)
    ligne("Features demandees", str(len(portail.features)), 26)
    ligne("commandes du cycle de vie",
          ", ".join(portail.commandes_posees), 26)
    ligne("accepte par le schema ?",
          "oui" if schema_publie.valide(portail) else "NON", 26)
    print()
    for l in plier(
        "Ce fichier n'est pas une illustration : c'est le dev container de ce "
        "projet. Ouvrez `exemples/devcontainer/` dans un editeur qui les "
        "gere, et c'est lui qui se lance. Les six chapitres mesurent dessus."):
        print(f"   {l}")

    titre(6, "CE QUE LE PROJET VA MESURER")
    for quoi, ou in [
        ("`context: \".\"` — valide, et le pom.xml disparait", "chapitre 2"),
        ("l'ordre d'installation des Features, tour par tour", "chapitre 3"),
        ("ce qu'une dependance DURE tire, et ce qu'une MOLLE ne tire pas",
         "chapitre 3"),
        ("ce qui a fini quand on vous rend la main", "chapitre 4"),
        ("le tableau qui croit avoir un shell", "chapitre 4"),
        ("une option mal nommee, exportee quand meme — mais l'autre",
         "chapitre 5"),
        ("deux options differentes, une seule variable", "chapitre 5"),
        ("`stopCompose` la ou il faut `stopContainer`", "chapitre 6"),
    ]:
        print(f"   {quoi:<58}{ou}")

    print("\n   Au chapitre suivant : construire l'image.\n")


if __name__ == "__main__":
    principal()
