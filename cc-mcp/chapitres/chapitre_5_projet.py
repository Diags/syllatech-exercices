"""Chapitre 5 — Le serveur base de donnees du job portal, de bout en bout.

    uv run python chapitres/chapitre_5_projet.py

Ce que l'agent ferait vraiment, dans l'ordre : lire le schema, chercher,
croiser, puis buter sur ce qui est interdit.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

from jobportal import console, donnees, serveur as srv   # noqa: E402
from verifier_acces import correspond                    # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def autorise(outil: str) -> tuple[bool, str]:
    """Applique les regles du projet dans l'ordre : deny, ask, allow."""
    p = json.loads((RACINE / ".claude" / "settings.json")
                   .read_text(encoding="utf-8"))["permissions"]
    for genre in ("deny", "ask", "allow"):
        for regle in p.get(genre, []):
            if correspond(regle, outil):
                return genre == "allow", genre
    return False, "aucune regle — Claude Code demandera"


async def main_async() -> None:
    print("ETAPE 1 — l'agent lit la ressource pour se situer\n")
    for ligne in donnees.schema_texte().splitlines():
        print("   " + ligne)
    print("\n   Aucun appel d'outil : une ressource se lit. C'est ce qui evite")
    print("   a l'agent d'inventer des noms de colonnes.")

    print("\nETAPE 2 — « quelles offres Python a Lyon ? »\n")
    outil = "mcp__jobportal__rechercher_offres"
    ok, genre = autorise(outil)
    print(f"   {outil}  →  {genre}")
    for o in srv.rechercher_offres("Python", "Lyon"):
        print(f"     {o['id']}  {o['titre']:<34}{o['contrat']:<11}{o['salaire_min']} EUR")

    print("\nETAPE 3 — « combien de candidatures sur off-000 ? »\n")
    stats = srv.statistiques_candidatures("off-000")
    print(f"   total {stats['total']} — {stats['par_statut']}")

    print("\nETAPE 4 — « quelles offres n'interessent personne ? »\n")
    orphelines = srv.offres_sans_candidature()
    for o in orphelines[:5]:
        print(f"   {o['id']}  {o['titre']}")
    print(f"   ... {len(orphelines)} au total")
    print("\n   Cette question-la n'a pas d'equivalent dans une interface web :")
    print("   c'est une jointure. Donner la BASE a l'agent, plutot qu'une API")
    print("   figee, c'est lui donner les questions qu'on n'a pas prevues.")

    print("\nETAPE 5 — « supprime off-000 »\n")
    outil = "mcp__jobportal__supprimer_offre"
    ok, genre = autorise(outil)
    print(f"   {outil}  →  {genre.upper()}")
    avant = len(donnees.query("SELECT id FROM offres"))
    if ok:
        srv.supprimer_offre("off-000")
    apres = len(donnees.query("SELECT id FROM offres"))
    print(f"   offres avant {avant}, apres {apres}")
    print("\n   L'outil EXISTE et fonctionne — c'est ce qui rend la regle utile.")
    print("   Une permission sur un outil incapable d'agir ne protege de rien.")

    print("\nETAPE 6 — ce que la session voit de tout cela\n")
    for o in await srv.serveur.list_tools():
        nom = f"mcp__jobportal__{o.name}"
        _, genre = autorise(nom)
        print(f"   {genre.upper():<10}{nom}")


def main() -> None:
    console.utf8()
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
