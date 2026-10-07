"""Les outils de l'agent : ce qu'il peut demander au portail, et rien d'autre.

Le modèle ne lit jamais la base : il demande un outil, le code l'exécute et
lui rend un résultat. Un outil rend toujours du JSON ; une erreur (une
référence inconnue) revient comme un résultat, pour que le modèle puisse la
dire au lieu d'inventer.
"""

import json

from jobportal.donnees import CANDIDATURES, OFFRES, PAR_REFERENCE
from jobportal.recherche import Index

CHAMPS_PUBLICS = ("reference", "titre", "entreprise", "ville", "contrat", "mode", "salaire_min", "salaire_max")


def _fiche(o: dict) -> dict:
    """Ce que l'outil rend d'une offre : les champs publics, sans la description."""
    return {c: o[c] for c in CHAMPS_PUBLICS}


def rechercher_offres(index: Index, requete: str) -> str:
    return json.dumps([_fiche(o) for o in index.chercher(requete)], ensure_ascii=False)


def filtrer_offres(ville: str = "", contrat: str = "", mode: str = "", categorie: str = "") -> str:
    def garde(o):
        return all(not v or v.lower() == o[c].lower()
                   for c, v in (("ville", ville), ("contrat", contrat), ("mode", mode), ("categorie", categorie)))
    return json.dumps([_fiche(o) for o in OFFRES if garde(o)], ensure_ascii=False)


def compter_candidatures(reference: str) -> str:
    if reference not in PAR_REFERENCE:
        return json.dumps({"erreur": f"l'offre {reference} n'existe pas dans le portail"}, ensure_ascii=False)
    return json.dumps({"reference": reference, "candidatures": CANDIDATURES[reference]})


def classement_candidatures(n: int = 3) -> str:
    tries = sorted(CANDIDATURES.items(), key=lambda kv: kv[1], reverse=True)[:n]
    return json.dumps([{"reference": r, "titre": PAR_REFERENCE[r]["titre"], "candidatures": c}
                       for r, c in tries], ensure_ascii=False)


def _schema(nom, description, proprietes, requis=()):
    return {"type": "function", "function": {
        "name": nom, "description": description,
        "parameters": {"type": "object", "properties": proprietes, "required": list(requis)}}}


TEXTE = {"type": "string"}
SCHEMAS = [
    _schema("rechercher_offres", "Recherche des offres par le sens : métier, compétence, technologie.",
            {"requete": {**TEXTE, "description": "ce que cherche l'utilisateur, en quelques mots"}},
            ["requete"]),
    _schema("filtrer_offres", "Liste les offres selon des critères exacts ; un critère vide est ignoré.",
            {"ville": TEXTE, "contrat": {**TEXTE, "enum": ["", "CDI", "CDD", "Freelance", "Stage", "Alternance"]},
             "mode": {**TEXTE, "enum": ["", "sur site", "hybride", "à distance"]}, "categorie": TEXTE}),
    _schema("compter_candidatures", "Le nombre de candidatures reçues par une offre.",
            {"reference": {**TEXTE, "description": "par exemple OFF-103"}}, ["reference"]),
    _schema("classement_candidatures", "Les offres qui ont reçu le plus de candidatures.",
            {"n": {"type": "integer", "description": "combien d'offres, 3 par défaut"}}),
]


def executer(index: Index, nom: str, arguments: dict) -> str:
    """Exécute l'outil demandé ; un nom ou des arguments faux reviennent en erreur, pas en exception."""
    fonctions = {"rechercher_offres": lambda **a: rechercher_offres(index, **a), "filtrer_offres": filtrer_offres,
                 "compter_candidatures": compter_candidatures, "classement_candidatures": classement_candidatures}
    if nom not in fonctions:
        return json.dumps({"erreur": f"outil inconnu : {nom}"}, ensure_ascii=False)
    try:
        return fonctions[nom](**arguments)
    except TypeError as erreur:
        return json.dumps({"erreur": f"arguments invalides : {erreur}"}, ensure_ascii=False)
