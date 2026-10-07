"""Chapitre 5 — CLAUDE.md : le fichier qu'on paie a chaque session.

    uv run python chapitres/chapitre_5_memoire.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chapitres.chapitre_1_demarrer import utf8         # noqa: E402
from outils.verifier_config import verifier_claude_md  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    utf8()
    texte = (RACINE / "CLAUDE.md").read_text(encoding="utf-8")

    print("1. CE QU'IL COUTE\n")
    print(f"   {len(texte)} signes, soit ~{len(texte) // 4} tokens")
    print("   x 40 sessions par mois = ~%d tokens, payes pour le meme texte."
          % (len(texte) // 4 * 40))
    print("\n   C'est peu ici. Ce ne l'est plus a 300 lignes — et c'est la")
    print("   raison pour laquelle un CLAUDE.md doit rester court et")
    print("   actionnable, pas parce que « c'est plus propre ».")

    print("\n2. CE QU'IL DOIT CONTENIR\n")
    for quoi, pourquoi in (
            ("les commandes", "l'agent ne les devine pas, il les invente"),
            ("les conventions non evidentes", "celles qu'un nouvel arrivant rate"),
            ("les interdits", "« jamais de any », « ne pas toucher aux migrations »"),
            ("l'outillage disponible", "sinon l'agent refait ce qui existe")):
        print(f"   {quoi:<32}{pourquoi}")
    print("\n   Ce qu'il ne doit PAS contenir : ce que le code dit deja. Une")
    print("   description de l'architecture se perime ; le code, non.")

    print("\n3. LE CONTROLE QUE PERSONNE NE FAIT\n")
    scripts = json.loads((RACINE / "package.json").read_text(encoding="utf-8"))["scripts"]
    print(f"   scripts reels : {', '.join(sorted(scripts))}")
    soucis = verifier_claude_md(RACINE)
    print(f"   CLAUDE.md de ce projet : {len(soucis)} souci(s)")

    print("\n   Et sur une configuration qui a vecu six mois :\n")
    for souci in verifier_claude_md(RACINE / "config-pourrie"):
        print(f"   {souci.gravite.upper():<10}{souci.message[:76]}")

    print("\n   Chacun de ces defauts est REPETE A L'AGENT A CHAQUE SESSION.")
    print("   Une commande fausse dans CLAUDE.md, c'est une commande fausse")
    print("   lancee des centaines de fois — et a chaque fois, l'agent")
    print("   « decouvre » qu'elle echoue et improvise autre chose.")

    print("\n4. LES TROIS NIVEAUX DE MEMOIRE\n")
    for ou, portee in (
            ("./CLAUDE.md", "le projet, partage par l'equipe (versionne)"),
            ("./CLAUDE.local.md", "vos notes sur ce projet (ignore par git)"),
            ("~/.claude/CLAUDE.md", "vous, sur tous vos projets")):
        print(f"   {ou:<24}{portee}")
    print("\n   Les trois se cumulent. Une preference personnelle dans le")
    print("   fichier partage impose votre facon de faire a toute l'equipe —")
    print("   et personne ne s'en apercoit, puisque ca marche.")

    print("\n5. LE CONTEXTE, ET LES DEUX COMMANDES QUI COMPTENT\n")
    print("   /compact   resume la conversation, garde le fil")
    print("   /clear     repart de zero, garde CLAUDE.md")
    print("\n   /clear entre deux taches SANS RAPPORT est le geste le plus")
    print("   rentable de Claude Code : le contexte d'une tache precedente ne")
    print("   sert pas a la suivante, il la parasite et il se paie.")


if __name__ == "__main__":
    main()
