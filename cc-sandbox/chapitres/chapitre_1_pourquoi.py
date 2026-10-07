"""Chapitre 1 — Pourquoi un bac à sable, et ce qu'il n'est pas.

    uv run python chapitres/chapitre_1_pourquoi.py
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import RACINE, config, titre, utf8   # noqa: E402
from outils.resolveur import LIMITES, appliquee         # noqa: E402
from outils.verifier import verifier                    # noqa: E402


def main() -> None:
    utf8()

    titre(1, "LE PROBLEME QU'IL RESOUT")
    print("   Sans bac a sable, chaque commande Bash demande une approbation.")
    print("   On finit par tout approuver — ou par passer en mode permissif,")
    print("   ce qui revient au meme sans le dire.")
    print()
    print("   Avec : on declare une fois ce que les commandes peuvent toucher,")
    print("   et le SYSTEME D'EXPLOITATION fait respecter la frontiere, pour")
    print("   la commande et pour tous ses processus fils. Plus de question")
    print("   par commande.")

    titre(2, "CE QU'IL N'EST PAS")
    for quoi, verdict in (
            ("un conteneur", "non : Seatbelt (macOS), seccomp (Linux)"),
            ("une machine virtuelle", "non : meme noyau, meme machine"),
            ("une protection contre l'agent", "non : contre ce qu'il EXECUTE"),
            ("un remplacement des permissions", "non : les deux se cumulent")):
        print(f"   {quoi:<33} {verdict}")

    titre(3, f"SUR CETTE MACHINE : {platform.system()}")
    if platform.system() == "Windows":
        print("   Le bac a sable ne tourne PAS sur Windows natif. La")
        print("   documentation demande WSL2, et Claude Code s'y execute alors")
        print("   comme sous Linux.")
        print()
        print("   Ce projet ne simule donc pas le bac a sable : il modelise ses")
        print("   REGLES, et permet de les interroger. C'est ce qu'on peut")
        print("   verifier honnetement ici — et c'est justement ce qui manque")
        print("   le plus quand on ecrit une configuration.")
    else:
        print("   Le bac a sable peut tourner ici. Ce projet reste un modele")
        print("   de ses regles : lancez « /sandbox » dans Claude Code pour")
        print("   voir la configuration reellement resolue sur cette machine.")

    titre(4, "LA CONFIGURATION MINIMALE")
    for ligne in ('{', '  "sandbox": {', '    "enabled": true,',
                  '    "failIfUnavailable": true', '  }', '}'):
        print(f"   {ligne}")
    print()
    print("   « failIfUnavailable » est la ligne qu'on oublie. A false — le")
    print("   defaut — Claude Code avertit et CONTINUE quand le bac a sable")
    print("   n'est pas disponible. On croit etre protege, on ne l'est pas, et")
    print("   la seule difference visible est un message au demarrage.")

    titre(5, "LE MEME FICHIER, DEUX ENDROITS, DEUX RESULTATS")
    print("   configs/a-corriger.json contient six defauts. Aucun n'est une")
    print("   faute de syntaxe. Et la liste change selon l'endroit ou on pose")
    print("   le fichier :\n")
    print(f"   {'portee':<16}{'erreurs':>9}{'avertissements':>16}   cles ignorees")
    for portee in ("projet", "utilisateur"):
        rotten = config("a-corriger", portee)
        soucis = verifier(rotten)
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        _, ignorees = appliquee(rotten)
        print(f"   {portee:<16}{erreurs:>9}{len(soucis) - erreurs:>16}"
              f"   {len(ignorees)}")
    print()
    print("   Cinq cles ne sont honorees que depuis les reglages utilisateur,")
    print("   geres, ou « --settings ». Dans le .claude/settings.json d'un")
    print("   depot — un fichier qu'un « git pull » peut changer — elles sont")
    print("   ignorees. Pas refusees : IGNOREES. La relecture ne montre rien.")

    titre(6, "LES DEUX CONFIGURATIONS SAINES")
    for nom, portee, quoi in (
            ("depot", "projet", "ce qui a sa place dans le depot"),
            ("utilisateur", "utilisateur", "ce qui doit rester chez vous")):
        soucis = verifier(config(nom, portee))
        erreurs = sum(1 for s in soucis if s.gravite == "erreur")
        print(f"   configs/{nom + '.json':<20} portee {portee:<12}"
              f" {erreurs} erreur, {len(soucis) - erreurs} avertissement")
        print(f"   {'':<20}          {quoi}")

    titre(7, "CE QUE CE PROJET NE FAIT PAS")
    for ligne in LIMITES.strip().splitlines():
        print(f"   {ligne}")

    print(f"\n   Les six chapitres sont dans {RACINE.name}/chapitres/.\n")


if __name__ == "__main__":
    main()
