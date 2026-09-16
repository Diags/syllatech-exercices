"""Chapitre 3 — Les chemins protégés.

    uv run python chapitres/chapitre_3_proteges.py

Le chapitre le plus court à énoncer et le plus facile à ne pas croire :
**un `allowWrite` sur un chemin protégé ne le rouvre pas.** Il n'échoue pas
non plus. Il ne fait rien.

    « There is no way to exempt one of these paths: an allowWrite entry or an
      Edit allow rule that covers the path doesn't lift the protection. »
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import ligne, titre, utf8                       # noqa: E402
from outils.resolveur import (PROTEGES_A_LA_RACINE,                # noqa: E402
                              PROTEGES_DEPOT_NU,
                              PROTEGES_DEPOT_NU_SI_EXISTANTS,
                              PROTEGES_MAISON, PROTEGES_REMONTEE,
                              Config, peut_ecrire, protege)


def main() -> None:
    utf8()

    titre(1, "LES QUATRE GROUPES")
    groupes = [
        ("le dossier de travail ET SES PARENTS", PROTEGES_REMONTEE),
        ("le dossier de travail seulement", PROTEGES_A_LA_RACINE),
        ("ce qui ferait un depot git nu", PROTEGES_DEPOT_NU),
        ("~/.claude (ou CLAUDE_CONFIG_DIR)", PROTEGES_MAISON),
    ]
    for ou, motifs in groupes:
        print(f"   {ou}")
        print(f"      {', '.join(motifs)}")
    print(f"\n   Et, dans le troisieme groupe, seulement SI ILS EXISTENT DEJA :")
    print(f"      {', '.join(PROTEGES_DEPOT_NU_SI_EXISTANTS)}")

    titre(2, "UNE CONFIGURATION QUI TENTE DE TOUT ROUVRIR")
    cibles = [".claude/settings.json", ".claude/hooks/pre.sh", ".mcp.json",
              ".claude/skills/deploy/SKILL.md", ".bashrc", ".git/config",
              "~/.claude/settings.json", "~/.claude.json",
              "HEAD", "refs/heads/main"]
    ouverte = Config(enabled=True, filesystem={"allowWrite": cibles + ["."]})

    print("   allowWrite liste EXPLICITEMENT chacun de ces chemins.\n")
    for chemin in cibles:
        verdict = peut_ecrire(ouverte, chemin)
        ligne(chemin, "ecrit" if verdict.autorise else "REFUS", 32)
    refuses = sum(1 for c in cibles if not peut_ecrire(ouverte, c).autorise)
    print(f"\n   {refuses}/{len(cibles)} refuses, malgre un allowWrite nomme")
    print("   pour chacun. Aucune erreur au demarrage, aucune ligne de")
    print("   journal : la regle est acceptee et sans effet.")

    titre(3, "LA REMONTEE — CE QUI SURPREND LE PLUS")
    print("   Le premier groupe protege aussi les dossiers AU-DESSUS du")
    print("   dossier de travail. Un .claude/ pose deux niveaux plus haut est")
    print("   protege comme le votre.\n")
    profond = Config(enabled=True)
    for chemin in ("/travail/client/appli/.claude/settings.json",
                   "/travail/client/.claude/settings.json",
                   "/travail/.mcp.json",
                   "/travail/client/appli/src/main.py"):
        verdict = peut_ecrire(profond, chemin, travail="/travail/client/appli")
        ligne(chemin, "ecrit" if verdict.autorise else "REFUS", 44)

    titre(4, "LE PIEGE QUI N'A RIEN A VOIR AVEC CLAUDE")
    print("   « config » et « hooks » a la racine du dossier de travail sont")
    print("   proteges s'ils existent — « even when the config directory")
    print("   belongs to your project rather than to git ». Un projet Rails,")
    print("   Symfony ou Spring a un dossier config/ a sa racine.\n")
    for existants, etiquette in ((set(), "sans dossier config/ a la racine"),
                                 ({"config"}, "AVEC un dossier config/")):
        verdict = peut_ecrire(Config(enabled=True), "config/base.yml",
                              existants=existants)
        ligne(etiquette, "ecrit" if verdict.autorise else "REFUS", 34)
    print()
    print("   Le meme chemin, la meme configuration, deux verdicts — selon")
    print("   qu'un dossier existe ou non. C'est la regle « depot git nu » :")
    print("   une commande qui creerait HEAD, objects, refs, config et hooks")
    print("   a la racine transformerait le dossier de travail en depot nu.")

    titre(5, "LA SEULE CLE QUI LEVE CES PROTECTIONS")
    print("   « The only way to turn the protection off is filesystem.disabled,")
    print("     which turns off filesystem isolation for every path. »\n")
    coupee = Config(enabled=True, filesystem={"disabled": True},
                    portee="utilisateur")
    for chemin in (".claude/settings.json", "~/.claude.json", "~/.bashrc"):
        verdict = peut_ecrire(coupee, chemin)
        ligne(chemin, "ecrit" if verdict.autorise else "REFUS", 32)
    print()
    print("   Elle ne fait pas d'exception : elle enleve la couche. Et elle")
    print("   n'est elle-meme honoree que depuis les reglages utilisateur,")
    print("   geres ou --settings — un depot ne peut pas se desandboxer.")
    dans_le_depot = Config(enabled=True, filesystem={"disabled": True},
                           portee="projet")
    verdict = peut_ecrire(dans_le_depot, ".claude/settings.json")
    ligne("la meme, en portee projet", "ecrit" if verdict.autorise else "REFUS",
          32)

    titre(6, "POURQUOI CETTE LISTE-LA")
    print("   Ce ne sont pas « des fichiers sensibles » : ce sont les fichiers")
    print("   que CLAUDE CODE LUI-MEME relit. Un hook, une skill, un serveur")
    print("   MCP, un settings.json sont executes ou obeis HORS du bac a")
    print("   sable. Une commande sandboxee qui pourrait les ecrire")
    print("   s'accorderait des permissions au tour suivant.")
    print()
    print("   Le bac a sable se refermerait lui-meme. D'ou l'absence")
    print("   d'exception : une exception serait exactement le trou.")

    print("\n   Au chapitre suivant : la meme question pour le reseau.\n")


if __name__ == "__main__":
    main()
