"""Les outils — autour des VRAIS `toolsets` et `model_tools` de Hermes.

    toolsets.TOOLSETS               57 ensembles
    model_tools.get_all_tool_names() 79 outils
    model_tools.get_tool_definitions(enabled_toolsets=…)  les schemas JSON

Rien n'est réimplémenté : les ensembles, les outils et leurs schémas sont
ceux de Hermes. Ce module les compte, les pèse, et répond à la seule question
qui se pose en pratique — **lesquels activer ?**

POURQUOI LA QUESTION SE POSE

La liste des outils fait partie de chaque requête. Elle est donc payée à
chaque tour de la boucle, et plus elle est longue, plus le modèle choisit
mal. Activer les 57 ensembles « au cas où » est le réglage par défaut de
beaucoup d'installations, et c'est le plus cher.
"""

from __future__ import annotations

import json

import model_tools
import toolsets


def tous_les_ensembles() -> dict[str, dict]:
    return dict(toolsets.TOOLSETS)


def outils_de(ensemble: str) -> list[str]:
    infos = toolsets.get_toolset(ensemble) or {}
    return list(infos.get("tools") or [])


def description_de(ensemble: str) -> str:
    infos = toolsets.get_toolset(ensemble) or {}
    return str(infos.get("description") or "")


def definitions(ensembles: list[str] | None = None) -> list[dict]:
    """Les schémas que le modèle reçoit réellement."""
    return model_tools.get_tool_definitions(enabled_toolsets=ensembles,
                                            quiet_mode=True)


def cout_en_jetons(defs: list[dict]) -> int:
    """Une approximation assumée : quatre signes par jeton.

    L'ordre de grandeur suffit pour la seule chose qui compte ici — le
    RAPPORT entre un catalogue complet et une sélection.
    """
    return len(json.dumps(defs, ensure_ascii=False)) // 4


def ensemble_de(outil: str) -> str | None:
    return model_tools.get_toolset_for_tool(outil)


def orphelins() -> list[str]:
    """Les outils qu'aucun ensemble ne réclame.

    Un outil sans ensemble ne s'active pas en activant un ensemble : il faut
    le connaître par son nom. C'est rare, et c'est exactement le genre de
    chose qu'on ne découvre qu'en comptant.
    """
    return sorted(nom for nom in model_tools.get_all_tool_names()
                  if not model_tools.get_toolset_for_tool(nom))


def couverture() -> dict[str, int]:
    # >>> depart: compter les outils, les ensembles, les outils rattaches a au moins un ensemble, et les references vers un outil qui n'existe pas. Les deux derniers nombres disent si les deux listes de Hermes sont tenues a jour ensemble. Un test le verifie.
    #     return {"outils": 0, "ensembles": 0, "outils_couverts": 0, "references_inconnues": 0}
    tous = model_tools.get_all_tool_names()
    dans_un_ensemble = {o for e in toolsets.TOOLSETS for o in outils_de(e)}
    return {
        "outils": len(tous),
        "ensembles": len(toolsets.TOOLSETS),
        "outils_couverts": len(set(tous) & dans_un_ensemble),
        "references_inconnues": len(dans_un_ensemble - set(tous)),
    }
    # <<<
