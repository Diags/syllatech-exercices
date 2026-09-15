"""Chapitre 1 — Le protocole : outils, ressources, invites.

    uv run python chapitres/chapitre_1_protocole.py

MCP definit trois choses qu'un serveur peut exposer. Les confondre est
l'erreur de debutant la plus courante, et elle se voit ici.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                 # noqa: E402
from jobportal.serveur import serveur         # noqa: E402


async def inventaire() -> None:
    outils = await serveur.list_tools()
    ressources = await serveur.list_resources()

    print("1. LES OUTILS — l'agent les APPELLE, avec des arguments\n")
    for o in outils:
        champs = list(o.input_schema.get("properties", {}))
        requis = set(o.input_schema.get("required", []))
        signature = ", ".join(f"{c}{'' if c in requis else '=...'}" for c in champs)
        print(f"   {o.name}({signature})")
        print(f"     {o.description.splitlines()[0]}")

    print("\n2. LES RESSOURCES — l'agent les LIT, sans argument ni effet\n")
    for r in ressources:
        print(f"   {r.uri}")
        print(f"     {(r.description or '').splitlines()[0]}")

    print("\n   La distinction n'est pas cosmetique. Une ressource ne prend")
    print("   aucun parametre et ne provoque aucun effet : elle se lit pour")
    print("   se situer. Un outil agit. Exposer le schema de la base comme un")
    print("   OUTIL obligerait l'agent a « l'appeler » pour savoir ou il est,")
    print("   et le rendrait interdisable par une regle de permission — alors")
    print("   qu'il n'y a rien a interdire dans la lecture d'un schema.")

    print("\n3. CE QUE L'AGENT VOIT DE CHAQUE OUTIL\n")
    outil = next(o for o in outils if o.name == "rechercher_offres")
    print(f"   nom         {outil.name}")
    print(f"   description {outil.description.splitlines()[0]}")
    print(f"   schema      {list(outil.input_schema.get('properties', {}))}")
    print("\n   C'est TOUT. Le corps de la fonction, ses commentaires, votre")
    print("   README : rien de cela n'arrive jusqu'au modele. La docstring")
    print("   est le seul indice dont il dispose pour decider d'appeler cet")
    print("   outil plutot qu'un autre — et une docstring vague produit un")
    print("   outil qui ne se declenche jamais, sans que rien ne le signale.")

    print("\n4. LE NOM COMPLET, COTE CLAUDE CODE\n")
    for o in outils:
        print(f"   mcp__jobportal__{o.name}")
    print("\n   C'est sous cette forme que les regles de permission les")
    print("   designent : mcp__<serveur>__<outil>. Le chapitre 4 montre")
    print("   pourquoi ce nom demande plus d'attention qu'il n'y parait.")


def main() -> None:
    console.utf8()
    asyncio.run(inventaire())


if __name__ == "__main__":
    main()
