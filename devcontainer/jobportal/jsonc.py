"""`devcontainer.json` n'est pas du JSON.

Le schéma publié le déclare lui-même, dans ses deux premières clés — et
elles ne disent PAS la même chose :

    "allowComments": true,
    "allowTrailingCommas": false

Les commentaires sont autorisés ; les virgules finales ne le sont **pas**.
C'est une nuance qui coûte cher, parce que la plupart des éditeurs les
tolèrent quand même : le fichier s'ouvre chez vous, et il est refusé
ailleurs. `virgules_finales()` les signale pour cette raison.

`json.load`, lui, refuse les deux. Un `devcontainer.json` commenté, qui
s'ouvre parfaitement dans l'éditeur, fait donc échouer le premier script de
vérification qu'on écrit — la panne la plus banale d'une CI qui veut relire
ce fichier, et la raison d'être de ce module.

Le lecteur retire les commentaires `//` et `/* */`, et tolère les virgules
finales pour pouvoir en parler. Il ne touche pas à ce qui est **dans une
chaîne** — c'est tout le travail, et c'est là que les lecteurs écrits à la
va-vite se trompent : une URL contient `//`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def sans_commentaires(texte: str) -> str:
    """Retire les commentaires JSONC en respectant les chaînes.

    Un automate à trois états suffit : dans une chaîne, dans un commentaire
    de ligne, dans un commentaire de bloc. L'échappement `\\"` compte, sinon
    `"il a dit \\"bonjour\\" // pas un commentaire"` se fait amputer.
    """
    # >>> depart: retirer les commentaires SANS toucher a ce qui est dans une chaine
    #     return "\n".join(l.split("//")[0] for l in texte.splitlines())
    sortie = []
    dans_chaine = False
    echappe = False
    i, n = 0, len(texte)
    while i < n:
        c = texte[i]
        if dans_chaine:
            sortie.append(c)
            if echappe:
                echappe = False
            elif c == "\\":
                echappe = True
            elif c == '"':
                dans_chaine = False
            i += 1
            continue
        if c == '"':
            dans_chaine = True
            sortie.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and texte[i + 1] == "/":
            while i < n and texte[i] != "\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and texte[i + 1] == "*":
            fin = texte.find("*/", i + 2)
            i = n if fin == -1 else fin + 2
            continue
        sortie.append(c)
        i += 1
    return "".join(sortie)
    # <<<


def sans_virgules_finales(texte: str) -> str:
    """Retire les virgules qui precedent un `}` ou un `]`.

    Meme precaution : on ne touche pas a ce qui est dans une chaine.
    """
    sortie: list[str] = []
    dans_chaine = False
    echappe = False
    for i, c in enumerate(texte):
        if dans_chaine:
            sortie.append(c)
            if echappe:
                echappe = False
            elif c == "\\":
                echappe = True
            elif c == '"':
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
            sortie.append(c)
            continue
        if c == ",":
            reste = texte[i + 1:].lstrip()
            if reste[:1] in ("}", "]"):
                continue          # virgule finale : on la jette
        sortie.append(c)
    return "".join(sortie)


def charger_texte(texte: str) -> Any:
    """Lit du JSONC. C'est ce que fait l'outil ; `json.load` ne le fait pas."""
    return json.loads(sans_virgules_finales(sans_commentaires(texte)))


def charger(chemin: Path | str) -> Any:
    return charger_texte(Path(chemin).read_text(encoding="utf-8"))


def virgules_finales(texte: str) -> list[int]:
    """Les numeros de ligne des virgules finales.

    Le schema publie declare `allowTrailingCommas: false` : elles ne sont
    pas autorisees. Beaucoup d'editeurs les acceptent malgre tout, et c'est
    precisement ce qui les rend dangereuses — le fichier marche chez vous.
    """
    # >>> depart: relever les virgules qui precedent un } ou un ]
    #     return []
    propre = sans_commentaires(texte)
    lignes = []
    dans_chaine = False
    echappe = False
    ligne = 1
    for i, c in enumerate(propre):
        if c == "\n":
            ligne += 1
        if dans_chaine:
            if echappe:
                echappe = False
            elif c == "\\":
                echappe = True
            elif c == '"':
                dans_chaine = False
            continue
        if c == '"':
            dans_chaine = True
            continue
        if c == "," and propre[i + 1:].lstrip()[:1] in ("}", "]"):
            lignes.append(ligne)
    return lignes
    # <<<


def est_du_json_strict(texte: str) -> bool:
    """Le fichier passerait-il un `json.loads` ordinaire ?

    Sert au chapitre 1 : la reponse est « non » pour la plupart des vrais
    `devcontainer.json`, et c'est une surprise.
    """
    try:
        json.loads(texte)
        return True
    except json.JSONDecodeError:
        return False
