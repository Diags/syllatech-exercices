#!/usr/bin/env python3
"""Le harnais : envoyer un événement factice à un hook, et voir ce qu'il rend.

C'est l'outil qui change tout dans l'écriture d'un hook. Sans lui, on modifie
un script, on relance une session, on provoque l'action, on regarde… et on
recommence. Avec lui, la boucle dure une seconde.

    python outils/essayer.py <script> <evenement> [outil] [commande-ou-fichier]

Exemples :

    python outils/essayer.py .claude/hooks/garde_bash.py PreToolUse Bash "rm -rf /"
    python outils/essayer.py .claude/hooks/garde_bash.py PreToolUse Bash "ls -la"
    python outils/essayer.py .claude/hooks/formate.py PostToolUse Edit src/app.py

Ce qu'il affiche : le code de sortie, la sortie standard, la sortie d'erreur,
et surtout LA CONCLUSION — ce que Claude Code aurait fait de tout ça.
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path

# La console Windows est en cp1252 : un seul accent dans un message suffit a
# faire planter le script. Un hook qui plante est un hook qui ne protege plus,
# et rien ne vous le dit. Deux lignes, une fois, et le probleme disparait.
for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001 - deja en UTF-8, ou flux redirige
        pass


RACINE = Path(__file__).resolve().parent.parent

# Les événements qu'un code de sortie 2 peut bloquer. Le savoir évite d'écrire
# un « garde-fou » sur PostToolUse, qui ne bloquera jamais rien.
BLOQUABLES = {"PreToolUse", "UserPromptSubmit", "UserPromptExpansion",
              "Stop", "SubagentStop", "PreModelSwitch",
              "WorktreeCreate", "WorktreeRemove"}


def evenement(nom: str, outil: str, valeur: str) -> dict:
    """Reconstitue le JSON que Claude Code enverrait sur l'entrée standard."""
    base = {
        "session_id": str(uuid.uuid4()),
        "transcript_path": str(RACINE / ".claude" / "transcript-factice.jsonl"),
        "cwd": str(RACINE),
        "permission_mode": "default",
        "hook_event_name": nom,
    }
    if not outil:
        return base

    # Bash porte sa commande, les outils de fichier portent un chemin. Se
    # tromper de champ est l'erreur numéro un quand on écrit son premier hook.
    entree = {"command": valeur} if outil == "Bash" else {"file_path": valeur}
    base |= {"tool_name": outil, "tool_input": entree,
             "tool_use_id": "toolu_" + uuid.uuid4().hex[:16]}
    if nom.startswith("PostToolUse"):
        base["tool_response"] = "(réponse factice)"
    return base


def conclusion(nom: str, code: int, sortie: str, erreur: str) -> str:
    """Ce que Claude Code aurait fait — la seule ligne qui compte vraiment."""
    decision = None
    texte = sortie.strip()
    if texte.startswith("{") and texte.endswith("}"):
        try:
            specifique = json.loads(texte).get("hookSpecificOutput", {})
            decision = specifique.get("permissionDecision") or specifique.get("decision")
            raison = specifique.get("permissionDecisionReason") or specifique.get("reason")
        except json.JSONDecodeError:
            return "JSON invalide sur la sortie standard → erreur non bloquante, l'action passe"

    if decision == "deny":
        return f"ACTION REFUSÉE par le champ « permissionDecision » — {raison}"
    if decision == "allow":
        return "ACTION AUTORISÉE explicitement, sans demander à l'utilisateur"

    if code == 2:
        if nom in BLOQUABLES:
            return f"ACTION REFUSÉE par le code de sortie 2 — raison : {erreur.strip() or '(stderr vide)'}"
        return (f"code 2 IGNORÉ : l'événement {nom} n'est pas bloquable. "
                "Le hook croit refuser, et l'action passe quand même.")
    if code == 0:
        return "action laissée passer"
    return f"code {code} → erreur non bloquante, l'action passe"


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 1

    script = sys.argv[1]
    nom = sys.argv[2]
    outil = sys.argv[3] if len(sys.argv) > 3 else ""
    valeur = sys.argv[4] if len(sys.argv) > 4 else ""

    charge = evenement(nom, outil, valeur)
    r = subprocess.run([sys.executable, script], input=json.dumps(charge),
                       capture_output=True, text=True, encoding="utf-8", cwd=RACINE)

    print(f"── {script}  ←  {nom}" + (f" / {outil} / {valeur!r}" if outil else ""))
    print(f"   code de sortie : {r.returncode}")
    if r.stdout.strip():
        print("   sortie standard :")
        for l in r.stdout.strip().splitlines():
            print(f"      {l}")
    if r.stderr.strip():
        print("   sortie d'erreur :")
        for l in r.stderr.strip().splitlines():
            print(f"      {l}")
    print(f"\n   → {conclusion(nom, r.returncode, r.stdout, r.stderr)}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
