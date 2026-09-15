"""Chapitre 4 — Outils, MCP & backends d'exécution.

    uv run python chapitres/chapitre_4_outils.py

Hermes déclare 57 ensembles d'outils et 79 outils. Ce chapitre les compte, les
pèse, et mesure l'écart entre ce qu'on active et ce que le modèle reçoit —
parce que cet écart est grand, silencieux, et qu'il dépend de la machine.

Tout vient de `toolsets` et `model_tools`, les modules de Hermes.
"""

from __future__ import annotations

import contextlib
import io
import json
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8              # noqa: E402
from jobportal.outillage import (couverture, cout_en_jetons,  # noqa: E402
                                 definitions, description_de,
                                 ensemble_de, orphelins, outils_de,
                                 tous_les_ensembles)


@contextlib.contextmanager
def sans_bruit():
    """Hermes journalise chaque verification d'outil, et sonde ses fournisseurs.

    ⚠️ `check_tool_availability()` ne se contente pas de lire la
    configuration : il interroge les fournisseurs auxiliaires, et signale
    « payment / credit error » quand aucun n'est joignable. Une fonction qui
    s'appelle « verifier la disponibilite » fait donc des appels reseau — a
    savoir avant de la mettre dans une sonde de demarrage.
    """
    niveau = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    piege = io.StringIO()
    try:
        with contextlib.redirect_stderr(piege):
            yield
    finally:
        logging.disable(niveau)


