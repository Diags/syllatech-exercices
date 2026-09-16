"""Le serveur MCP du job portal — celui du chapitre 5, exécutable.

⚠️ LE NOM DE LA CLASSE A CHANGÉ. Le SDK 2.x expose `MCPServer` :

    from mcp.server.mcpserver import MCPServer

Les extraits qui montrent `from mcp.server.fastmcp import FastMCP` datent du
SDK 1.x. Sur une installation à jour, cet import lève `ImportError` — un
défaut qui échoue bruyamment, donc facile. Le vrai piège est ailleurs : une
borne de dépendance à `mcp[cli]>=1.2` autorise la résolution vers une 1.x où
`MCPServer` n'existe pas. Ce projet borne des deux côtés : `mcp>=2.2,<3`.

CE QUE LE SERVEUR EXPOSE, ET POURQUOI CE DÉCOUPAGE

Trois outils de lecture, **un** outil d'écriture, et une ressource. Ce n'est
pas un hasard : c'est ce découpage qui rend la règle de permission du
chapitre 4 écrivable. Un serveur qui mélange lecture et écriture dans le même
outil ne peut pas être gouverné par une liste d'autorisations.
"""

from __future__ import annotations

import argparse
import sys

from mcp.server.mcpserver import MCPServer

from . import donnees

serveur = MCPServer("jobportal")


# ------------------------------------------------------------------ lectures

@serveur.tool()
def rechercher_offres(mot_cle: str, ville: str = "") -> list[dict]:
    """Recherche les offres d'emploi par mot-clé, éventuellement filtrées par ville.

    La description que vous lisez est celle que l'agent lit aussi : c'est le
    SEUL indice dont il dispose pour décider d'appeler cet outil. Une
    docstring vague produit un outil qui ne se déclenche jamais, ou qui se
    déclenche à tort — et rien ne vous le signale.
    """
    sql = ("SELECT id, titre, ville, contrat, salaire_min FROM offres "
           "WHERE titre LIKE ?")
    parametres: list = [f"%{mot_cle}%"]
    if ville:
        sql += " AND ville = ?"
        parametres.append(ville)
    return donnees.query(sql + " ORDER BY publiee_le DESC LIMIT 20", *parametres)


@serveur.tool()
def statistiques_candidatures(offre_id: str) -> dict:
    """Nombre et répartition par statut des candidatures reçues pour une offre."""
    lignes = donnees.query(
        "SELECT statut, COUNT(*) AS n FROM candidatures "
        "WHERE offre_id = ? GROUP BY statut", offre_id)
    return {"offre_id": offre_id,
            "total": sum(l["n"] for l in lignes),
            "par_statut": {l["statut"]: l["n"] for l in lignes}}


@serveur.tool()
def offres_sans_candidature() -> list[dict]:
    """Liste les offres publiées qui n'ont reçu aucune candidature."""
    return donnees.query(
        "SELECT o.id, o.titre, o.ville FROM offres o "
        "LEFT JOIN candidatures c ON c.offre_id = o.id "
        "WHERE c.id IS NULL ORDER BY o.publiee_le")


# ------------------------------------------------------------------ écriture

@serveur.tool()
def supprimer_offre(offre_id: str) -> dict:
    """Supprime définitivement une offre et toutes ses candidatures.

    L'outil que la règle « deny » du chapitre 4 doit couvrir. Il est écrit,
    il fonctionne, et c'est précisément pour cela qu'il faut l'interdire :
    une permission n'a de sens que sur un outil qui pourrait vraiment agir.
    """
    supprimees = donnees.executer("DELETE FROM candidatures WHERE offre_id = ?", offre_id)
    offres = donnees.executer("DELETE FROM offres WHERE id = ?", offre_id)
    return {"offres_supprimees": offres, "candidatures_supprimees": supprimees}


# ----------------------------------------------------------------- ressource

@serveur.resource("schema://tables")
def schema() -> str:
    """Le schéma complet de la base job portal.

    Une RESSOURCE, pas un outil : l'agent la lit pour se situer, sans qu'un
    appel d'outil soit nécessaire. La distinction compte — une ressource ne
    prend pas de paramètre et ne provoque pas d'effet.
    """
    return donnees.schema_texte()


async def outils_exposes() -> list[str]:
    """Les noms d'outils RÉELLEMENT exposés, demandés au serveur lui-même.

    C'est la source de vérité que `outils/verifier_acces.py` compare aux
    règles de permission. Claude Code, lui, ne fait pas cette comparaison
    pour les outils MCP : voir l'en-tête du vérificateur.
    """
    return [o.name for o in await serveur.list_tools()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Serveur MCP du job portal")
    parser.add_argument("--lister", action="store_true",
                        help="affiche les outils exposes et quitte")
    args = parser.parse_args()

    if args.lister:
        import asyncio
        for nom in asyncio.run(outils_exposes()):
            print(f"mcp__jobportal__{nom}")
        return 0

    serveur.run()      # stdio : c'est Claude Code qui parle a l'autre bout
    return 0


if __name__ == "__main__":
    sys.exit(main())
