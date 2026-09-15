"""Ce que le catalogue PUBLIE pour vos serveurs MCP, et d'ou ca sort.

    uv run python outils/fiches.py catalogue/portail
    uv run python outils/fiches.py catalogue/a-corriger.yaml --detail

`GET /v0.1/servers` ne rend pas le manifeste : il rend une projection, et la
projection remplit `description` et `version` meme quand le manifeste les
laisse vides — la specification amont les declare obligatoires.

Cet outil affiche la fiche ET l'etage de la cascade qui a repondu. La vraie
fiche, elle, ne le dit pas : « 0.0.0 » et « 1.4.0 » s'y affichent de la meme
facon.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import vue_mcp                                    # noqa: E402
from jobportal.commun import utf8                                # noqa: E402
from jobportal.manifeste import charger, charger_dossier         # noqa: E402

LIBELLE = {
    "paquet": "le paquet",
    "etiquette": "metadata.tag",
    "repli": "⚠ un repli",
    "manifeste": "le manifeste",
    "titre": "spec.title",
    "genere": "⚠ genere",
}


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="La fiche publiee de chaque serveur MCP d'un catalogue.")
    a.add_argument("chemin", type=Path,
                   help="un fichier de manifestes, ou un dossier")
    a.add_argument("--detail", action="store_true",
                   help="afficher la fiche JSON complete")
    return a.parse_args(argv)


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    documents = (charger_dossier(args.chemin) if args.chemin.is_dir()
                 else list(charger(args.chemin)))
    serveurs = [d for d in documents if d.type == "MCPServer"]
    if not serveurs:
        print(f"{args.chemin} : aucun MCPServer")
        return 0

    replis = 0
    for doc in serveurs:
        f = vue_mcp.fiche(doc)
        origines = f.pop("_origine")
        print(f"\n{f['name']}")
        print(f"   version      {f['version']:<28} ← "
              f"{LIBELLE[origines['version']]}")
        print(f"   description  {f['description'][:28]:<28} ← "
              f"{LIBELLE[origines['description']]}")
        print(f"   isLatest     {str(f['isLatest']):<28} ← "
              f"metadata.tag = {doc.etiquette or '(absent)'!r}")
        if origines["version"] == "repli" or origines["description"] == "genere":
            replis += 1
        if args.detail:
            print("   " + json.dumps(f, ensure_ascii=False, indent=2)
                  .replace("\n", "\n   "))

    print(f"\n{len(serveurs)} serveur(s), {replis} dont au moins un champ "
          f"obligatoire vient d'un repli.")
    return replis


if __name__ == "__main__":
    raise SystemExit(principal())
