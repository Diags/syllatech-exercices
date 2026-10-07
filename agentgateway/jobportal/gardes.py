"""Les guardrails de contenu : des expressions régulières, et leurs limites.

`policies.ai.promptGuard` a la forme suivante dans le schéma publié :

    promptGuard:
      request:  [ {regex: {action, rules}, rejection: {...}}, … ]
      response: [ … ]

`action` vaut **`mask` par défaut** — pas `reject`. Une règle écrite sans
`action` masque donc la donnée et laisse passer la requête. C'est le défaut
le plus discret de tout le schéma, et le chapitre 5 le mesure.

`rules` accepte deux formes : `{pattern: "<regex>"}` et `{builtin: "<nom>"}`.
Les cinq builtins sont énumérés dans le schéma : `ssn`, `creditCard`,
`phoneNumber`, `email`, `caSin`.

⚠️ **Les motifs de ces builtins ne sont PAS publiés** — ils vivent dans le
code Rust. Ceux de ce module sont donc les MIENS, écrits à la main, et c'est
volontaire : la leçon du chapitre 5 n'est pas « voici les bons motifs », mais
« un garde-fou de contenu est une expression régulière, et voici ce qu'une
expression régulière rate ». On le mesure sur un corpus.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# Les cinq noms sont ceux du schema (definition « Builtin »). Les motifs sont
# de ce projet. Ne pas les prendre pour ceux d'agentgateway.
BUILTINS: dict[str, str] = {
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "creditCard": r"\b(?:\d[ -]?){13,19}\b",
    "phoneNumber": r"\b(?:\+?\d{1,3}[ .-]?)?(?:\(?\d{2,4}\)?[ .-]?){2,4}\d{2,4}\b",
    "email": r"\b[\w.%+-]+@[\w.-]+\.[A-Za-z]{2,}\b",
    "caSin": r"\b\d{3}[ -]?\d{3}[ -]?\d{3}\b",
}

# RegexRules.action — « default: "mask" ».
ACTION_PAR_DEFAUT = "mask"


@dataclass
class Constat:
    """Ce qu'un garde a trouvé, et ce qu'il en a fait."""

    declenche: bool
    action: str
    motifs: list[str]
    texte: str

    @property
    def bloque(self) -> bool:
        return self.declenche and self.action == "reject"

    @property
    def masque(self) -> bool:
        return self.declenche and self.action == "mask"


def motif_de(regle: dict[str, Any]) -> tuple[str, str]:
    """Rend (etiquette, motif) pour une RegexRule."""
    if "builtin" in regle:
        nom = regle["builtin"]
        return f"builtin:{nom}", BUILTINS.get(nom, "")
    if "pattern" in regle:
        return f"pattern:{regle['pattern']}", regle["pattern"]
    return "(inconnue)", ""


def builtins_inconnus(regles: list[dict[str, Any]]) -> list[str]:
    """Les `builtin:` qui ne sont pas dans l'énumération du schéma.

    Le schéma les refuse : `agentgateway --file` ne démarrerait pas. Autant
    le dire avant.
    """
    return [r["builtin"] for r in regles
            if isinstance(r, dict) and "builtin" in r
            and r["builtin"] not in BUILTINS]


def appliquer(bloc_regex: dict[str, Any], texte: str) -> Constat:
    """Applique un bloc `regex` — action comprise, défaut compris."""
    action = (bloc_regex or {}).get("action", ACTION_PAR_DEFAUT)
    # TODO : appliquer chaque motif, et masquer quand l'action le demande
    return Constat(False, action, [], texte)


def gardes_de(politiques: dict[str, Any], sens: str = "request") -> list[dict[str, Any]]:
    """Les gardes d'une route, lus au bon endroit.

    Le chemin est `policies.ai.promptGuard.<sens>`, et c'est une LISTE. Ni
    `policies.promptGuard`, ni un objet unique : la forme se vérifie dans
    `amont/exemples/llm-prompt-guard.yaml`.
    """
    ia = (politiques or {}).get("ai")
    if not isinstance(ia, dict):
        return []
    garde = ia.get("promptGuard")
    if not isinstance(garde, dict):
        return []
    entrees = garde.get(sens)
    return [e for e in entrees if isinstance(e, dict)] if isinstance(entrees, list) else []


def passer(politiques: dict[str, Any], texte: str,
           sens: str = "request") -> list[Constat]:
    """Fait passer un texte dans tous les gardes d'une route."""
    constats = []
    for entree in gardes_de(politiques, sens):
        bloc = entree.get("regex")
        if isinstance(bloc, dict):
            constats.append(appliquer(bloc, texte))
    return constats


def mesurer(bloc_regex: dict[str, Any],
            corpus: list[tuple[str, bool]]) -> dict[str, int]:
    """Compte vrais/faux positifs et négatifs sur un corpus étiqueté.

    `corpus` est une liste de (texte, contient-il vraiment une donnee
    sensible). C'est la seule façon honnête de parler d'un garde-fou : un
    taux, pas une promesse.
    """
    compte = {"vrai positif": 0, "faux positif": 0,
              "vrai negatif": 0, "faux negatif": 0}
    for texte, sensible in corpus:
        touche = appliquer(bloc_regex, texte).declenche
        if sensible and touche:
            compte["vrai positif"] += 1
        elif sensible and not touche:
            compte["faux negatif"] += 1
        elif not sensible and touche:
            compte["faux positif"] += 1
        else:
            compte["vrai negatif"] += 1
    return compte
