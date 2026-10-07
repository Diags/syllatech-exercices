"""Chapitre 6 — Le mode sans tete, et ce qu'il faut border avant.

    uv run python chapitres/chapitre_6_production.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chapitres.chapitre_1_demarrer import utf8    # noqa: E402
from outils.verifier_config import verifier       # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    utf8()

    print("1. LE MODE SANS TETE\n")
    for ligne in (
            r'   claude -p "Relis le diff de cette PR. Liste bugs et failles." \\',
            r'       --allowedTools "Read,Grep,Glob" \\',
            r'       --output-format json \\',
            r'       --max-turns 5'):
        print(ligne.replace("\\\\", "\\"))
    print("\n   « -p » : pas d'interface, une reponse, puis on sort. C'est ce")
    print("   qui rend Claude Code utilisable dans une CI.")

    print("\n2. LES QUATRE DRAPEAUX QUI COMPTENT EN CI\n")
    for drapeau, pourquoi in (
            ("--allowedTools", "la liste blanche : sans elle, chaque outil demande"),
            ("--max-turns", "la borne : un agent qui boucle epuise le budget CI"),
            ("--output-format json", "pour que le pas suivant puisse lire le resultat"),
            ("--permission-mode", "ce qu'on autorise sans demander")):
        print(f"   {drapeau:<22}{pourquoi}")
    print("\n   « --allowed-tools » avec des tirets existe aussi : les deux")
    print("   orthographes fonctionnent.")

    print("\n3. LE DROIT D'ECRITURE EST UNE DECISION, PAS UN DEFAUT\n")
    print("   Read, Grep, Glob         relire une PR — aucun risque")
    print("   + Edit, Write            corriger — il faudra relire le diff")
    print("   + Bash                   tout — a n'accorder qu'en sachant")
    print("\n   Une revue de PR n'a pas besoin d'ecrire. Lui donner Edit")
    print("   « au cas ou » transforme un commentaire en commit.")

    print("\n4. LA VERIFICATION A BRANCHER AVANT LE RESTE\n")
    print("   # .github/workflows/claude.yml")
    print("   - run: uv run python outils/verifier_config.py --ci")
    print("   - run: claude -p \"...\" --allowedTools \"Read,Grep,Glob\"")
    print("\n   Dans cet ordre. Lancer un agent sur une configuration")
    print("   incoherente, c'est payer un appel pour un resultat fausse par un")
    print("   CLAUDE.md perime ou un hook mort.")

    propres = verifier(RACINE)
    pourries = verifier(RACINE / "config-pourrie")
    print(f"\n   cette configuration   {len(propres)} souci(s)  → la CI passe")
    print(f"   config-pourrie/       {len(pourries)} souci(s)  → la CI echoue")

    print("\n5. CE QU'UNE CI NE DOIT PAS FAIRE\n")
    for quoi, pourquoi in (
            ("committer sans relecture", "un agent qui pousse est un agent sans revue"),
            ("tourner sur chaque push", "le cout suit le nombre de commits, pas de PR"),
            ("--permission-mode bypassPermissions", "dans une CI, c'est un shell ouvert"),
            ("garder les secrets en clair", "les logs de CI sont lus par tout le monde")):
        print(f"   {quoi:<38}{pourquoi}")

    print("\n6. LE VRAI SUJET DE CE COURS\n")
    print("   Hooks, MCP, sous-agents, skills, CLAUDE.md : cinq mecanismes")
    print("   qui marchent bien separement, et qui pourrissent ENSEMBLE.")
    print("\n   Un hook survit a son script. Un CLAUDE.md documente une")
    print("   commande renommee. Une regle nomme un serveur retire. Aucun de")
    print("   ces defauts ne leve d'erreur, et aucune commande integree ne les")
    print("   cherche. C'est ce que fait outils/verifier_config.py — et c'est")
    print("   la seule piece de ce projet qui n'existe nulle part ailleurs.")


if __name__ == "__main__":
    main()
