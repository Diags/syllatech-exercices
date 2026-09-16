"""Les règles d'autorisation, évaluées pour de bon.

`mcpAuthorization` (et `authorization`, et `networkAuthorization`) pointent
tous vers le même `RuleSet` : une liste de règles CEL. Le schéma publié
décrit chaque forme, et sa description de `deny` vaut d'être citée en entier :

    allow    « Allow the request when this CEL expression is true. »
    require  « Require this CEL expression to be true. »
    deny     « Deny the request when this CEL expression is true. This mode
               is not recommended because expression failures fail to deny;
               prefer `Allow` or `Require`. If used, design expressions
               defensively against evaluation errors. »

Une règle peut aussi s'écrire en chaîne nue — c'est ce que font les exemples
du dépôt — et vaut alors `allow`.

⚠️ **La composition des trois formes n'est pas écrite dans le schéma.** Ce
module applique celle-ci, et le dit plutôt que de la faire passer pour la
vérité : tous les `require` doivent être vrais, aucun `deny` ne doit l'être,
et s'il existe au moins un `allow`, l'un d'eux doit être vrai. Le contexte
CEL, lui, est documenté : `amont/cel.md` en liste chaque champ.

Ce qui est réel ici : les expressions sont compilées et évaluées par
`cel-python`. Une règle qui ne compile pas est une règle qui, sur le proxy,
empêcherait le démarrage ; une règle qui lève à l'évaluation est le piège
que la citation ci-dessus annonce, et le chapitre 5 le mesure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from jobportal.modeles import ErreurDeCEL, evaluer

FORMES = ("allow", "require", "deny")


@dataclass(frozen=True)
class Regle:
    forme: str
    expression: str

    def __str__(self) -> str:
        return f"{self.forme}: {self.expression}"


def lire(brut: Any) -> list[Regle]:
    """Lit un `RuleSet` — une liste où chaque entrée est un objet ou une chaîne."""
    if isinstance(brut, dict):
        brut = brut.get("rules")
    regles = []
    for entree in brut or []:
        if isinstance(entree, str):
            regles.append(Regle("allow", entree))
        elif isinstance(entree, dict):
            forme = next((f for f in FORMES if f in entree), None)
            if forme:
                regles.append(Regle(forme, entree[forme]))
    return regles


@dataclass
class Verdict:
    autorise: bool
    motif: str
    evaluations: list[tuple[Regle, Any]] = field(default_factory=list)

    def __str__(self) -> str:
        return ("AUTORISE" if self.autorise else "REFUSE") + f" — {self.motif}"


def _evaluer(regle: Regle, contexte: dict[str, Any]) -> Any:
    """Rend True, False, ou l'exception — c'est le troisième cas qui compte."""
    try:
        return evaluer(regle.expression, contexte)
    except ErreurDeCEL as erreur:
        return erreur


def decider(regles: list[Regle], contexte: dict[str, Any]) -> Verdict:
    """Applique un jeu de règles à un contexte.

    Une expression qui LÈVE est traitée comme « non vraie », ce qui est le
    comportement sûr pour `allow` et `require` — et exactement le trou que
    le schéma signale pour `deny`.
    """
    evaluations = [(r, _evaluer(r, contexte)) for r in regles]

    # TODO : composer les trois formes — tout `require` vrai, aucun `deny` vrai, un `allow` vrai
    return Verdict(True, "a completer", evaluations)


def contexte_mcp(nom_de_l_outil: str, cible: str = "",
                 claims: dict[str, Any] | None = None,
                 methode: str = "tools/call") -> dict[str, Any]:
    """Le contexte CEL d'un appel d'outil MCP, tel qu'`amont/cel.md` le décrit.

    Deux champs à retenir : `mcp.tool.name` est « the RESOLVED tool name sent
    to the upstream target » — donc après résolution du multiplexage — et
    `mcp.tool.target` est « the target handling the tool call after
    multiplexing resolution ». Une règle écrite sur le nom préfixé regarde
    donc le mauvais champ ; le chapitre 5 le mesure.
    """
    mcp: dict[str, Any] = {"methodName": methode,
                           "tool": {"name": nom_de_l_outil}}
    if cible:
        mcp["tool"]["target"] = cible
    contexte: dict[str, Any] = {"mcp": mcp}
    if claims is not None:
        contexte["jwt"] = claims
    return contexte


def compile_t_elle(expression: str) -> tuple[bool, str]:
    """Une règle qui ne compile pas empêche le proxy de démarrer."""
    try:
        evaluer(expression, {"jwt": {}, "mcp": {"tool": {"name": ""}}})
        return True, ""
    except ErreurDeCEL as erreur:
        message = str(erreur)
        # Une erreur d'EVALUATION (clé absente) n'est pas une erreur de
        # COMPILATION : la distinction est tout le sujet du chapitre 5.
        if "no such member" in message or "no such key" in message:
            return True, ""
        return False, message


def defensive(expression: str) -> bool:
    """L'expression se garde-t-elle des champs absents ?

    « design expressions defensively against evaluation errors » — en CEL,
    cela s'écrit `has(...)` ou `default(...)`. Les exemples amont utilisent
    les deux.
    """
    return "has(" in expression or "default(" in expression
