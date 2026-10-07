"""Extraire la fiche d'une annonce avec un modèle local, et la noter.

La sortie est contrainte par un schéma JSON (paramètre `format` d'Ollama) :
le modèle ne peut rendre que les cinq champs attendus, et `contrat` et `mode`
seulement parmi les valeurs du portail. La note compte les champs justes.
"""

import json

import ollama

from jobportal.donnees import CHAMPS, CONTRATS, MODES

SCHEMA_FICHE = {
    "type": "object",
    "properties": {
        "ville": {"type": "string"},
        "contrat": {"type": "string", "enum": CONTRATS},
        "mode": {"type": "string", "enum": MODES},
        "salaire_min": {"type": "integer"},
        "salaire_max": {"type": "integer"},
    },
    "required": CHAMPS,
}

CONSIGNE = (
    "Tu extrais la fiche d'une annonce d'emploi. Salaires en euros bruts ANNUELS, "
    "en nombre entier (52 k€ = 52000). Ville : la ville du poste, sans département."
)


def extraire_fiche(client: ollama.Client, modele: str,
                   annonce: str) -> tuple[dict, ollama.ChatResponse]:
    reponse = client.chat(
        model=modele,
        messages=[{"role": "system", "content": CONSIGNE}, {"role": "user", "content": annonce}],
        # TODO : imposer le schéma de la fiche à la génération (paramètre format), avec une température à 0 et une graine fixe.
    )
    return json.loads(reponse.message.content), reponse


def champs_justes(fiche: dict, attendu: dict) -> int:
    """Le nombre de champs exacts. La ville se compare sans casse ni espaces."""
    # TODO : compter les champs justes. Un texte se compare sans casse ni espaces autour ; un nombre doit être exact.
    return 0
