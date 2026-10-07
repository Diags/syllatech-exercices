"""Un affichage sobre pour les scripts de chapitre."""

import json


def titre(numero: int, texte: str) -> None:
    print(f"\n{numero}. {texte.upper()}")
    print("-" * (len(texte) + 4))


def ligne(libelle: str, valeur) -> None:
    print(f"   {libelle:<42} {valeur}")


def json_court(donnees, limite: int = 400) -> str:
    texte = json.dumps(donnees, ensure_ascii=False)
    return texte if len(texte) <= limite else texte[:limite] + " …"
