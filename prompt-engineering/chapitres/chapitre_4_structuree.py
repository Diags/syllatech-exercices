"""Chapitre 4 — Sorties structurées.

Le schéma ne sert pas à faire joli : il fait la différence entre une sortie
qu'on lit et une sortie qu'on VERIFIE. Ce chapitre soumet quatre sorties de
modèle au même contrat et montre ce que chaque échec vous apprend.

    uv run python chapitres/chapitre_4_structuree.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                       # noqa: E402
from jobportal.schemas import Analyse, analyser_sortie   # noqa: E402

SORTIES = [
    ('{"avis": "Offre solide pour un profil junior.", "risque": 3, "manques": ["salaire"]}',
     "conforme"),
    ("Voici mon avis : l'offre est solide.",
     "le modèle a répondu en prose — le format n'était pas imposé"),
    ('{"avis": "Bien.", "risque": 3, "manques": []}',
     "JSON valide, mais avis trop court : le contrat porte aussi sur le CONTENU"),
    ('{"avis": "Offre correcte mais floue.", "risque": 42, "manques": []}',
     "hors bornes : 42 sur une échelle de 0 à 10"),
]


def main() -> None:
    console.utf8()
    print("Le contrat :\n")
    for nom, champ in Analyse.model_fields.items():
        print(f"   {nom:<9} {champ.description}")

    print("\nQuatre sorties soumises au même contrat :\n")
    for texte, commentaire in SORTIES:
        objet, erreur = analyser_sortie(texte)
        etat = "ACCEPTÉE" if objet else "REFUSÉE "
        print(f"   {etat}  {texte[:56]}")
        print(f"             {erreur or 'conforme'}  —  {commentaire}\n")

    print("Remarquez la troisième : le JSON est valide, la structure est")
    print("bonne, et pourtant elle est refusée. Un schéma ne contraint pas")
    print("que la FORME — « min_length=10 » dit qu'un avis d'un mot n'est pas")
    print("un avis. C'est là qu'un schéma cesse d'être de la plomberie pour")
    print("devenir une spécification.")
    print("\nEt c'est ce qui rend le chapitre 6 possible : une sortie refusée")
    print("est un échec COMPTABILISABLE, pas une déception.")


if __name__ == "__main__":
    main()
