"""Chapitre 1 — Découvrir Hermes Agent.

    uv run python chapitres/chapitre_1_decouvrir.py

Hermes est **auto-hébergé et open source**. Ce n'est pas un détail de licence :
c'est ce qui rend ce projet possible. Le paquet est sur PyPI, il s'installe,
et son code s'importe — donc tout ce que les six chapitres affirment se
vérifie en appelant Hermes lui-même, pas une imitation.

C'est la première fois dans ce catalogue qu'un cours porte sur un agent dont
on peut lire et exécuter les gardes, les limites et les analyseurs.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8       # noqa: E402


def main() -> None:
    utf8()

    titre(1, "CE QUI EST REELLEMENT INSTALLE")
    from importlib.metadata import distribution, entry_points

    paquet = distribution("hermes-agent")
    ligne("paquet", f"{paquet.metadata['Name']} {paquet.version}", 22)
    ligne("licence", paquet.metadata.get("License-Expression")
          or paquet.metadata.get("License") or "MIT (annoncee)", 22)
    hauts = sorted({f.parts[0] for f in paquet.files
                    if f.parts and not f.parts[0].endswith(".dist-info")
                    and f.parts[0] != ".."})
    ligne("modules de premier rang", str(len(hauts)), 22)
    print(f"   {'':22} {', '.join(hauts[:11])}…")
    scripts = [(e.name, e.value) for e in
               entry_points().select(group="console_scripts")
               if "herm" in e.name]
    for nom, cible in scripts:
        ligne(f"commande « {nom} »", cible, 22)

    titre(2, "LA TAILLE DE CE QU'ON AUTO-HEBERGE")
    import pkgutil

    for paquet_nom in ("agent", "tools", "gateway", "cron", "plugins"):
        module = __import__(paquet_nom)
        sous = list(pkgutil.iter_modules(module.__path__))
        ligne(paquet_nom, f"{len(sous):>3} modules", 16)
    print()
    print("   Auto-heberger n'est pas gratuit : c'est ce code-la qui tourne")
    print("   sur votre serveur, que vous devez mettre a jour, et dont les")
    print("   failles sont les votres. C'est le prix de l'autre colonne —")
    print("   pas de fournisseur, pas de donnees qui sortent, et un code")
    print("   qu'on peut lire.")

    titre(3, "CE QUE « MODEL-AGNOSTIC » VEUT DIRE, EN FICHIERS")
    import agent
    adaptateurs = sorted(i.name for i in pkgutil.iter_modules(agent.__path__)
                         if i.name.endswith("_adapter"))
    ligne("adaptateurs de modele", str(len(adaptateurs)), 26)
    print(f"   {'':26} {', '.join(a.removesuffix('_adapter') for a in adaptateurs)}")
    print()
    print("   Changer de modele est une ligne de configuration parce que")
    print("   quelqu'un a ecrit un adaptateur par fournisseur. Ce n'est pas")
    print("   magique, c'est du travail deja fait — et c'est exactement ce")
    print("   que le cours « Passerelle IA » resout autrement, avec un proxy.")

    titre(4, "CE QUE LE PROJET VA POUVOIR MESURER")
    debut = time.perf_counter()
    import toolsets
    from tools import approval, skills_guard
    duree = (time.perf_counter() - debut) * 1000

    ligne("ensembles d'outils", f"{len(toolsets.TOOLSETS)}", 30)
    import model_tools
    ligne("outils au total", f"{len(model_tools.get_all_tool_names())}", 30)
    ligne("motifs de commande dangereuse", f"{len(approval.DANGEROUS_PATTERNS)}", 30)
    ligne("motifs « hardline »", f"{len(approval.HARDLINE_PATTERNS)}", 30)
    ligne("motifs de menace (skills)", f"{len(skills_guard.THREAT_PATTERNS)}", 30)
    ligne("caracteres invisibles traques",
          f"{len(skills_guard.INVISIBLE_CHARS)}", 30)
    ligne("import des trois modules", f"{duree:.0f} ms", 30)
    print()
    print("   Tous ces nombres viennent de Hermes. Aucun n'est ecrit dans ce")
    print("   projet : les chapitres les lisent, et les font travailler sur")
    print("   les skills et les commandes du job portal.")

    titre(5, "LA BOUCLE D'AUTO-AMELIORATION, EN UNE PHRASE")
    print("   La plupart des agents recommencent chaque tache de zero.")
    print("   Hermes ecrit une SKILL quand il a resolu quelque chose de")
    print("   difficile, et la rappelle plus tard.")
    print()
    print("   Une skill n'est pas un outil : un outil est une capacite, une")
    print("   skill est une PROCEDURE — l'ordre des etapes, les pieges, ce")
    print("   qu'il ne faut pas faire. C'est ce qui ne se redecouvre pas.")
    print()
    from jobportal.commun import toutes_les_competences
    for nom, texte in toutes_les_competences():
        ligne(f"jobportal/skills/{nom}", f"{len(texte):>4} signes", 34)
    print()
    print("   Le chapitre 3 les fait analyser par le code de Hermes, et le")
    print("   chapitre 6 en fait scanner une qui est piegee.")

    titre(6, "LE PLAN DES SIX CHAPITRES")
    for numero, quoi, mesure in (
            (2, "La memoire persistante",
             "deux limites, un refus qui enseigne, un instantane FIGE"),
            (3, "Skills : l'agent qui s'ameliore",
             "le vrai analyseur de frontmatter, et une skill invisible"),
            (4, "Outils, MCP & backends",
             "57 ensembles, 79 outils, et ce que le catalogue coute"),
            (5, "Multi-plateforme & automatisations",
             "les taches planifiees, et l'injection qu'elles portent"),
            (6, "Auto-hebergement, securite & production",
             "70 gardes de commande, 121 motifs de menace")):
        print(f"   {numero}. {quoi}")
        print(f"      {mesure}")

    print("\n   Au chapitre suivant : ce dont l'agent se souvient, et")
    print("   jusqu'a quand.\n")


if __name__ == "__main__":
    main()
