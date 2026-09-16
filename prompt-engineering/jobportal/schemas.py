"""Les sorties structurées : transformer du texte en donnée vérifiable.

Un modèle rend du texte. Tant qu'il reste du texte, on ne peut que le lire.
Décrit par un schéma, il devient une donnée : validée, typée, testable — et
un écart devient une ERREUR au lieu d'un malentendu.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, Field, ValidationError


# TODO : décrire le contrat de sortie. Les tests exigent qu'un avis d'un mot soit REFUSÉ et qu'un risque de 42 le soit aussi : le schéma contraint le contenu, pas seulement la forme.
class Analyse(BaseModel):
    """La sortie attendue du conseiller carrière (chapitre 1)."""


def analyser_sortie(texte: str) -> tuple[Analyse | None, str]:
    """Valide une sortie de modèle. Rend (objet, message d'erreur).

    Les deux échecs possibles sont distingués : le modèle n'a pas rendu de
    JSON du tout, ou il en a rendu un qui ne respecte pas le contrat. Ce
    n'est pas la même correction à apporter au prompt.
    """
    try:
        brut = json.loads(texte)
    except json.JSONDecodeError as e:
        return None, f"pas du JSON : {e.msg}"
    try:
        return Analyse.model_validate(brut), ""
    except ValidationError as e:
        premiere = e.errors()[0]
        champ = ".".join(str(p) for p in premiere["loc"])
        return None, f"champ « {champ} » : {premiere['msg']}"
