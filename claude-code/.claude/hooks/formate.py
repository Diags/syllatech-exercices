#!/usr/bin/env python3
"""PostToolUse — formater le fichier qui vient d'être édité.

⚠️ CE HOOK CORRIGE UNE ERREUR RÉPANDUE.

On lit souvent, y compris dans la vidéo de ce cours :

    "command": "npx eslint --fix $CLAUDE_FILE_PATHS"

**`CLAUDE_FILE_PATHS` n'existe pas.** Les seules variables d'environnement
fournies aux hooks sont `CLAUDE_PROJECT_DIR`, `CLAUDE_PLUGIN_ROOT`,
`CLAUDE_PLUGIN_DATA`, `CLAUDE_EFFORT`, `CLAUDE_CODE_REMOTE` et
`CLAUDE_CODE_BRIDGE_SESSION_ID`. La variable inconnue s'étend donc à la chaîne
vide, et la commande devient `npx eslint --fix` : le formateur ne reçoit aucun
fichier. Le hook ne fait rien, ne signale rien, et l'on croit son projet
formaté pendant des semaines. C'est la pire catégorie de bug.

Le chemin du fichier arrive **dans le JSON de l'entrée standard**, sous
`tool_input.file_path`. C'est ce que fait ce script.

    python outils/essayer.py .claude/hooks/formate.py PostToolUse Edit exemple.py
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001
        pass


# Un formateur par extension. Le premier disponible sur la machine gagne :
# inutile d'exiger que tout le monde installe la même chose.
FORMATEURS: dict[str, list[list[str]]] = {
    ".py": [["ruff", "format"], ["black"]],
    ".js": [["npx", "prettier", "--write"]],
    ".ts": [["npx", "prettier", "--write"]],
    ".jsx": [["npx", "prettier", "--write"]],
    ".tsx": [["npx", "prettier", "--write"]],
    ".json": [["npx", "prettier", "--write"]],
    ".md": [["npx", "prettier", "--write"]],
    ".css": [["npx", "prettier", "--write"]],
}


def main() -> int:
    try:
        evenement = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0

    # TODO : lire le chemin du fichier édité. Il N'EST PAS dans une variable d'environnement — relisez l'en-tête de ce fichier.
    chemin = ""
    if not chemin:
        # Edit et Write portent un file_path ; les autres outils, non. Sortir
        # sans rien faire est la bonne réponse — pas une erreur.
        return 0

    fichier = Path(chemin)
    if not fichier.exists():
        return 0

    candidats = FORMATEURS.get(fichier.suffix.lower(), [])
    for commande in candidats:
        if not shutil.which(commande[0]):
            continue
        r = subprocess.run([*commande, str(fichier)], capture_output=True, text=True)
        if r.returncode == 0:
            # PostToolUse ne peut RIEN bloquer : son rôle est d'agir, pas de
            # juger. On se contente d'informer, sur la sortie d'erreur, qui
            # n'apparaît qu'en mode debug.
            print(f"formaté : {fichier.name} ({commande[0]})", file=sys.stderr)
        else:
            print(f"{commande[0]} a échoué sur {fichier.name} : "
                  f"{r.stderr.strip()[:200]}", file=sys.stderr)
        return 0

    if candidats:
        print(f"aucun formateur installé pour {fichier.suffix} "
              f"(essayés : {', '.join(c[0] for c in candidats)})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
