"""Chapitre 4 — Sous-agents et skills : deux choses qu'on confond.

    uv run python chapitres/chapitre_4_agents_skills.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from chapitres.chapitre_1_demarrer import utf8              # noqa: E402
from outils.verifier_config import (_frontmatter, verifier_agents,  # noqa: E402
                                    verifier_skills)

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    utf8()

    print("1. UN SOUS-AGENT ET UNE SKILL NE FONT PAS LA MEME CHOSE\n")
    for quoi, ou, quand in (
            ("sous-agent", ".claude/agents/nom.md",
             "isoler un CONTEXTE : il lit 50 fichiers, rend 10 lignes"),
            ("skill", ".claude/skills/nom/SKILL.md",
             "figer une PROCEDURE : les memes etapes, a chaque fois")):
        print(f"   {quoi:<12}{ou:<30}{quand}")
    print("\n   On prend un sous-agent quand la tache est volumineuse en")
    print("   LECTURE. On prend une skill quand elle est repetitive et que")
    print("   l'ordre des etapes compte. Une skill qui explore 50 fichiers")
    print("   remplit votre contexte ; un sous-agent qui suit une procedure")
    print("   la reinvente a chaque fois.")

    print("\n2. LE SOUS-AGENT DE CE PROJET\n")
    fichier = RACINE / ".claude" / "agents" / "reviseur.md"
    champs, corps = _frontmatter(fichier.read_text(encoding="utf-8"))
    for cle in ("name", "description", "tools", "model"):
        print(f"   {cle:<14}{champs.get(cle, '—')[:70]}")
    print(f"\n   prompt systeme : {len(corps.strip())} signes")
    print("\n   « tools: Read, Grep, Glob » n'est pas une optimisation : un")
    print("   outil absent de la liste est REFUSE. C'est ce qui garantit")
    print("   qu'un reviseur ne reecrira pas le code qu'il juge.")
    print("\n   Sans champ « tools », un sous-agent HERITE de tout — Write et")
    print("   Edit compris. La difference tient en une ligne, et elle ne")
    print("   produit aucune erreur tant que l'agent n'essaie pas.")

    print("\n3. LA SKILL DE CE PROJET\n")
    fichier = RACINE / ".claude" / "skills" / "changelog" / "SKILL.md"
    champs, corps = _frontmatter(fichier.read_text(encoding="utf-8"))
    print(f"   name          {champs.get('name')}")
    print(f"   description   {champs.get('description', '')[:66]}…")
    print(f"   corps         {len(corps.strip())} signes")
    print("\n   Seuls le nom et la description sont charges EN PERMANENCE. Le")
    print("   corps n'entre dans le contexte qu'au declenchement — c'est tout")
    print("   le sens de « chargement a la demande ».")
    print("\n   Consequence directe : la description est le SEUL texte dont")
    print("   le modele dispose pour choisir. Une description qui dit ce que")
    print("   fait la skill sans dire QUAND l'employer ne se declenche jamais.")

    print("\n4. LE DEFAUT QUI NE SE VOIT QU'A L'USAGE\n")
    for souci in verifier_skills(RACINE / "config-pourrie"):
        print(f"   {souci.gravite.upper():<10}{souci.message[:78]}")
    print("\n   Un chemin relatif est resolu depuis le dossier de TRAVAIL, pas")
    print("   depuis la skill. Le script est introuvable, et on ne l'apprend")
    print("   qu'a l'instant ou la skill s'execute, en pleine tache.")

    print("\n5. ET POUR LES SOUS-AGENTS\n")
    for souci in verifier_agents(RACINE / "config-pourrie"):
        print(f"   {souci.gravite.upper():<10}{souci.message[:78]}")
    print("\n   Un outil dont le nom a change reste dans le « tools: ». Il est")
    print("   simplement ignore : l'agent n'a pas cet outil, et rien ne le dit.")

    print("\n6. LES DEUX SE VERSIONNENT\n")
    print("   .claude/ vit dans git, avec le code qu'il sert. Un nouvel")
    print("   arrivant clone et herite de tout l'outillage — a condition que")
    print("   l'outillage soit encore coherent avec le code. C'est ce que")
    print("   verifie outils/verifier_config.py, et ce qu'aucune commande")
    print("   integree ne fait.")


if __name__ == "__main__":
    main()
