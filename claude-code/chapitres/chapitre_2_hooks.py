"""Chapitre 2 — Les hooks : deux defauts qui ne disent rien.

    uv run python chapitres/chapitre_2_hooks.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chapitres.chapitre_1_demarrer import utf8       # noqa: E402
from outils.verifier_config import EVENEMENTS, verifier_hooks  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    utf8()
    reglages = json.loads((RACINE / ".claude" / "settings.json")
                          .read_text(encoding="utf-8"))

    print("1. LES HOOKS DE CE PROJET\n")
    for evenement, entrees in reglages["hooks"].items():
        for entree in entrees:
            for hook in entree["hooks"]:
                print(f"   {evenement:<14}{entree['matcher']:<14}{hook['command'][:52]}")

    print("\n2. LE MATCHER EST UNE EXPRESSION REGULIERE\n")
    print("   « Edit|Write »   les deux outils d'ecriture")
    print("   « Bash »          uniquement Bash")
    print("   « .* »            tout — rarement ce qu'on veut")
    print("\n   Un matcher trop large fait tourner votre script a chaque")
    print("   action de l'agent. C'est la premiere cause de session lente.")

    print(f"\n3. PREMIER DEFAUT MUET : L'EVENEMENT MAL ORTHOGRAPHIE\n")
    print(f"   evenements valides : {', '.join(sorted(EVENEMENTS))}")
    casse = {"hooks": {"PreToolUsage": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "echo x"}]}]}}
    for souci in verifier_hooks(RACINE, casse):
        print(f"\n   {souci.gravite.upper()} : {souci.message[:88]}")
    print("\n   « PreToolUsage » au lieu de « PreToolUse » : le hook est")
    print("   accepte, enregistre, et ne se declenche JAMAIS. Aucune erreur,")
    print("   aucun avertissement — on croit son projet protege.")

    print("\n4. SECOND DEFAUT MUET : LE SCRIPT DISPARU\n")
    casse = {"hooks": {"PreToolUse": [{"matcher": "Bash", "hooks": [
        {"type": "command", "command": "python .claude/hooks/supprime.py"}]}]}}
    for souci in verifier_hooks(RACINE, casse):
        print(f"   {souci.gravite.upper()} : {souci.message[:86]}")
    print("\n   Le hook survit au script. Il echoue alors a chaque")
    print("   declenchement, et l'echec d'un hook ne remonte pas toujours")
    print("   jusqu'a vous. C'est le defaut le plus courant d'un .claude/")
    print("   ancien, et il est invisible a la relecture.")

    print("\n5. LE CHEMIN DU SCRIPT\n")
    commande = reglages["hooks"]["PostToolUse"][0]["hooks"][0]["command"]
    print(f"   {commande}")
    print("\n   « $CLAUDE_PROJECT_DIR » et non un chemin relatif : un hook")
    print("   s'execute depuis le dossier courant de l'agent, qui n'est pas")
    print("   forcement la racine du projet. Un chemin relatif marche tant")
    print("   qu'on ne fait pas « cd » dans la session.")

    print("\n6. CE QUE LE HOOK RECOIT, ET CE QU'IL REND\n")
    print("   entree  : le JSON de l'evenement, sur stdin")
    print("            tool_input.file_path, tool_input.command, cwd…")
    print("   sortie  : code 2 = bloque et montre stderr a l'agent")
    print("            JSON avec permissionDecision = « deny » + une raison")
    print("\n   La seconde forme est meilleure : la raison arrive dans un")
    print("   champ prevu pour elle, et l'agent peut proposer autre chose au")
    print("   lieu de reessayer la meme commande.")


if __name__ == "__main__":
    main()
