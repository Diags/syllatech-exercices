"""Chapitre 1 — Ce que Claude Code lit avant votre premier mot.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.verifier_config import verifier          # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def utf8() -> None:
    for flux in (sys.stdout, sys.stderr):
        try:
            flux.reconfigure(encoding="utf-8", errors="replace")
        except Exception:      # noqa: BLE001
            pass


def main() -> None:
    utf8()

    print("1. L'ARBORESCENCE D'UN PROJET EQUIPE\n")
    for chemin in sorted(RACINE.rglob(".claude/**/*")):
        if chemin.is_file() and ".venv" not in str(chemin) \
                and "config-pourrie" not in str(chemin):
            print(f"   {chemin.relative_to(RACINE).as_posix()}")
    for nom in ("CLAUDE.md", ".mcp.json"):
        if (RACINE / nom).exists():
            print(f"   {nom}")

    print("\n2. CE QUI EST LU AU LANCEMENT, ET QUAND\n")
    quand = [
        ("CLAUDE.md", "a CHAQUE session, en entier"),
        (".claude/settings.json", "au lancement : permissions et hooks"),
        (".mcp.json", "au lancement : les serveurs se connectent"),
        (".claude/agents/*.md", "leur description seulement, en permanence"),
        (".claude/skills/*/SKILL.md", "nom + description ; le corps au declenchement"),
    ]
    for quoi, moment in quand:
        print(f"   {quoi:<28}{moment}")
    print("\n   La colonne de droite decide de ce qui compte. Un CLAUDE.md de")
    print("   200 lignes est paye a chaque session ; la description d'une")
    print("   skill, aussi. Le corps d'une skill, non.")

    print("\n3. CE QUE CA PESE, ICI\n")
    total = 0
    for nom in ("CLAUDE.md", ".claude/settings.json", ".mcp.json"):
        chemin = RACINE / nom
        if chemin.exists():
            signes = len(chemin.read_text(encoding="utf-8"))
            total += signes
            print(f"   {nom:<28}{signes:>6} signes")
    print(f"   {'':<28}{'':->6}")
    print(f"   {'a chaque session':<28}{total:>6} signes (~{total // 4} tokens)")

    print("\n4. LA VERIFICATION QUI N'EXISTE PAS\n")
    print("   /hooks         liste les hooks")
    print("   /doctor        relit les skills")
    print("   claude mcp list teste les serveurs")
    print("\n   Chacun verifie SA piece. Personne ne verifie la coherence")
    print("   ENTRE les pieces — et c'est la que se trouve le pourrissement")
    print("   reel d'un .claude/ apres six mois.")
    propre = verifier(RACINE)
    pourrie = verifier(RACINE / "config-pourrie")
    print(f"\n   cette configuration       {len(propre)} souci(s)")
    print(f"   config-pourrie/           {len(pourrie)} souci(s)")
    print("\n   uv run python outils/verifier_config.py config-pourrie")


if __name__ == "__main__":
    main()
