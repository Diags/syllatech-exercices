"""Dans quel ordre vos Features s'installeront — et pourquoi.

    uv run python outils/ordre_features.py .devcontainer/devcontainer.json
    uv run python outils/ordre_features.py MON.json --tours

C'est la question à laquelle aucun fichier ne répond en se relisant : deux
Features peuvent se gêner, l'ordre dépend d'un graphe qu'on ne voit pas, et
`overrideFeatureInstallOrder` ne peut pas contredire ce graphe.

L'algorithme est celui de `amont/feature-dependencies.md` — (B1) graphe,
(B2) `roundPriority`, (B3) tri par tours. `--tours` montre chaque tour :
c'est ce qui explique un ordre, et un ordre inexpliqué ne se corrige pas.

Code de sortie : 0 si l'ordre se résout, 1 si le graphe est circulaire.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import features, options                          # noqa: E402
from jobportal.commun import utf8                                # noqa: E402
from jobportal.config import charger                             # noqa: E402


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="Resout l'ordre d'installation des Features d'un "
                    "devcontainer.json.")
    a.add_argument("fichier", type=Path)
    a.add_argument("--tours", action="store_true",
                   help="detailler chaque tour de l'algorithme")
    a.add_argument("--env", action="store_true",
                   help="afficher le devcontainer-features.env de chaque "
                        "Feature")
    return a.parse_args(argv)


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    config = charger(args.fichier)
    demandees = config.features
    impose = config.ordre_impose

    print(f"\n{args.fichier}")
    print(f"   Features demandees : {len(demandees)}")
    for identifiant in demandees:
        print(f"      {identifiant}")
    if impose:
        print(f"   overrideFeatureInstallOrder : {len(impose)} entree(s)")
        for nom in impose:
            print(f"      {nom}")

    if not demandees:
        print("\n   Aucune Feature : rien a ordonner.")
        return 0

    index = features.catalogue()
    try:
        ordre, journal = features.resoudre(demandees, impose, index)
    except features.CycleDeDependances as erreur:
        print(f"\n   ERREUR : {erreur}")
        return 1

    tirees = [f for f in ordre if not f.demandee]
    print(f"\n   A installer : {len(ordre)}"
          + (f"   dont {len(tirees)} tiree(s) par `dependsOn` :"
             f" {', '.join(str(f) for f in tirees)}" if tirees else ""))
    print()
    for rang, feature in enumerate(ordre, 1):
        marque = "" if feature.demandee else "   ← tiree par dependsOn"
        priorite = f"   priorite {feature.priorite}" if feature.priorite else ""
        print(f"   {rang}. {str(feature):<28}{priorite}{marque}")

    if args.tours:
        print("\n   Les tours :")
        for tour in journal:
            candidates = ", ".join(str(f) for f in tour.candidates)
            retenues = ", ".join(str(f) for f in tour.retenues)
            print(f"      tour {tour.numero} — installables : {candidates}")
            print(f"               priorite max {tour.priorite_max} → "
                  f"retenues : {retenues}")

    if args.env:
        print("\n   devcontainer-features.env, par Feature :")
        for feature in ordre:
            passees = feature.options
            variables = options.env(feature.manifeste, passees)
            print(f"      {feature}")
            for nom, valeur in sorted(variables.items()):
                origine = "" if nom.lower().replace("_", "") in \
                    {c.lower().replace("_", "") for c in passees} else "   (defaut)"
                print(f"         {nom}={valeur}{origine}")
            if not variables:
                print("         (aucune option declaree)")

    return 0


if __name__ == "__main__":
    raise SystemExit(principal())
