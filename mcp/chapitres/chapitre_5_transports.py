"""Chapitre 5 — Transports et sécurité.

Trois transports, trois situations, trois niveaux d'exposition. Ce chapitre
les compare, puis lance celui que vous choisissez.

    uv run python chapitres/chapitre_5_transports.py            (comparatif)
    uv run python chapitres/chapitre_5_transports.py stdio      (lance)
    uv run python chapitres/chapitre_5_transports.py http
"""

from __future__ import annotations

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from jobportal import console               # noqa: E402
from jobportal.serveur import serveur       # noqa: E402

TRANSPORTS = {
    "stdio": (
        "local, processus enfant lance par le client",
        "rien n'ecoute sur le reseau ; le client controle le cycle de vie",
        "un seul client a la fois",
    ),
    "streamable-http": (
        "distant, plusieurs clients simultanes",
        "deployable, observable, mis a l'echelle comme un service web",
        "expose sur le reseau : l'autorisation devient obligatoire",
    ),
    "sse": (
        "historique, evenements pousses par le serveur",
        "compatible avec des clients plus anciens",
        "remplace par streamable-http pour les nouveaux projets",
    ),
}


def comparatif() -> None:
    for nom, (quoi, pour, contre) in TRANSPORTS.items():
        print(f"  {nom}")
        print(f"     quoi   : {quoi}")
        print(f"     pour   : {pour}")
        print(f"     limite : {contre}")
        print()
    print("La securite n'est pas un chapitre a part : elle decoule du transport.")
    print()
    print("  En stdio, le perimetre EST le processus. Le client vous a lance,")
    print("  il vous arrete ; personne d'autre ne vous atteint.")
    print()
    print("  En HTTP, votre serveur devient une porte. Il lui faut alors :")
    print("    - OAuth 2.1 : le client obtient un jeton du serveur d'autorisation,")
    print("      chaque requete MCP le porte en Bearer ;")
    print("    - une verification du scope AVANT d'executer l'outil ;")
    print("    - un perimetre minimal : lecture seule par defaut, l'ecriture")
    print("      demandant une permission explicite.")
    print()
    print("Regle pratique : n'exposez en HTTP que ce qui doit l'etre. Un serveur")
    print("qui n'a qu'un seul client n'a aucune raison d'ecouter sur un port.")


def main() -> int:
    console.utf8()
    choix = sys.argv[1] if len(sys.argv) > 1 else None
    if choix is None:
        comparatif()
        print()
        print("Pour en lancer un : ajoutez « stdio » ou « http » a la commande.")
        return 0
    if choix == "stdio":
        print("Serveur en stdio. Il attend du JSON-RPC sur l'entree standard.")
        print("Ctrl+C pour arreter.")
        serveur.run(transport="stdio")
    elif choix == "http":
        print("Serveur en streamable HTTP sur le port 8080. Ctrl+C pour arreter.")
        serveur.run(transport="streamable-http", port=8080)
    else:
        print(f"Transport inconnu : {choix}. Attendu : stdio ou http.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
