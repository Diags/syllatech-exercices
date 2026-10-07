"""Chapitre 3 — Les Features, et l'ordre qu'on ne voit pas.

    uv run python chapitres/chapitre_3_features.py

Deux Features peuvent se gêner, et rien dans le fichier ne dit dans quel
ordre elles s'installent. L'ordre vient d'un graphe — `dependsOn` dur et
récursif, `installsAfter` mou et non récursif — puis d'un tri par tours que
`amont/feature-dependencies.md` spécifie assez précisément pour être
implanté. Ce chapitre l'exécute sur les **vrais** manifestes officiels.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import features, options, schema_publie            # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, FEATURES_AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import charger                              # noqa: E402

G = "ghcr.io/devcontainers/features/"


def principal() -> None:
    utf8()
    index = features.catalogue()

    titre(1, "LE GRAPHE REEL DES FEATURES OFFICIELLES")
    avec_relations = [(nom, m) for nom, m in sorted(index.items())
                      if m.get("installsAfter") or m.get("dependsOn")]
    ligne("manifestes lus", str(len(index)), 30)
    ligne("avec au moins une relation", str(len(avec_relations)), 30)
    print()
    tableau(["Feature", "installsAfter (mou)", "dependsOn (dur)"],
            [[nom.rsplit("/", 1)[-1],
              ", ".join(x.rsplit("/", 1)[-1] for x in (m.get("installsAfter") or [])),
              ", ".join(x.rsplit("/", 1)[-1].split(":")[0]
                        for x in (m.get("dependsOn") or {}))]
             for nom, m in avec_relations
             if len(m.get("installsAfter") or []) > 1 or m.get("dependsOn")],
            [18, 34, 22])
    print()
    for l in plier(
        "Presque toutes declarent `installsAfter: [common-utils]` — c'est la "
        "Feature qui cree l'utilisateur non-root. Les quatre lignes "
        "ci-dessus sont les seules qui ajoutent autre chose, et ce sont "
        "celles sur lesquelles l'ordre se joue."):
        print(f"   {l}")

    titre(2, "MOU ET DUR : LA DIFFERENCE, MESUREE")
    for etiquette, demandees in [
        ("python + terraform", {f"{G}python:1": {}, f"{G}terraform:1": {}}),
        ("python + oryx + dotnet",
         {f"{G}python:1": {}, f"{G}oryx:1": {}, f"{G}dotnet:1": {}}),
    ]:
        ordre, journal = features.resoudre(demandees, [], index)
        tirees = [str(f) for f in ordre if not f.demandee]
        print(f"   {etiquette}")
        ligne("     demandees / installees",
              f"{len(demandees)} / {len(ordre)}", 28)
        ligne("     tirees par `dependsOn`", ", ".join(tirees) or "aucune", 28)
        ligne("     ordre", " → ".join(str(f) for f in ordre), 28)
        ligne("     tours", str(len(journal)), 28)
        print()
    for l in plier(
        "Le premier cas : `terraform` declare `dependsOn` sur `github-cli`, "
        "une dependance DURE et RECURSIVE — elle entre dans la file meme si "
        "personne ne l'a demandee. Deux Features demandees, trois installees."):
        print(f"   {l}")
    print()
    for l in plier(
        "Le second : `python` declare `installsAfter: [common-utils, oryx]`. "
        "Dans le premier cas, `oryx` n'etait pas dans la file — l'arete est "
        "donc RETIREE, et python s'installe au premier tour. Ici `oryx` est "
        "demande, l'arete compte, et l'ordre devient dotnet → oryx → python "
        "en trois tours. Les memes Features, un ordre different, parce qu'on "
        "en a ajoute une."):
        print(f"   {l}")

    titre(3, "L'ORDRE IMPOSE, ET CE QU'IL NE PEUT PAS FAIRE")
    base = {f"{G}github-cli:1": {}, f"{G}git:1": {},
            f"{G}node:1": {}, f"{G}common-utils:2": {}}
    for etiquette, impose in [
        ("sans overrideFeatureInstallOrder", []),
        ("node impose en tete", [f"{G}node"]),
        ("github-cli impose en tete", [f"{G}github-cli"]),
    ]:
        ordre, journal = features.resoudre(base, impose, index)
        ligne(etiquette, " → ".join(str(f) for f in ordre), 34)
    print()
    for l in plier(
        "La derniere ligne est celle qui apprend quelque chose : imposer "
        "`github-cli` en tete ne le fait PAS passer devant `git`. La priorite "
        "n'agit qu'a l'interieur d'un tour, et `github-cli` declare "
        "`installsAfter: [common-utils, git]` — il ne devient installable "
        "qu'apres eux. « Elle ne peut pas contredire le graphe de "
        "dependances resolu. »"):
        print(f"   {l}")

    titre(4, "LE MEME CONSTAT, SUR UNE DEPENDANCE DURE")
    impossible = charger(A_CORRIGER / "11-ordre-impossible.json")
    ligne("le schema accepte ?",
          "oui" if schema_publie.valide(impossible) else "non", 30)
    ligne("ordre impose",
          " puis ".join(x.rsplit("/", 1)[-1] for x in impossible.ordre_impose), 30)
    ordre, journal = features.resoudre(impossible.features,
                                       impossible.ordre_impose, index)
    ligne("ordre reel", " → ".join(str(f) for f in ordre), 30)
    print()
    for tour in journal:
        ligne(f"  tour {tour.numero}",
              f"installables : {', '.join(str(f) for f in tour.candidates)}"
              f"   priorite max {tour.priorite_max}", 12)
    print()
    for l in plier(
        "L'auteur demande terraform AVANT github-cli. Le graphe dit "
        "l'inverse, et il gagne : au premier tour, terraform n'est pas "
        "installable du tout, quelle que soit sa priorite. L'ordre impose "
        "n'a strictement aucun effet ici — et rien ne le signale."):
        print(f"   {l}")
    print()
    for l in plier(
        "Et il y a plus surprenant dans cette ligne : `github-cli` apparait "
        "DEUX FOIS. L'auteur le demande sans options ; terraform le tire avec "
        "`{version: latest}`. Or l'egalite de deux Features compte les "
        "options — « the options executed against the Feature are equal » — "
        "donc ce sont deux Features distinctes, et elles s'installent toutes "
        "les deux."):
        print(f"   {l}")
    print()
    for l in plier(
        "Ce n'est pas un bogue de ce projet : la specification prevoit le "
        "cas en toutes lettres pour les auteurs de Features — « Features "
        "that require updating shared state in the container (e.g. updating "
        "the $PATH), should be aware that the same Feature may be run "
        "multiple times. » Le remede cote utilisateur tient en un mot : "
        "passer la MEME option que la dependance, ou ne pas demander la "
        "Feature du tout."):
        print(f"   {l}")
    print()
    doublons = {}
    for f in ordre:
        doublons.setdefault(f.qualifie, []).append(f)
    for nom, liste in doublons.items():
        if len(liste) > 1:
            ligne(f"  {nom.rsplit('/', 1)[-1]} installe",
                  f"{len(liste)} fois — options "
                  f"{', '.join(str(f.options) for f in liste)}", 24)

    titre(5, "LE CATALOGUE DU PORTAIL")
    portail = charger(PORTAIL / "devcontainer.json")
    ordre, journal = features.resoudre(portail.features,
                                       portail.ordre_impose, index)
    tableau(["rang", "Feature", "tour", "pourquoi ce tour"],
            [[str(rang), str(f),
              str(next((t.numero for t in journal if f in t.retenues), "?")),
              ", ".join(sorted(
                  {features.nom_qualifie(x).rsplit("/", 1)[-1]
                   for x in f.molles}
                  & {g.qualifie.rsplit("/", 1)[-1] for g in ordre})) or "rien avant lui"]
             for rang, f in enumerate(ordre, 1)], [7, 34, 7, 30])
    print()
    for l in plier(
        "Trois Features au meme tour : elles n'ont aucune raison de "
        "s'attendre, et un outil qui les installerait en parallele le "
        "pourrait. L'ordre entre elles vient du Round Stable Sort — "
        "alphabetique — et non d'une contrainte : s'y fier serait une erreur."):
        print(f"   {l}")

    titre(6, "LES OPTIONS DEVIENNENT DES VARIABLES")
    java = index[f"{G}java"]
    passees = portail.features[f"{G}java:1"]
    variables = options.env(java, passees)
    ligne("options declarees par la Feature",
          str(len(java.get("options") or {})), 36)
    ligne("options passees par le portail", str(len(passees)), 36)
    ligne("variables exportees", str(len(variables)), 36)
    print()
    for nom, valeur in sorted(variables.items())[:6]:
        origine = "  ← passee" if nom == "VERSION" else "  (defaut)"
        ligne(f"  {nom}", f"{valeur}{origine}", 24)
    print("      …")
    print()
    for l in plier(
        "Une option omise est exportee QUAND MEME, avec la valeur par defaut "
        "que la Feature declare. C'est ce qui permet a un `install.sh` de "
        "lire ses variables sans tester leur existence — et c'est aussi "
        "pourquoi une faute de frappe dans un nom d'option ne se voit pas : "
        "la variable attendue existe, avec sa valeur par defaut."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : le cycle de vie.\n")


if __name__ == "__main__":
    principal()