def main() -> None:
    utf8()

    titre(1, "CE QUE HERMES DECLARE")
    chiffres = couverture()
    ligne("ensembles d'outils", str(chiffres["ensembles"]), 30)
    ligne("outils au total", str(chiffres["outils"]), 30)
    ligne("outils rattaches a un ensemble", str(chiffres["outils_couverts"]), 30)
    ligne("outils orphelins", str(len(orphelins())) or "0", 30)
    ligne("references vers un outil absent",
          str(chiffres["references_inconnues"]), 30)
    print()
    print("   Les deux dernieres lignes sont a zero, et c'est une bonne")
    print("   nouvelle : chaque outil appartient a un ensemble, et aucun")
    print("   ensemble ne reference un outil qui n'existe pas. Ce n'est pas")
    print("   automatique — c'est deux listes tenues a jour ensemble.")

    titre(2, "QUELQUES ENSEMBLES, ET CE QU'ILS CONTIENNENT")
    for nom in ("coding", "browser", "memory", "delegation", "cronjob"):
        outils = outils_de(nom)
        if not outils:
            continue
        ligne(nom, f"{len(outils):>2} outils — {description_de(nom)[:44]}", 14)
    print()
    print("   Un ensemble n'est pas une categorie de rangement : c'est une")
    print("   UNITE D'ACTIVATION. On active « coding », pas quinze outils.")

    titre(3, "CE QU'ON ACTIVE N'EST PAS CE QU'ON RECOIT")
    import model_tools

    with sans_bruit():
        disponibles, manquants = model_tools.check_tool_availability(quiet=True)
    ligne("ensembles declares", str(chiffres["ensembles"]), 32)
    ligne("  dont ceux qui posent une condition",
          f"{len(model_tools.TOOLSET_REQUIREMENTS)}", 36)
    ligne("    condition remplie ici", str(len(disponibles)), 34)
    ligne("    condition NON remplie", str(len(manquants)), 34)
    ligne("  sans aucune condition",
          str(chiffres["ensembles"] - len(model_tools.TOOLSET_REQUIREMENTS)), 36)
    print()
    print("   Les nombres ne s'additionnent pas comme on croit : 29 ensembles")
    print("   sur 57 declarent une condition, et les 28 autres sont toujours")
    print("   disponibles. Ce qui manque ici, et pourquoi :\n")
    for manque in manquants[:5]:
        variables = ", ".join(manque.get("env_vars") or []) \
            or "un binaire ou un service absent"
        print(f"      {manque['name']:<18}{variables}")
    print()
    print("   Un ensemble dont la condition n'est pas remplie n'est pas en")
    print("   erreur : il est ABSENT. Activer « browser » sans navigateur ne")
    print("   donne pas un outil qui echoue — cela ne donne aucun outil, et")
    print("   l'agent repond qu'il ne sait pas naviguer.")
    print()
    print("   ⚠️ Et il y a un SECOND filtre, un cran plus bas : chaque outil")
    print("   peut poser sa propre condition. « coding » n'en pose aucune,")
    print(f"   annonce {len(outils_de('coding'))} outils — et la section "
          f"suivante en offre moins.")

    titre(4, "CE QUE LE CATALOGUE COUTE, A CHAQUE TOUR")
    with sans_bruit():
        defs = definitions(None)
    total = cout_en_jetons(defs)
    ligne("outils reellement offerts", str(len(defs)), 30)
    ligne("cout du catalogue", f"~{total} jetons", 30)
    print()
    tailles = sorted(((len(json.dumps(t, ensure_ascii=False)) // 4,
                       (t.get("function") or {}).get("name") or t.get("name"))
                      for t in defs), reverse=True)
    print(f"   {'les six outils les plus chers':<30}part du catalogue")
    for cout, nom in tailles[:6]:
        print(f"   {str(nom):<30}{cout:>5} jetons   {cout / total:>5.0%}")
    print(f"   {'les six, ensemble':<30}"
          f"{sum(c for c, _ in tailles[:6]):>5} jetons   "
          f"{sum(c for c, _ in tailles[:6]) / total:>5.0%}")
    print()
    print("   Six outils sur dix-neuf pesent plus de la moitie du catalogue.")
    print("   C'est la liste des SCHEMAS qui coute, pas le nombre d'outils :")
    print("   un outil a douze parametres documentes vaut dix outils simples.")
    print()
    print("   Et ce cout est paye a CHAQUE tour de la boucle, puisque la")
    print("   liste fait partie de la requete. Sur une conversation de dix")
    print(f"   tours, c'est ~{total * 10} jetons de catalogue.")

    titre(5, "ACTIVER MOINS, ET LE MESURER")
    with sans_bruit():
        essais = [("tout ce qui est disponible", None),
                  ("coding seul", ["coding"]),
                  ("coding + memory", ["coding", "memory"])]
        resultats = [(etiquette, definitions(ens)) for etiquette, ens in essais]
    for etiquette, defs_ in resultats:
        ligne(etiquette, f"{len(defs_):>2} outils, ~{cout_en_jetons(defs_)} jetons",
              30)
    print()
    print("   « coding + memory » ne coute pas plus que « coding » seul : les")
    print("   outils de memoire sont deja dans l'ensemble de base. Activer un")
    print("   ensemble n'ajoute que ce qui n'y est pas — et ne rien ajouter")
    print("   ne se signale pas non plus.")

    titre(6, "OU VA UN OUTIL QU'ON CHERCHE")
    for outil in ("terminal", "memory", "skill_manage", "delegate_task"):
        ligne(f"outil « {outil} »", ensemble_de(outil) or "(aucun ensemble)", 26)
    print()
    print("   `get_toolset_for_tool` repond a la question qu'on se pose")
    print("   vraiment : « l'agent n'a pas cet outil — quel ensemble dois-je")
    print("   activer ? ». Sans elle, on active tout, et on paie la section 4.")

    titre(7, "CE QUE CE CHAPITRE NE PROUVE PAS")
    for limite in (
            "aucun outil n'est APPELE ici : les faire tourner demande un",
            "  modele, des cles et, pour certains, un navigateur ;",
            "les backends d'execution (local, conteneur, VPS) ne sont pas",
            "  compares — ils demandent Docker et une machine distante ;",
            "MCP n'est pas branche : `mcp_serve.py` existe dans le paquet,",
            "  et le cours « Model Context Protocol » monte un vrai serveur."):
        print(f"   · {limite}" if not limite.startswith("  ") else f"   {limite}")
    print()
    print("   Ce qui EST mesure : le catalogue, son poids, et l'ecart entre")
    print("   ce qu'on active et ce que le modele recoit.")

    print("\n   Au chapitre suivant : l'agent qui travaille quand personne")
    print("   ne le regarde.\n")


if __name__ == "__main__":
    main()
