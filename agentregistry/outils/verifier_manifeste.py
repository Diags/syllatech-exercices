"""Les trois couches sur un fichier de manifestes.

    uv run python outils/verifier_manifeste.py catalogue/a-corriger.yaml
    uv run python outils/verifier_manifeste.py MON.yaml --registre catalogue/portail

Sans `--registre`, la troisieme couche n'a rien a quoi comparer : les
references sont declarees NON VERIFIEES plutot que valides. C'est la
difference entre « je n'ai pas trouve d'erreur » et « il n'y en a pas », et
un outil qui les confond ment a son utilisateur.

Code de sortie : le nombre de documents refuses (0 si tout passe).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import regles, schema_publie                      # noqa: E402
from jobportal.catalogue import Catalogue                        # noqa: E402
from jobportal.commun import utf8                                # noqa: E402
from jobportal.manifeste import charger, charger_dossier         # noqa: E402


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="Valide des manifestes AgentRegistry en trois couches.")
    a.add_argument("fichiers", nargs="+", type=Path,
                   help="les fichiers de manifestes a verifier")
    a.add_argument("--registre", type=Path, default=None,
                   help="un dossier de manifestes a appliquer d'abord, pour "
                        "que les references aient une chance de resoudre")
    a.add_argument("--muet", action="store_true",
                   help="n'afficher que le compte final")
    return a.parse_args(argv)


def _peupler(dossier: Path) -> Catalogue:
    """Applique un dossier dans l'ordre des dependances, pas alphabetique.

    Un dossier n'a pas d'ordre ; `arctl apply -f` en a un (celui du
    document). On applique donc en deux passes : d'abord tout ce qui ne
    reference rien, ensuite le reste. Cela suffit pour un catalogue plat et
    cela evite de faire croire qu'un dossier se publie tout seul.
    """
    catalogue = Catalogue()
    documents = charger_dossier(dossier)
    feuilles = [d for d in documents if not catalogue.references_de(d)]
    autres = [d for d in documents if catalogue.references_de(d)]
    catalogue.appliquer_tous(feuilles + autres)
    return catalogue


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    catalogue = _peupler(args.registre) if args.registre else Catalogue()
    refuses = 0

    for chemin in args.fichiers:
        fichier = charger(chemin)
        if not args.muet:
            print(f"\n{chemin}  ({len(fichier)} document(s))")
        for doc in fichier:
            publie = schema_publie.verifier(doc)
            structure = regles.verifier(doc.avec_defauts())
            references = catalogue.resoudre(doc.avec_defauts()) \
                if args.registre else []
            total = len(publie) + len(structure) + len(references)
            if total:
                refuses += 1
            if args.muet:
                continue

            etiquette = f"{doc.type}/{doc.nom}" if doc.type else "(sans kind)"
            print(f"\n  {doc.rang}. {etiquette}")
            for chemin_, message in publie:
                print(f"     A schema publie   {chemin_}: {message}")
            for e in structure:
                print(f"     B validateur      {e}")
            for e in references:
                print(f"     C references      {e}")
            if not total:
                if args.registre:
                    print("     OK sur les trois couches")
                else:
                    print("     OK sur A et B — references NON VERIFIEES "
                          "(passer --registre)")

    print(f"\n{refuses} document(s) refuse(s)")
    return refuses


if __name__ == "__main__":
    raise SystemExit(principal())
