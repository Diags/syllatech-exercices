"""Les outils que l'agent peut appeler.

Un outil LangChain, c'est une fonction annotée : le décorateur en tire le nom,
la description (depuis la docstring) et le schéma des arguments (depuis les
annotations de type). Ce sont ces trois choses que le modèle voit.
"""

from __future__ import annotations

from langchain_core.tools import tool

from . import donnees


@tool
def rechercher_offres(mot_cle: str) -> str:
    """Recherche les offres d'emploi par mot-cle : titre, lieu ou competence."""
    trouvees = donnees.query(mot_cle)
    if not trouvees:
        return f"Aucune offre pour « {mot_cle} »."
    return " ; ".join(f"{o['id']} {o['titre']} ({o['lieu']})" for o in trouvees)


@tool
def detail_offre(offre_id: str) -> str:
    """Donne le detail d'une offre a partir de son identifiant."""
    return donnees.get_offre(offre_id)


OUTILS = [rechercher_offres, detail_offre]
