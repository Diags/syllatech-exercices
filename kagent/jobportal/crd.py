"""Valider un manifeste contre un schema structurel — et voir ce qui est ELAGUE.

CE QU'UNE CRD EST VRAIMENT
--------------------------
Une `CustomResourceDefinition` n'ajoute pas seulement un genre d'objet : elle
ajoute un **schema structurel** que l'API applique a chaque `kubectl apply`.
Ce schema fait deux choses, et la seconde surprend tout le monde :

1. il **refuse** ce qui viole le schema — un type faux, un champ obligatoire
   absent, une valeur hors de l'`enum` ;
2. il **ELAGUE en silence** ce qu'il ne connait pas. Un champ dont le nom
   comporte une faute de frappe n'est pas signale : il est simplement retire
   de l'objet stocke. `kubectl apply` repond « configured », et votre agent
   tourne avec un prompt vide.

⚠️ C'EST LA MESURE DU CHAPITRE 2, et c'est la raison pour laquelle on relit
toujours l'objet tel que l'API l'a STOCKE (`kubectl get -o yaml`), jamais le
fichier qu'on a envoye.

CE QUI EST SUPPORTE
-------------------
`type` (object, array, string, integer, boolean), `required`, `properties`,
`items`, `enum`, `pattern`, `minimum`/`maximum`, `default`, et
`x-kubernetes-validations` — les regles transverses que Kubernetes evalue en
CEL, ici reduites a un petit langage de predicats nommes.

CE QUI NE L'EST PAS
-------------------
`oneOf` / `anyOf` / `allOf` libres, les schemas recursifs, `$ref`, et CEL
dans sa generalite. Chacun leve plutot que d'etre ignore — un validateur qui
laisse passer ce qu'il ne comprend pas ne valide rien.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable


class ErreurSchema(Exception):
    """Un schema non gere, ou une regle inconnue."""


@dataclass
class Probleme:
    chemin: str
    message: str

    def __str__(self) -> str:
        return f"{self.chemin} : {self.message}"


@dataclass
class Verdict:
    """Le resultat d'une admission : ce qui est refuse, ce qui est elague."""

    valide: bool
    objet: dict[str, Any]
    problemes: list[Probleme] = field(default_factory=list)
    elagues: list[str] = field(default_factory=list)

    @property
    def silencieux(self) -> bool:
        """⚠️ Admis, et pourtant ampute. Le pire des deux mondes."""
        return self.valide and bool(self.elagues)

    def __str__(self) -> str:
        if not self.valide:
            return "refuse : " + " ; ".join(str(p) for p in self.problemes)
        if self.elagues:
            return f"admis, {len(self.elagues)} champ(s) elague(s) en silence"
        return "admis"


# ── les regles transverses ───────────────────────────────────────────────
#
# Kubernetes les ecrit en CEL dans `x-kubernetes-validations`. Ici, chaque
# regle est une fonction nommee, declaree une fois — c'est moins general et
# c'est lisible, ce qui est le but d'un cours.

REGLES: dict[str, tuple[Callable[[dict[str, Any]], bool], str]] = {
    "declaratif-exige-declarative": (
        lambda o: o.get("type") != "Declarative" or "declarative" in o,
        "un agent de type « Declarative » doit porter un bloc « declarative »"),
    "byo-exige-byo": (
        lambda o: o.get("type") != "BYO" or "byo" in o,
        "un agent de type « BYO » doit porter un bloc « byo »"),
    "un-seul-corps": (
        lambda o: not ("declarative" in o and "byo" in o),
        "« declarative » et « byo » sont exclusifs"),
    "url-exigee-si-http": (
        lambda o: o.get("protocol") not in ("STREAMABLE_HTTP", "SSE")
        or bool(o.get("url")),
        "un serveur en HTTP streamable ou SSE doit declarer une « url »"),
}


# ── la validation ────────────────────────────────────────────────────────

def _type_python(attendu: str) -> tuple[type, ...]:
    return {
        "object": (dict,),
        "array": (list,),
        "string": (str,),
        "integer": (int,),
        "number": (int, float),
        "boolean": (bool,),
    }[attendu]


_NON_GERES = ("oneOf", "anyOf", "allOf", "$ref", "not")


def valider(schema: dict[str, Any], objet: Any,
            chemin: str = "") -> tuple[Any, list[Probleme], list[str]]:
    """Rend (objet elague, problemes, champs elagues)."""
    for cle in _NON_GERES:
        if cle in schema:
            raise ErreurSchema(
                f"{chemin or '.'} : « {cle} » n'est pas gere par ce validateur")

    attendu = schema.get("type")
    problemes: list[Probleme] = []
    elagues: list[str] = []

    if attendu and attendu in ("object", "array", "string", "integer",
                               "number", "boolean"):
        classes = _type_python(attendu)
        # ⚠️ En Python, `True` est un `int`. Sans ce garde-fou, un booleen
        # passerait pour un entier — et le schema ne verrait rien.
        mauvais = (not isinstance(objet, classes)
                   or (attendu in ("integer", "number")
                       and isinstance(objet, bool)))
        if mauvais:
            problemes.append(Probleme(
                chemin or ".",
                f"« {attendu} » attendu, {type(objet).__name__} recu"))
            return objet, problemes, elagues

    if attendu == "object":
        proprietes = schema.get("properties") or {}
        resultat: dict[str, Any] = {}

        # TODO : valider chaque propriete connue, et ELAGUER les autres
        return objet, problemes, elagues

    if attendu == "array":
        interne = schema.get("items") or {}
        resultat_liste = []
        for rang, element in enumerate(objet):
            sous, sous_problemes, sous_elagues = valider(
                interne, element, f"{chemin}[{rang}]")
            resultat_liste.append(sous)
            problemes.extend(sous_problemes)
            elagues.extend(sous_elagues)
        return resultat_liste, problemes, elagues

    if "enum" in schema and objet not in schema["enum"]:
        problemes.append(Probleme(
            chemin or ".",
            f"« {objet} » hors de l'enumeration {schema['enum']}"))

    if "pattern" in schema and isinstance(objet, str):
        if not re.fullmatch(schema["pattern"], objet):
            problemes.append(Probleme(
                chemin or ".",
                f"« {objet} » ne correspond pas au motif "
                f"« {schema['pattern']} »"))

    if "minimum" in schema and isinstance(objet, (int, float)):
        if objet < schema["minimum"]:
            problemes.append(Probleme(
                chemin or ".", f"{objet} < minimum {schema['minimum']}"))

    if "maximum" in schema and isinstance(objet, (int, float)):
        if objet > schema["maximum"]:
            problemes.append(Probleme(
                chemin or ".", f"{objet} > maximum {schema['maximum']}"))

    return objet, problemes, elagues


def admettre(schema: dict[str, Any], manifeste: dict[str, Any]) -> Verdict:
    """Ce que l'API fait d'un manifeste : valide, elague, puis stocke."""
    objet, problemes, elagues = valider(schema, manifeste)
    return Verdict(not problemes, objet, problemes, elagues)
