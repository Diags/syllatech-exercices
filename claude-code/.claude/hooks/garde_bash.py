#!/usr/bin/env python3
"""PreToolUse — le garde-fou : refuser une commande avant qu'elle ne parte.

Claude Code envoie l'événement en JSON sur l'entrée standard. Ce que le hook
rend décide du sort de l'action :

    sortie 0   l'action passe
    sortie 2   l'action est REFUSEE ; stderr est montré à Claude et à vous
    autre      erreur non bloquante : l'action passe quand même

Deux façons de refuser, et ce script montre les deux :

  · le code de sortie 2, court et suffisant ;
  · un objet JSON sur la sortie standard, plus précis — il permet de dire
    « deny » avec une raison, ou même de RÉÉCRIRE la commande.

Tester sans lancer Claude Code :

    python outils/essayer.py .claude/hooks/garde_bash.py PreToolUse Bash "rm -rf /"
"""

from __future__ import annotations

import json
import re
import sys

# La console Windows est en cp1252 : un seul accent dans un message suffit a
# faire planter le script. Un hook qui plante est un hook qui ne protege plus,
# et rien ne vous le dit. Deux lignes, une fois, et le probleme disparait.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001 - deja en UTF-8, ou flux redirige
        pass


# Des motifs, pas des chaînes : « rm  -rf » avec deux espaces passerait au
# travers d'un simple `in`, et c'est exactement ce qu'un agent finira par
# écrire un jour.
# >>> depart: écrire les motifs à refuser, en expressions régulières. Les tests de tests/test_hooks.py disent lesquels — et lesquels doivent PASSER.
#     INTERDITS: list[tuple[str, str]] = [
#         # (motif, explication montrée à Claude)
#     ]
INTERDITS: list[tuple[str, str]] = [
    (r"\brm\s+-[a-z]*[rf]", "suppression récursive ou forcée"),
    (r"\bdrop\s+(table|database)\b", "suppression de schéma SQL"),
    (r"\bgit\s+push\b.*--force(?!-with-lease)", "push forcé sans --force-with-lease"),
    (r"\bgit\s+reset\s+--hard\b", "réinitialisation destructive"),
    (r":\(\)\s*\{.*\}\s*;\s*:", "bombe de forks"),
    (r"\bchmod\s+777\b", "permissions 777"),
    (r"\bcurl\b[^|]*\|\s*(ba)?sh", "script distant exécuté sans relecture"),
]
# <<<


def refuser(raison: str) -> None:
    """Refus par la sortie riche : une décision et une raison, sans ambiguïté.

    L'avantage sur le simple code 2 : la raison arrive dans un champ prévu
    pour ça, et non mêlée au flux d'erreur. Claude la lit et peut proposer
    autre chose au lieu de réessayer la même commande.
    """
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": raison,
        }
    }, ensure_ascii=False))
    sys.exit(0)   # la décision est dans le JSON, pas dans le code de sortie


def main() -> int:
    try:
        evenement = json.load(sys.stdin)
    except json.JSONDecodeError:
        # Entrée illisible : on ne bloque pas. Un garde-fou qui casse sur une
        # entrée inattendue bloquerait tout le travail, ce qui est pire que
        # de laisser passer une commande.
        print("garde_bash : entrée JSON illisible, action laissée passer", file=sys.stderr)
        return 0

    commande = (evenement.get("tool_input") or {}).get("command", "")
    if not commande:
        return 0

    for motif, explication in INTERDITS:
        if re.search(motif, commande, re.IGNORECASE):
            refuser(f"Commande refusée par .claude/hooks/garde_bash.py — "
                    f"{explication}. Commande : {commande.strip()[:120]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
