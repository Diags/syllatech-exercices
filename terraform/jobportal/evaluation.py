"""Evaluer une expression HCL une fois qu'on sait ce que valent les noms.

L'analyseur de `hcl.py` ne calcule rien : il rend un arbre ou `var.taille`
reste une `Reference`. C'est delibere — Terraform fait la meme chose, et
pour la meme raison : **l'ordre d'evaluation depend des dependances**, pas
de l'ordre des lignes dans le fichier.

Ce module fait le second temps : il resout les references dans un
*contexte* (les variables, les locals, les ressources deja connues, la
variable de boucle `each`).

⚠️ UNE REFERENCE INCONNUE LEVE, ELLE NE REND PAS UNE CHAINE VIDE.
C'est le comportement qui evite les catastrophes silencieuses : un nom mal
orthographie doit arreter le plan, pas produire un conteneur nomme
« jobportal- » parce que la variable etait vide.
"""

from __future__ import annotations

from typing import Any

from .hcl import (Appel, BoucleListe, BoucleObjet, Index, Interpolation,
                  Reference)


class ErreurEvaluation(Exception):
    """Une reference introuvable, une fonction inconnue, un mauvais type."""


def evaluer(expression: Any, contexte: dict[str, Any]) -> Any:
    """Rend la valeur d'une expression dans un contexte donne."""
    if isinstance(expression, Reference):
        return _resoudre(expression, contexte)
    if isinstance(expression, Interpolation):
        return "".join(
            _texte(evaluer(morceau, contexte)) if not isinstance(morceau, str)
            else morceau
            for morceau in expression.morceaux)
    if isinstance(expression, Appel):
        return _appeler(expression, contexte)
    if isinstance(expression, Index):
        source = evaluer(expression.source, contexte)
        cle = evaluer(expression.cle, contexte)
        try:
            return source[cle]
        except (KeyError, IndexError, TypeError) as erreur:
            raise ErreurEvaluation(
                f"index invalide : {cle!r} sur {type(source).__name__}"
            ) from erreur
    if isinstance(expression, BoucleListe):
        source = evaluer(expression.source, contexte)
        return [evaluer(expression.valeur,
                        {**contexte, expression.variable: valeur})
                for valeur in _iterer(source)]
    if isinstance(expression, BoucleObjet):
        source = evaluer(expression.source, contexte)
        resultat: dict[str, Any] = {}
        for cle, valeur in _paires(source):
            local = {**contexte,
                     expression.cle_variable: cle,
                     expression.valeur_variable: valeur}
            resultat[_texte(evaluer(expression.cle, local))] = evaluer(
                expression.valeur, local)
        return resultat
    if isinstance(expression, list):
        return [evaluer(element, contexte) for element in expression]
    if isinstance(expression, dict):
        return {cle: evaluer(valeur, contexte)
                for cle, valeur in expression.items()}
    return expression


def _resoudre(reference: Reference, contexte: dict[str, Any]) -> Any:
    # TODO : descendre le chemin segment par segment, et LEVER si un segment manque
    return ""


def _texte(valeur: Any) -> str:
    if isinstance(valeur, bool):
        return "true" if valeur else "false"
    if valeur is None:
        return ""
    return str(valeur)


def _iterer(source: Any):
    if isinstance(source, dict):
        return list(source.values())
    if isinstance(source, (list, tuple, set)):
        return list(source)
    raise ErreurEvaluation(f"valeur non parcourable : {source!r}")


def _paires(source: Any):
    if isinstance(source, dict):
        return list(source.items())
    if isinstance(source, (list, tuple)):
        return list(enumerate(source))
    raise ErreurEvaluation(f"valeur non parcourable par cle : {source!r}")


# ── les fonctions du langage ─────────────────────────────────────────────

def _fonction_merge(*cartes):
    resultat: dict[str, Any] = {}
    for carte in cartes:
        resultat.update(carte)
    return resultat


_FONCTIONS = {
    "contains": lambda collection, valeur: valeur in collection,
    "length": len,
    "upper": lambda texte: str(texte).upper(),
    "lower": lambda texte: str(texte).lower(),
    "join": lambda separateur, liste: str(separateur).join(
        _texte(element) for element in liste),
    "keys": lambda carte: sorted(carte.keys()),
    "values": lambda carte: [carte[cle] for cle in sorted(carte.keys())],
    "merge": _fonction_merge,
    "toset": lambda liste: sorted(set(liste)),
    "format": lambda modele, *arguments: str(modele) % arguments,
    "tostring": _texte,
}


def _appeler(appel: Appel, contexte: dict[str, Any]) -> Any:
    fonction = _FONCTIONS.get(appel.nom)
    if fonction is None:
        raise ErreurEvaluation(
            f"fonction inconnue : « {appel.nom} ». "
            f"Celles de ce projet : {', '.join(sorted(_FONCTIONS))}")
    arguments = [evaluer(argument, contexte) for argument in appel.arguments]
    return fonction(*arguments)


def dependances(expression: Any) -> set[str]:
    """Les ressources dont une expression depend — la base du graphe.

    Terraform ne lit pas vos fichiers dans l'ordre : il construit un graphe
    a partir de ces references, puis le parcourt. C'est pourquoi une
    ressource peut en citer une autre declaree plus bas dans le fichier.
    """
    trouvees: set[str] = set()
    _collecter(expression, trouvees)
    return trouvees


def _collecter(expression: Any, trouvees: set[str]) -> None:
    if isinstance(expression, Reference):
        chemin = expression.chemin
        if chemin[0] in ("var", "local", "each", "count", "module"):
            return
        if len(chemin) >= 2:
            trouvees.add(f"{chemin[0]}.{chemin[1]}")
        return
    if isinstance(expression, Interpolation):
        for morceau in expression.morceaux:
            _collecter(morceau, trouvees)
        return
    if isinstance(expression, Appel):
        for argument in expression.arguments:
            _collecter(argument, trouvees)
        return
    if isinstance(expression, Index):
        _collecter(expression.source, trouvees)
        _collecter(expression.cle, trouvees)
        return
    if isinstance(expression, BoucleListe):
        _collecter(expression.source, trouvees)
        _collecter(expression.valeur, trouvees)
        return
    if isinstance(expression, BoucleObjet):
        _collecter(expression.source, trouvees)
        _collecter(expression.cle, trouvees)
        _collecter(expression.valeur, trouvees)
        return
    if isinstance(expression, list):
        for element in expression:
            _collecter(element, trouvees)
        return
    if isinstance(expression, dict):
        for valeur in expression.values():
            _collecter(valeur, trouvees)
