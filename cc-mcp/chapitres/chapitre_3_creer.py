"""Chapitre 3 — Creer son serveur : la docstring EST l'interface.

    uv run python chapitres/chapitre_3_creer.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                        # noqa: E402
from jobportal.serveur import serveur                # noqa: E402
from mcp.server.mcpserver import MCPServer           # noqa: E402


async def demonstration() -> None:
    print("1. LE NOM DE LA CLASSE A CHANGE\n")
    print("   SDK 2.x   from mcp.server.mcpserver import MCPServer")
    print("   SDK 1.x   from mcp.server.fastmcp import FastMCP   (les extraits du cours)")
    try:
        from mcp.server.fastmcp import FastMCP       # noqa: F401
        print("\n   L'ancien nom repond encore sur cette installation.")
    except ImportError as e:
        print(f"\n   L'ancien import echoue ici : {e}")
    print("   Celui-la echoue BRUYAMMENT : on le corrige en trente secondes.")
    print("   Le vrai piege est la borne de version — « mcp[cli]>=1.2 »")
    print("   autorise une 1.x ou MCPServer n'existe pas. Ce projet borne des")
    print("   deux cotes : mcp>=2.2,<3. Chapitre 6.")

    print("\n2. UN OUTIL EST UNE FONCTION DECOREE, ET RIEN DE PLUS\n")
    essai = MCPServer("essai")

    @essai.tool()
    def compter(elements: list[str]) -> int:
        """Compte les elements d'une liste."""
        return len(elements)

    outil = (await essai.list_tools())[0]
    print(f"   nom         {outil.name}")
    print(f"   description {outil.description}")
    print(f"   entree      {outil.input_schema.get('properties')}")
    print(f"   sortie      {outil.output_schema.get('properties')}")
    print("\n   Les deux schemas sont deduits des ANNOTATIONS de type. Une")
    print("   fonction sans annotation produit un outil dont le modele ne sait")
    print("   pas quoi passer — et il passera n'importe quoi.")

    print("\n3. LA DOCSTRING EST LE SEUL INDICE DU MODELE\n")
    for avant, apres in [
        ("Recherche.", "Recherche les offres d'emploi par mot-cle, "
                       "eventuellement filtrees par ville."),
    ]:
        print(f"   vague   « {avant} »")
        print(f"   precise « {apres} »")
    print("\n   Le corps de la fonction, ses commentaires, votre README :")
    print("   rien de cela n'arrive au modele. Une docstring vague produit un")
    print("   outil qui ne se declenche jamais, ou qui se declenche a tort.")
    print("   Aucune erreur ne vous le signale — c'est un defaut de qualite,")
    print("   pas de syntaxe.")

    print("\n4. LECTURE ET ECRITURE DANS DES OUTILS SEPARES\n")
    for o in await serveur.list_tools():
        role = "ECRIT" if o.name.startswith(("supprimer", "creer", "modifier")) else "lit  "
        print(f"   {role}  {o.name}")
    print("\n   Ce decoupage n'est pas du style : c'est ce qui rend une regle")
    print("   de permission ecrivable. Un outil « gerer_offre(action=...) »")
    print("   qui lit ET supprime selon son parametre ne peut etre ni")
    print("   autorise, ni interdit — seulement approuve a l'aveugle.")


def main() -> None:
    console.utf8()
    asyncio.run(demonstration())


if __name__ == "__main__":
    main()
