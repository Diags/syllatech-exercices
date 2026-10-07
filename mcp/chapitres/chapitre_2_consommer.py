"""Chapitre 2 — Consommer des serveurs MCP existants.

Le chemin le plus rapide vers un agent outillé n'est pas d'écrire un serveur :
c'est d'en brancher un qui existe. Ce chapitre lit le `.mcp.json` du projet et
explique, entrée par entrée, ce que chaque ligne déclenche.

    uv run python chapitres/chapitre_2_consommer.py
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from jobportal import console               # noqa: E402

CATALOGUE = {
    "uvx": "lance un paquet Python sans l'installer (fourni par uv)",
    "npx": "lance un paquet npm sans l'installer (fourni par Node)",
    "uv": "le gestionnaire de projet Python utilise ici",
    "docker": "lance le serveur dans un conteneur, isole de votre machine",
}


def main() -> None:
    console.utf8()
    fichier = RACINE / ".mcp.json"
    config = json.loads(fichier.read_text(encoding="utf-8"))
    serveurs = config.get("mcpServers", {})

    print(f"{fichier.name} declare {len(serveurs)} serveur(s).\n")
    for nom, entree in serveurs.items():
        commande = entree.get("command", "")
        args = entree.get("args", [])
        dispo = shutil.which(commande)
        print(f"  {nom}")
        print(f"     commande : {commande} {' '.join(args)}")
        print(f"     role     : {CATALOGUE.get(commande, 'commande maison')}")
        print(f"     presente : {'oui — ' + dispo if dispo else 'NON : installez-la avant de brancher ce serveur'}")
        print()

    print("Ce que fait le client MCP avec ce fichier :")
    print("  1. il lance chaque commande comme un processus enfant ;")
    print("  2. il parle JSON-RPC avec lui sur l'entree et la sortie standard ;")
    print("  3. il demande la liste des outils, resources et prompts offerts ;")
    print("  4. il les presente au modele comme s'ils etaient les siens.")
    print()
    print("Rien n'ecoute sur le reseau : c'est le transport stdio, celui du")
    print("chapitre 5. C'est pour cela qu'il est le plus simple ET le plus sur.")
    print()
    print("Pour brancher CE serveur dans Claude Code : copiez .mcp.json a la")
    print("racine de votre projet, puis relancez la session.")


if __name__ == "__main__":
    main()
