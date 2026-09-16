"""Chapitre 3 — Les trois primitives, appelées pour de vrai.

Un outil, une resource, un prompt. La différence entre les trois n'est pas
une question de goût : elle décide de ce qu'un client peut faire **sans vous
demander**. Ce chapitre les appelle toutes les trois et affiche le résultat.

    uv run python chapitres/chapitre_3_primitives.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                      # noqa: E402
from jobportal.serveur import (                    # noqa: E402
    creer_candidature,
    lettre_motivation,
    offre,
    rechercher_offres,
    serveur,
)


def titre(texte: str) -> None:
    print(f"\n{'─' * 68}\n{texte}\n{'─' * 68}")


def main() -> None:
    console.utf8()
    titre("OUTIL — une ACTION que le modèle peut déclencher")
    print("rechercher_offres('python') :")
    for o in rechercher_offres("python"):
        print(f"   {o['id']}  {o['titre']:<36} {o['lieu']}")
    print("\nUn outil peut lire… mais il peut aussi écrire :")
    print("  ", creer_candidature("JP-002", "CV de Diaguily SYLLA"))
    print("   candidatures en base :", donnees.candidatures())
    print("\n→ C'est pourquoi un client MCP demande avant d'appeler un outil :")
    print("  il ne peut pas savoir, de l'extérieur, lequel écrit.")

    titre("RESOURCE — une DONNÉE, que l'on lit sans rien changer")
    print(offre("JP-002"))
    print("\n→ Une resource a une URI (« offres://JP-002 »). Le client peut la")
    print("  lire sans vous demander : par construction, elle ne modifie rien.")

    titre("PROMPT — un MODÈLE de message, réutilisable")
    print(lettre_motivation("Ingénieur IA", "syllatech"))
    print("\n→ Le prompt n'exécute rien. Il fournit au client un texte tout prêt,")
    print("  que l'utilisateur choisit d'envoyer. C'est de l'outillage humain.")

    titre("CE QUE LE SERVEUR DÉCLARE")
    print(f"nom du serveur : {serveur.name}")
    print("Les trois primitives ci-dessus sont enregistrées par les décorateurs")
    print("@serveur.tool(), @serveur.resource(...) et @serveur.prompt() dans")
    print("jobportal/serveur.py — ouvrez-le, c'est vingt lignes.")


if __name__ == "__main__":
    main()
