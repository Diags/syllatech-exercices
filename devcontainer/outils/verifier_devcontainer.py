"""Votre `devcontainer.json`, contre le schéma publié — et au-delà.

    uv run python outils/verifier_devcontainer.py .devcontainer/devcontainer.json
    uv run python outils/verifier_devcontainer.py configs/a-corriger/*.json
    uv run python outils/verifier_devcontainer.py MON.json --brut

La première moitié de ce que fait l'outil, l'éditeur la fait déjà : appliquer
le schéma. La seconde est celle qui manque partout — sept avertissements que
le schéma **ne peut pas** exprimer, parce qu'ils portent sur des fichiers
qui existent ou non, sur des habitudes, ou sur le sens d'une valeur
parfaitement typée.

Code de sortie : le nombre de fichiers refusés par le schéma. Les
avertissements ne comptent pas — une configuration correcte ne doit pas
faire échouer une CI parce qu'elle mérite un commentaire.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import chemins, cycle, features, options, schema_publie  # noqa: E402
from jobportal.commun import utf8                                 # noqa: E402
from jobportal.config import Config, charger                      # noqa: E402
from jobportal.jsonc import (                                     # noqa: E402
    est_du_json_strict, virgules_finales,
)


def analyser(argv: list[str] | None = None) -> argparse.Namespace:
    a = argparse.ArgumentParser(
        description="Valide un devcontainer.json contre le schema publie, "
                    "puis signale ce que le schema ne peut pas voir.")
    a.add_argument("fichiers", nargs="+", type=Path)
    a.add_argument("--base", type=Path, default=None,
                   help="le dossier depuis lequel resoudre les chemins "
                        "relatifs, si le fichier n'est pas a sa place")
    a.add_argument("--brut", action="store_true",
                   help="les erreurs de `jsonschema` sans tri — instructif "
                        "une fois")
    a.add_argument("--muet", action="store_true")
    return a.parse_args(argv)


def avertissements(config: Config, base: Path | None = None) -> list[str]:
    """Ce qui est VALIDE et mérite quand même d'être dit."""
    dits: list[str] = []

    contexte = chemins.contexte_est_la_racine(config, base)
    if contexte is False:
        ecrit = config.construction.get("context")
        dits.append(f"build.context vaut {ecrit!r} : il ne remonte pas d'un "
                    f"cran, donc il ne designe pas la racine du depot")
    for resolution in chemins.manquants(config, base=base):
        dits.append(f"{resolution.propriete} designe {resolution.ecrit!r} — "
                    f"introuvable depuis le dossier du fichier")

    if cycle.tout_dans_post_create(config):
        dits.append("les trois commandes de creation sont reduites a "
                    "`postCreateCommand` : rien ne peut se preconstruire")
    apres = cycle.creation_apres_la_main(config)
    if apres:
        dits.append(f"vous aurez la main avant la fin de : {', '.join(apres)} "
                    f"(waitFor = {config.attend}"
                    f"{'' if config.attend_est_ecrit else ', par defaut'})")
    par_onglet = cycle.cout_par_onglet(config)
    if par_onglet:
        dits.append(f"{', '.join(par_onglet)} se rejoue a CHAQUE connexion "
                    f"d'un outil — un onglet de terminal compte")
    for nom in config.commandes_posees:
        pieges = cycle.piege_de_shell(config.commande(nom))
        if pieges:
            dits.append(f"{nom} est un tableau — donc SANS shell : "
                        f"{', '.join(pieges)} y sont des arguments litteraux")

    index = features.catalogue()
    if config.features:
        try:
            ordre, _ = features.resoudre(config.features, config.ordre_impose,
                                         index)
        except features.CycleDeDependances as erreur:
            dits.append(f"les Features ne s'ordonnent pas : {erreur}")
            ordre = []
        compte: dict[str, list] = {}
        for feature in ordre:
            compte.setdefault(feature.qualifie, []).append(feature)
        for nom, liste in compte.items():
            if len(liste) > 1:
                dits.append(
                    f"{nom.rsplit('/', 1)[-1]} sera installee {len(liste)} "
                    f"fois : les options different "
                    f"({', '.join(str(f.options) for f in liste)}), et deux "
                    f"Features aux options differentes ne sont pas egales")
    for identifiant, passees in config.features.items():
        manifeste = index.get(features.nom_qualifie(identifiant))
        if manifeste is None:
            continue
        inconnues = options.ignorees(manifeste, passees if isinstance(passees, dict) else {})
        if inconnues:
            declarees = sorted(manifeste.get("options") or {})
            dits.append(f"{features.nom_qualifie(identifiant).rsplit('/', 1)[-1]} : "
                        f"option(s) {', '.join(inconnues)} non declaree(s) — "
                        f"ignoree(s) en silence (declarees : "
                        f"{', '.join(declarees) or 'aucune'})")
    return dits


def principal(argv: list[str] | None = None) -> int:
    utf8()
    args = analyser(argv)
    refuses = 0

    for chemin in args.fichiers:
        config = charger(chemin)
        texte = chemin.read_text(encoding="utf-8")
        strict = est_du_json_strict(texte)
        virgules = virgules_finales(texte)
        erreurs = (schema_publie.erreurs_brutes(config) if args.brut
                   else schema_publie.verifier(config))
        if erreurs:
            refuses += 1
        if args.muet:
            continue

        print(f"\n{chemin}")
        print(f"   {config.nom}   —   depart : {config.depart}")
        if not strict:
            print("   (JSONC : commentaires ou virgule finale — `json.load` "
                  "echouerait)")
        for cible, message in erreurs:
            print(f"   REFUS  {cible}")
            print(f"          {message}")
        if virgules:
            print(f"   ⚠  virgule finale ligne(s) "
                  f"{', '.join(str(v) for v in virgules)} — le schema "
                  f"declare `allowTrailingCommas: false`")
        for avis in avertissements(config, args.base):
            print(f"   ⚠  {avis}")
        if not erreurs:
            print("   le schema publie accepte cette configuration")

    print(f"\n{refuses} fichier(s) refuse(s) sur {len(args.fichiers)}")
    return refuses


if __name__ == "__main__":
    raise SystemExit(principal())
