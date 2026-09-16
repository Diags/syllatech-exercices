"""Chapitre 5 — Ports, utilisateurs, montages : et le nom d'une variable.

    uv run python chapitres/chapitre_5_ports.py

Quatre réglages du quotidien, et une règle de nommage que la spécification
donne en JavaScript — assez précisément pour qu'on puisse montrer que deux
options différentes produisent parfois **la même** variable d'environnement.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import features, options, schema_publie            # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import charger                              # noqa: E402


def principal() -> None:
    utf8()
    portail = charger(PORTAIL / "devcontainer.json")

    titre(1, "PUBLIER, ET SURTOUT ETIQUETER")
    ligne("forwardPorts",
          ", ".join(str(p) for p in portail.ports()), 24)
    tableau(["port", "label", "onAutoForward"],
            [[p, a.get("label", "(sans etiquette)"), a.get("onAutoForward", "(defaut)")]
             for p, a in sorted(portail.ports_etiquetes().items())], [10, 24, 20])
    print()
    non_etiquetes = [str(p) for p in portail.ports()
                     if str(p) not in portail.ports_etiquetes()]
    ligne("ports sans etiquette", ", ".join(non_etiquetes) or "aucun", 24)
    print()
    for l in plier(
        "Une liste de numeros ne se relit pas. Sur un projet a cinq services, "
        "`portsAttributes` est la difference entre « 8080, 5432, 6379, 9090, "
        "3000 » et cinq noms — et c'est une propriete que personne n'ecrit au "
        "premier jet."):
        print(f"   {l}")

    titre(2, "DEUX UTILISATEURS, ET UN ALIGNEMENT")
    for champ in ("containerUser", "remoteUser", "updateRemoteUserUID"):
        for l in plier(f"{champ} — {schema_publie.description(champ)}", 62):
            print(f"      {l}")
        print()
    ligne("le portail pose", f"remoteUser={portail.brut.get('remoteUser')}, "
          f"updateRemoteUserUID={portail.brut.get('updateRemoteUserUID')}", 22)
    print()
    for l in plier(
        "`containerUser` vaut pour TOUTES les operations ; `remoteUser` ne "
        "vaut que pour l'outil qui s'y connecte. Et sous Linux, "
        "`updateRemoteUserUID` est le remede au symptome le plus agacant : un "
        "fichier cree dans le conteneur qui appartient a root et devient "
        "illisible depuis la machine."):
        print(f"   {l}")

    titre(3, "CE QUE LES FEATURES SAVENT DE CES DEUX UTILISATEURS")
    variables = options.utilisateurs(portail.brut.get("remoteUser"),
                                     portail.brut.get("containerUser"))
    for nom, valeur in sorted(variables.items()):
        ligne(f"  {nom}", valeur, 24)
    print()
    phrase = next(l for l in (AMONT / "features-user-env-variables.md")
                  .read_text(encoding="utf-8").splitlines()
                  if "If no `remoteUser` is configured" in l)
    for l in plier(" ".join(phrase.split()), 62):
        print(f"      {l}")
    print()
    for l in plier(
        "Les scripts d'installation tournent en `root`. Sans ces quatre "
        "variables, une Feature ne saurait pas a qui doit appartenir le "
        "dossier qu'elle cree — et c'est exactement la panne de permissions "
        "du paragraphe precedent, vue de l'autre cote."):
        print(f"   {l}")

    titre(4, "LE NOM D'UNE VARIABLE D'OPTION")
    print("   La regle, telle que la specification l'ecrit :\n")
    print("      (str: string) => str")
    print(r"          .replace(/[^\w_]/g, '_')")
    print(r"          .replace(/^[\d_]+/g, '_')")
    print("          .toUpperCase();\n")
    essais = ["version", "installMaven", "jdk-distro", "my.option",
              "2fa", "22fa", "_prive", "__double", "a b"]
    tableau(["option", "variable", "pourquoi"],
            [[o, options.nom_de_variable(o),
              "suite de tete → UN souligne" if o[0].isdigit() or o[0] == "_"
              else ("non-mot → souligne" if not o.isalnum() else "majuscules")]
             for o in essais], [16, 18, 34])
    print()
    doublons = options.collisions(essais)
    for variable, sources in doublons.items():
        ligne(f"  collision sur {variable}",
              " et ".join(sources), 26)
    print()
    for l in plier(
        "La deuxieme substitution est celle qu'on lit mal : elle remplace "
        "TOUTE une suite de chiffres ou de soulignes en tete par UN SEUL "
        "souligne. `2fa` et `22fa` donnent donc la meme variable — une "
        "Feature qui declarerait les deux n'en verrait qu'une, et rien ne le "
        "signalerait."):
        print(f"   {l}")

    titre(5, "UNE OPTION OMISE EST EXPORTEE QUAND MEME")
    index = features.catalogue()
    java = index["ghcr.io/devcontainers/features/java"]
    passees = {"version": "21"}
    variables = options.env(java, passees)
    ligne("options declarees", str(len(java.get("options") or {})), 30)
    ligne("options passees", str(len(passees)), 30)
    ligne("variables ecrites dans le .env", str(len(variables)), 30)
    print()
    for nom, valeur in sorted(variables.items())[:5]:
        source = "← passee" if nom == "VERSION" else "(defaut declare)"
        ligne(f"  {nom}", f"{valeur:<14}{source}", 22)
    print("      …")
    print()
    mal = charger(A_CORRIGER / "10-option-inconnue.json")
    mauvaises = options.ignorees(java, mal.features[
        "ghcr.io/devcontainers/features/java:1"])
    ligne("le schema accepte le fichier fautif ?",
          "oui" if schema_publie.valide(mal) else "non", 40)
    ligne("options passees mais non declarees", ", ".join(mauvaises), 40)
    ligne("VERSION exportee malgre tout",
          options.env(java, mal.features[
              "ghcr.io/devcontainers/features/java:1"]).get("VERSION", ""), 40)
    print()
    for l in plier(
        "C'est la combinaison qui rend la faute invisible : l'option mal "
        "nommee n'est pas exportee, et la bonne l'est quand meme — avec sa "
        "valeur par defaut. Le conteneur se construit, la Feature s'installe, "
        "et la version demandee n'est pas celle qu'on obtient."):
        print(f"   {l}")

    titre(6, "MONTER LE CACHE, PAS LE DEPOT")
    for montage in portail.montages():
        for l in plier(str(montage), 62):
            print(f"      {l}")
    print()
    ligne("containerEnv", str(portail.brut.get("containerEnv")), 20)
    ligne("remoteEnv", str(portail.brut.get("remoteEnv")), 20)
    print()
    for l in plier(
        "`${localEnv:HOME}` est lu sur VOTRE machine au moment de composer le "
        "montage : c'est ce qui permet au meme fichier de marcher pour toute "
        "l'equipe. Et la distinction `containerEnv` / `remoteEnv` compte pour "
        "les secrets — une valeur dans `containerEnv` est visible de "
        "n'importe quel processus du conteneur, y compris ceux qu'on n'a pas "
        "lances."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : Compose, et l'equipe.\n")


if __name__ == "__main__":
    principal()
