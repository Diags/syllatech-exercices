"""Gateway — une spécification OpenAPI devient un catalogue d'outils MCP.

Le cours montre la commande :

    aws bedrock-agentcore-control create-gateway-target \\
      --target-configuration '{"openApiSchema": {"s3": {"uri": "…"}}}'

Ce qu'elle fait, elle le fait chez AWS. Ce qu'elle PRODUIT — un outil MCP par
opération, avec son schéma d'entrée — se dérive de la spécification, et c'est
ce que fait ce module. On peut donc mesurer ce que le cours affirme : qu'un
grand catalogue noierait le modèle, et que la recherche sémantique le sauve.

CE QUI EST SUBSTITUÉ

La Gateway elle-même : l'endpoint MCP managé, l'authentification entrante et
sortante, et l'appel réel de l'API cible. Ce qui est réel : la dérivation
opération → outil, et le coût en contexte, qui se compte.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

VERBES = {"get": "Lire", "post": "Creer", "put": "Remplacer",
          "patch": "Modifier", "delete": "Supprimer"}


@dataclass
class Outil:
    """La forme d'un outil MCP : un nom, une description, un schéma."""

    nom: str
    description: str
    schema: dict

    def en_json(self) -> str:
        return json.dumps({"name": self.nom, "description": self.description,
                           "inputSchema": self.schema}, ensure_ascii=False)


def depuis_openapi(spec: dict) -> list[Outil]:
    """Une opération OpenAPI → un outil MCP.

    C'est la seule chose que la Gateway fait de magique, et elle n'est pas
    magique : `operationId` devient le nom, `summary` la description, et les
    paramètres le schéma d'entrée. Écrire cela à la main pour 40 opérations
    est le travail que la Gateway supprime.
    """
    # >>> depart: une operation OpenAPI par outil MCP. Le nom vient de operationId — et, a defaut, de _nom_deduit, ce qui peut produire des DOUBLONS ; la description vient de summary ; les parametres deviennent le schema d'entree, ceux marques required allant dans la liste « required ». Cinq tests le verifient.
    #     return [Outil("aEcrire", "a ecrire",
    #                   {"type": "object", "properties": {}, "required": []})]
    outils = []
    for chemin, operations in spec.get("paths", {}).items():
        for methode, operation in operations.items():
            if methode not in VERBES:
                continue
            proprietes, requis = {}, []
            for parametre in operation.get("parameters", []):
                proprietes[parametre["name"]] = {
                    "type": parametre.get("schema", {}).get("type", "string"),
                    "description": parametre.get("description", "")}
                if parametre.get("required"):
                    requis.append(parametre["name"])
            outils.append(Outil(
                nom=operation.get("operationId")
                or _nom_deduit(methode, chemin),
                description=operation.get("summary")
                or f"{VERBES[methode]} {chemin}",
                schema={"type": "object", "properties": proprietes,
                        "required": requis}))
    return outils
    # <<<


def depuis_lambda(nom: str, description: str, schema: dict) -> Outil:
    """Une fonction Lambda → un outil. Le schéma est le vôtre."""
    return Outil(nom=nom, description=description, schema=schema)


def _nom_deduit(methode: str, chemin: str) -> str:
    """Sans `operationId`, la Gateway doit inventer un nom.

    ⚠️ Et deux chemins voisins peuvent alors produire le MÊME nom — auquel cas
    un outil en masque un autre. `doublons()` les signale : c'est la première
    chose à vérifier sur une spécification qu'on n'a pas écrite.
    """
    morceaux = [m for m in re.split(r"[/{}]+", chemin) if m]
    return methode + "".join(m.capitalize() for m in morceaux)


def doublons(outils: list[Outil]) -> list[str]:
    vus, repetes = set(), []
    for outil in outils:
        (repetes.append(outil.nom) if outil.nom in vus else vus.add(outil.nom))
    return sorted(set(repetes))


# ------------------------------------------- ce que le catalogue coûte

def cout_en_jetons(outils: list[Outil]) -> int:
    """Une approximation, et elle est annoncée comme telle.

    Un jeton vaut à peu près quatre signes en anglais, un peu moins en
    français. Ce module compte donc des signes et divise par quatre. L'ordre
    de grandeur suffit pour la seule chose qui compte ici : le RAPPORT entre
    un catalogue entier et une sélection.
    """
    return sum(len(o.en_json()) for o in outils) // 4


# ------------------------------------------------ la recherche d'outils

MOTS_VIDES = {"le", "la", "les", "un", "une", "des", "de", "du", "pour",
              "avec", "dans", "sur", "et", "ou", "a", "au", "aux", "par"}


def _mots(texte: str) -> set[str]:
    return {m for m in re.findall(r"\w{3,}", texte.lower())
            if m not in MOTS_VIDES}


def chercher(outils: list[Outil], requete: str, combien: int = 5) -> list[Outil]:
    """Ce que fait la recherche sémantique de la Gateway, en plus bête.

    ⚠️ La vraie utilise des plongements vectoriels : elle rapproche « poste »
    de « emploi » sans qu'aucun mot ne soit commun. Celle-ci compte les mots
    partagés — elle rate donc les synonymes, et le chapitre 4 le mesure.

    Ce que les deux ont en commun, et qui est le point du cours : elles ne
    présentent au modèle que quelques outils, pas le catalogue.
    """
    demandes = _mots(requete)
    notes = []
    for outil in outils:
        cible = _mots(f"{outil.nom} {outil.description}")
        note = len(demandes & cible)
        if note:
            notes.append((note, outil.nom, outil))
    notes.sort(key=lambda x: (-x[0], x[1]))
    return [o for _, _, o in notes[:combien]]
