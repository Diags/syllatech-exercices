"""La specification OpenAPI du job portal — celle qu'on donnerait a la Gateway.

Elle est GENEREE plutot qu'ecrite a la main : quarante operations ecrites une
par une occuperaient six cents lignes sans rien apprendre, et le chapitre 4 a
besoin d'un catalogue assez grand pour que la mesure ait un sens.

La derniere section ajoute deux operations SANS operationId : c'est le cas
qui produit des noms deduits, et parfois des doublons.
"""

from __future__ import annotations

RESSOURCES = [
    ("offres", "offre d'emploi", ["ville", "contrat", "salaire_min"]),
    ("candidats", "candidat", ["nom", "competence", "ville"]),
    ("candidatures", "candidature", ["offre_id", "candidat_id", "statut"]),
    ("entretiens", "entretien", ["candidature_id", "date", "format"]),
    ("entreprises", "entreprise", ["siret", "secteur", "taille"]),
    ("competences", "competence", ["libelle", "niveau"]),
    ("messages", "message", ["destinataire", "sujet"]),
    ("alertes", "alerte", ["frequence", "criteres"]),
]

OPERATIONS = [
    ("get", "Lister les {pluriel}", True),
    ("post", "Creer un(e) {singulier}", False),
    ("get", "Lire un(e) {singulier} par identifiant", False),
    ("put", "Remplacer un(e) {singulier}", False),
    ("delete", "Supprimer un(e) {singulier}", False),
]


def specification() -> dict:
    chemins: dict[str, dict] = {}
    for pluriel, singulier, champs in RESSOURCES:
        collection, element = f"/{pluriel}", f"/{pluriel}/{{id}}"
        for index, (methode, gabarit, sur_collection) in enumerate(OPERATIONS):
            cible = collection if sur_collection or methode == "post" else element
            parametres = (
                [{"name": c, "in": "query", "required": False,
                  "schema": {"type": "string"},
                  "description": f"filtre sur {c}"} for c in champs]
                if cible == collection and methode == "get"
                else [{"name": "id", "in": "path", "required": True,
                       "schema": {"type": "string"},
                       "description": f"identifiant du/de la {singulier}"}]
                if cible == element else [])
            chemins.setdefault(cible, {})[methode] = {
                "operationId": f"{methode}{pluriel.capitalize()}"
                               + ("ParId" if cible == element else ""),
                "summary": gabarit.format(pluriel=pluriel, singulier=singulier),
                "parameters": parametres,
            }

    # Deux operations sans operationId : la Gateway doit deduire un nom.
    chemins["/stats/offres"] = {"get": {
        "summary": "Statistiques des offres", "parameters": []}}
    chemins["/stats/offres/"] = {"get": {
        "summary": "Statistiques des offres (variante avec barre finale)",
        "parameters": []}}

    return {"openapi": "3.0.0",
            "info": {"title": "Job portal", "version": "1.0.0"},
            "paths": chemins}
