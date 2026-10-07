"""Une requête fictive, et les routes qui peuvent l'attraper.

    uv run python outils/essayer_route.py configs/portail/01-mcp.yaml /mcp/tools
    uv run python outils/essayer_route.py MON.yaml /v1/chat --methode POST \
        --entete "x-equipe: rh"

⚠️ Sous Git Bash (Windows), le shell réécrit un argument commençant par « / »
en chemin Windows : `/mcp/tools` devient `C:/Program Files/Git/mcp/tools`, et
plus aucune route ne correspond. Préfixer la commande de `MSYS_NO_PATHCONV=1`,
ou utiliser PowerShell. Ce n'est pas l'outil qui se trompe — c'est le shell
qui a modifié l'argument avant qu'il n'arrive.

⚠️ Cet outil ne désigne PAS de vainqueur quand plusieurs routes
correspondent. La règle de précédence d'agentgateway n'est écrite ni dans
`amont/config.schema.json`, ni dans les fichiers d'`amont/` : la deviner
ferait dire à cet outil une chose qu'il ne sait pas.

Ce qu'il fait à la place est ce dont on a besoin en relecture : il liste
**toutes** les candidates, et marque celles qui n'écrivent aucun `matches` —
celles-là attrapent tout, et rien dans le fichier ne le montre.

Code de sortie : 0 si exactement une route correspond, 1 sinon (aucune, ou
plusieurs). C'est ce qu'on veut en CI.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import utf8                                # noqa: E402
from jobportal.config import charger                             # noqa: E402
from jobportal.routage import Requete, candidates, route_correspond  # noqa: E402


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="Quelles routes d'une configuration peuvent attraper "
                    "cette requete ?")
    a.add_argument("fichier", type=Path)
    a.add_argument("chemin", help="le chemin, avec sa chaine de requete")
    a.add_argument("--methode", default="GET")
    a.add_argument("--entete", action="append", default=[],
                   metavar="NOM: VALEUR")
    a.add_argument("--hote", default="")
    return a.parse_args(argv)


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    entetes = {}
    for brut in args.entete:
        nom, _, valeur = brut.partition(":")
        entetes[nom.strip()] = valeur.strip()

    config = charger(args.fichier)
    requete = Requete(args.chemin, args.methode.upper(), entetes, args.hote)
    trouvees = candidates(config, requete)

    print(f"\n{args.fichier}")
    print(f"   requete  {requete}")
    print(f"   routes   {len(config.routes())} au total, "
          f"{len(trouvees)} candidate(s)\n")

    for candidate in trouvees:
        marque = "  ← n'ecrit aucun `matches`" if candidate.attrape_par_defaut else ""
        print(f"   PREND    {candidate.route.position()}  "
              f"« {candidate.route.nom} »{marque}")
        for backend in candidate.route.backends:
            type_ = config.type_de_backend(backend)
            print(f"            backend {type_}")
        if candidate.route.politiques:
            print(f"            politiques : "
                  f"{', '.join(sorted(candidate.route.politiques))}")

    prises = {c.route.position() for c in trouvees}
    for route in config.routes():
        if route.position() in prises:
            continue
        _, raisons = route_correspond(route, requete)
        print(f"   passe    {route.position()} — {raisons[0] if raisons else '?'}")

    print()
    if len(trouvees) == 1:
        print("   Une seule route correspond : la destination ne depend pas "
              "d'une regle\n   de precedence.")
        return 0
    if not trouvees:
        print("   Aucune route ne correspond. Le proxy repondra une erreur, "
              "pas un 404\n   du backend — la difference compte quand on "
              "cherche la panne.")
        return 1
    print("   PLUSIEURS routes correspondent. Laquelle gagne depend d'une "
          "regle de\n   precedence que ce projet ne reproduit pas : c'est "
          "exactement le genre\n   d'ambiguite qu'une configuration ne "
          "devrait pas contenir.")
    return 1


if __name__ == "__main__":
    raise SystemExit(principal())
