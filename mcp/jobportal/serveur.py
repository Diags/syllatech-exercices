"""Le serveur MCP du fil rouge « job portal », complet.

Les trois primitives du protocole y sont, avec la distinction qui structure
tout le cours :

    outil     (tool)      une ACTION que le modèle peut déclencher
    resource              une DONNÉE que le client peut lire
    prompt                un MODÈLE de message réutilisable

⚠️ API : le SDK Python `mcp` est passé en 2.x, où `FastMCP` a été renommé
`MCPServer` (`from mcp.server.mcpserver import MCPServer`). Les extraits du
cours montrent l'ancien nom, `from mcp.server.fastmcp import FastMCP` : c'est
exactement le même objet, renommé. Ce projet utilise le nom actuel pour que
vous puissiez l'exécuter tel quel ; si vous devez faire tourner du code v1,
épinglez `mcp<2`.

Lancer :  uv run jobportal-serveur          (transport stdio, par défaut)
          uv run jobportal-serveur --http   (streamable HTTP, port 8080)
"""

from __future__ import annotations

import argparse
import sys

from mcp.server.mcpserver import MCPServer

from . import donnees

serveur = MCPServer("jobportal")


# ---------------------------------------------------------------- outils

@serveur.tool()
def rechercher_offres(mot_cle: str) -> list[dict]:
    """Recherche les offres d'emploi par mot-clé (titre, lieu, compétence)."""
    return donnees.query(mot_cle)


@serveur.tool()
def creer_candidature(offre_id: str, cv: str) -> str:
    """Enregistre une candidature à une offre. Action : elle écrit."""
    return donnees.postuler(offre_id, cv)


@serveur.tool()
def lister_candidatures() -> list[dict]:
    """Liste les candidatures déposées dans cette session."""
    return donnees.candidatures()


# ------------------------------------------------------------- resources

# TODO : exposer une offre en RESOURCE, pas en outil. L'URI porte un paramètre ; le décorateur le passe à la fonction. Pourquoi une resource et pas un outil ? Le README le dit.
def offre(offre_id: str) -> str:
    """Expose une offre en lecture."""
    return donnees.get_offre(offre_id)


@serveur.resource("offres://toutes")
def toutes_les_offres() -> str:
    """Le catalogue complet, en texte."""
    return "\n".join(
        f"{o['id']} — {o['titre']} ({o['entreprise']}, {o['lieu']})"
        for o in donnees.query("")
    )


# --------------------------------------------------------------- prompts

@serveur.prompt()
def lettre_motivation(poste: str, entreprise: str = "l'entreprise") -> str:
    """Modèle de lettre de motivation, réutilisable par n'importe quel client."""
    return (
        f"Rédige une lettre de motivation pour le poste de {poste} chez {entreprise}.\n"
        "Contraintes : trois paragraphes, pas de superlatif, une réalisation "
        "chiffrée par paragraphe, et un ton sobre."
    )


@serveur.prompt()
def preparer_entretien(offre_id: str) -> str:
    """Prépare un entretien à partir d'une offre réelle du catalogue."""
    return (
        "Voici une offre :\n\n"
        f"{donnees.get_offre(offre_id)}\n\n"
        "Donne-moi dix questions probables, et pour chacune la faille que "
        "l'intervieweur cherche à sonder."
    )


# ------------------------------------------------------------ démarrage

def main() -> int:
    ap = argparse.ArgumentParser(description="Serveur MCP du job portal")
    ap.add_argument("--http", action="store_true",
                    help="transport streamable HTTP au lieu de stdio")
    ap.add_argument("--port", type=int, default=8080)
    a = ap.parse_args()

    # stdio : le client lance le serveur comme processus enfant — le plus
    # simple, et le plus sûr : rien n'écoute sur le réseau.
    # streamable-http : serveur distant, plusieurs clients. C'est là que la
    # question de l'autorisation se pose vraiment (voir chapitre 5).
    if a.http:
        serveur.run(transport="streamable-http", port=a.port)
    else:
        serveur.run(transport="stdio")
    return 0


if __name__ == "__main__":
    sys.exit(main())
