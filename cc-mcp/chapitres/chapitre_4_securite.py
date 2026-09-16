"""Chapitre 4 — Permissions : la regle qui ne protege rien, et ne le dit pas.

    uv run python chapitres/chapitre_4_securite.py

Le chapitre le plus important du cours, et celui ou une faute de frappe ne
produit aucun message.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

from jobportal import console                              # noqa: E402
from verifier_acces import correspond, outils_reels, verifier  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    console.utf8()
    reels = outils_reels()

    print("1. LA PRECEDENCE : deny, puis ask, puis allow\n")
    print("   Les regles s'evaluent DANS CET ORDRE, et la premiere qui")
    print("   correspond decide. La specificite ne change rien : un deny large")
    print("   l'emporte sur un allow precis. Une regle deny ne peut donc pas")
    print("   porter d'exception — il faut la restreindre, pas l'annoter.\n")
    exemples = [
        ("deny  mcp__jobportal__*", "allow mcp__jobportal__rechercher_offres",
         "REFUSE : le deny large gagne"),
        ("deny  mcp__jobportal__supprimer_offre", "allow mcp__jobportal__*",
         "AUTORISE sauf la suppression — la bonne forme"),
    ]
    for refus, autorisation, issue in exemples:
        print(f"   {refus:<38}{autorisation}")
        print(f"     → {issue}")

    print("\n2. LE GLOB EST UN GLOB, PAS UNE EXPRESSION REGULIERE\n")
    outil = "mcp__jobportal__rechercher_offres"
    for regle in ("mcp__jobportal__*", "mcp__jobportal__.*", "mcp__jobportal__recherche*"):
        print(f"   {regle:<34}{'correspond' if correspond(regle, outil) else 'NE CORRESPOND PAS'}")
    print("\n   La forme « .* » vient des matchers de hooks, qui sont des")
    print("   expressions regulieres. Les regles de permission, elles, sont")
    print("   des globs. Une regle « mcp__jobportal__.* » ne correspond qu'a")
    print("   un outil litteralement nomme « .quelquechose » — donc a rien.")

    print("\n3. LE DEFAUT QUI NE DIT RIEN\n")
    casse = json.loads((RACINE / "config-a-corriger" / ".claude" / "settings.json")
                       .read_text(encoding="utf-8"))
    faute = casse["permissions"]["deny"][0]
    print(f"   Regle ecrite   : {faute}")
    print(f"   Outil reel     : mcp__jobportal__supprimer_offre")
    print(f"   Correspond ?     {'oui' if any(correspond(faute, o) for o in reels) else 'NON'}")
    print("\n   Ce que dit la documentation des permissions :\n")
    print("     « A deny or ask rule whose tool name matches no known tool")
    print("       produces a startup warning to catch typos. Tool names")
    print("       containing `_` or `*` are exempt from the check. »\n")
    print("   Or TOUT nom d'outil MCP contient « _ » : il commence par")
    print("   « mcp__ ». Les regles MCP sont donc exemptes du controle.")
    print("   Resultat : aucun avertissement, la regle ne correspond a rien,")
    print("   et l'outil de suppression reste autorise.")
    print("\n   C'est la meme famille de defaut que la variable de hook qui")
    print("   n'existe pas : il ne casse rien, il ne dit rien, il reussit en")
    print("   apparence. On le decouvre le jour ou l'agent supprime une offre.")

    print("\n4. LE VERIFICATEUR — quinze lignes, et un angle mort en moins\n")
    for dossier, titre in ((RACINE, "la configuration du projet"),
                           (RACINE / "config-a-corriger", "la configuration fautive")):
        soucis = verifier(dossier)
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        print(f"   {titre:<32}{erreurs} erreur(s), "
              f"{len(soucis) - erreurs} avertissement(s)")
    print("\n   Il demande au serveur ses VRAIS noms d'outils, puis les compare")
    print("   aux regles. Claude Code ne fait pas cette comparaison pour les")
    print("   outils MCP ; vous pouvez la faire.")
    print("\n   Lancez-le : uv run python outils/verifier_acces.py config-a-corriger")

    print("\n5. LES QUATRE REGLES QUI TIENNENT\n")
    print("   · Interdire nommement ce qui ECRIT, avant d'autoriser ce qui lit.")
    print("   · Ancrer les globs : « mcp__* » est ignore et n'autorise RIEN.")
    print("   · Ne jamais ecrire un secret dans .mcp.json — il est versionne.")
    print("   · Verifier les noms contre le serveur, puisque personne ne le fait.")


if __name__ == "__main__":
    main()
