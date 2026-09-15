"""Chapitre 3 — MCP : la regle qui ne protege rien.

    uv run python chapitres/chapitre_3_mcp.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chapitres.chapitre_1_demarrer import utf8       # noqa: E402
from outils.verifier_config import verifier_mcp      # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    utf8()
    config = json.loads((RACINE / ".mcp.json").read_text(encoding="utf-8"))
    reglages = json.loads((RACINE / ".claude" / "settings.json")
                          .read_text(encoding="utf-8"))

    print("1. LE .mcp.json DE CE PROJET\n")
    for nom, serveur in config["mcpServers"].items():
        cible = serveur.get("url") or " ".join(
            [serveur.get("command", "")] + serveur.get("args", []))
        print(f"   {nom:<10}{serveur.get('type', '?'):<8}{cible[:64]}")

    print("\n2. TROIS PORTEES, ET UNE SEULE EST PARTAGEE\n")
    for portee, fichier, partage in (
            ("local (defaut)", "~/.claude.json, sous le projet", "non"),
            ("project", ".mcp.json a la racine", "OUI"),
            ("user", "~/.claude.json, au niveau superieur", "non")):
        print(f"   {portee:<16}{fichier:<36}{partage}")
    print("\n   « --scope project » ecrit dans .mcp.json, qui est versionne.")
    print("   C'est ce qu'on veut pour l'outillage d'equipe — et c'est")
    print("   exactement pourquoi un secret ne doit jamais y figurer.")

    print("\n3. LA VERSION EPINGLEE\n")
    args = config["mcpServers"]["db"]["args"]
    print(f"   {args}")
    print("\n   « @1.4.2 » et non « @latest » : la description d'un outil MCP")
    print("   est du texte que le modele lit. Une montee de version silencieuse")
    print("   peut donc changer ce que votre agent croit devoir faire — sans")
    print("   commit, sans revue, sans trace.")

    print("\n4. LA VARIABLE PLUTOT QUE LE SECRET\n")
    print(f"   {args[-1]}")
    print("\n   ${VAR:-defaut} : le projet demarre sans configuration")
    print("   prealable, et celui qui veut pointer ailleurs pose la variable.")
    print("   Un ${VAR} sans defaut et non defini reste LITTERAL dans la")
    print("   commande — le serveur repond une erreur qui ne parle pas de ca.")

    print("\n5. LA REGLE QUI NE PROTEGE RIEN\n")
    permissions = reglages["permissions"]
    print(f"   allow : {permissions['allow']}")
    print(f"   deny  : {permissions['deny']}\n")
    casse = {"permissions": {"deny": ["mcp__analytics__export"]}}
    for souci in verifier_mcp(RACINE, casse):
        print(f"   {souci.gravite.upper()} : {souci.message[:84]}")
    print("\n   Une regle qui nomme un serveur absent du .mcp.json ne")
    print("   correspond a rien. Elle est acceptee, elle a l'air de proteger,")
    print("   et elle ne protege rien. Meme chose pour une faute de frappe")
    print("   dans le nom d'un outil : les noms MCP contiennent « _ », et le")
    print("   controle de faute de frappe de Claude Code les exempte.")

    print("\n6. L'ORDRE D'EVALUATION\n")
    print("   deny, puis ask, puis allow — la premiere qui correspond decide.")
    print("   La specificite ne change rien : un deny large l'emporte sur un")
    print("   allow precis. Une regle deny ne peut donc pas porter")
    print("   d'exception ; il faut la restreindre, pas l'annoter.")


if __name__ == "__main__":
    main()
