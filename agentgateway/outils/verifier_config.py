"""Votre `config.yaml`, contre le schéma que le proxy publie.

    uv run python outils/verifier_config.py configs/portail/01-mcp.yaml
    uv run python outils/verifier_config.py configs/du-cours/*.yaml
    uv run python outils/verifier_config.py MON.yaml --brut

Ce que fait cet outil, `agentgateway --file` le fait aussi — au démarrage,
et en refusant de démarrer. L'avantage de le faire ici : ça tient dans une
CI, ça ne demande ni Docker ni backends, et les messages sont lisibles.

`--brut` montre les erreurs telles que `jsonschema` les produit. C'est
instructif une fois : un backend mal écrit en produit une trentaine, parce
qu'il échoue contre les dix branches de `LocalRouteBackend`.

Code de sortie : le nombre de fichiers refusés.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import schema_publie                              # noqa: E402
from jobportal.commun import utf8                                # noqa: E402
from jobportal.config import charger                             # noqa: E402
from jobportal.gardes import builtins_inconnus, gardes_de        # noqa: E402
from jobportal.routage import routes_fourre_tout                 # noqa: E402


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="Valide une configuration agentgateway contre le schema "
                    "publie, puis signale ce que le schema ne peut pas voir.")
    a.add_argument("fichiers", nargs="+", type=Path)
    a.add_argument("--brut", action="store_true",
                   help="les erreurs non resumees, telles que jsonschema les rend")
    a.add_argument("--muet", action="store_true")
    return a.parse_args(argv)


def avertissements(config) -> list[str]:
    """Ce qui est VALIDE et mérite quand même d'être dit.

    Trois choses qu'un schéma ne peut pas exprimer, et qui coûtent cher :
    une route sans `matches` attrape tout, un `jwtAuth` sans `mode` accepte
    les requêtes sans jeton, un garde `regex` sans `action` masque au lieu
    de refuser.
    """
    dits = []
    for route in routes_fourre_tout(config):
        dits.append(f"{route.position()} n'ecrit aucun `matches` : elle "
                    f"attrape tout (defaut `pathPrefix: /`)")
    for route in config.routes():
        jwt = route.politiques.get("jwtAuth")
        if isinstance(jwt, dict) and "mode" not in jwt:
            dits.append(f"{route.position()} pose `jwtAuth` sans `mode` : le "
                        f"defaut est `optional`, qui accepte une requete SANS "
                        f"jeton")
        for entree in gardes_de(route.politiques):
            bloc = entree.get("regex")
            if isinstance(bloc, dict):
                if "action" not in bloc:
                    dits.append(f"{route.position()} pose un garde `regex` "
                                f"sans `action` : le defaut est `mask`, pas "
                                f"`reject`")
                inconnus = builtins_inconnus(bloc.get("rules") or [])
                if inconnus:
                    dits.append(f"{route.position()} : builtin inconnu "
                                f"{', '.join(inconnus)}")
    return dits


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    refuses = 0

    for chemin in args.fichiers:
        config = charger(chemin)
        erreurs = schema_publie.verifier(config, resumer=not args.brut)
        if erreurs:
            refuses += 1
        if args.muet:
            continue
        print(f"\n{chemin}")
        ligne = f"   sections : {', '.join(config.sections) or '(aucune)'}"
        if config.sections_inconnues:
            ligne += f"   INCONNUES : {', '.join(config.sections_inconnues)}"
        print(ligne)
        print(f"   ports    : {', '.join(str(p) for p in config.ports()) or '(aucun)'}"
              f"   routes : {len(config.routes())}")
        for cible, message in erreurs:
            print(f"   REFUS  {cible}")
            print(f"          {message}")
        for avis in avertissements(config):
            print(f"   ⚠  {avis}")
        if not erreurs:
            print("   le schema publie accepte cette configuration")

    print(f"\n{refuses} fichier(s) refuse(s) sur {len(args.fichiers)}")
    return refuses


if __name__ == "__main__":
    raise SystemExit(principal())
