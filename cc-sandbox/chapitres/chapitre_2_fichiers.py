"""Chapitre 2 — Isoler le système de fichiers.

    uv run python chapitres/chapitre_2_fichiers.py

Ce que le chapitre démontre, plutôt que de l'affirmer :

  · les deux défauts ne sont pas symétriques — on lit tout, on écrit peu ;
  · ce n'est ni « deny d'abord » ni « allow d'abord » : la règle la plus
    SPÉCIFIQUE gagne ;
  · donc l'ordre des entrées dans le JSON ne change rien — vérifié sur les
    720 permutations d'un jeu de six règles.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import config, ligne, titre, utf8         # noqa: E402
from outils.resolveur import Config, peut_ecrire, peut_lire  # noqa: E402

TRAVAIL = "/projet"
MAISON = "/home/moi"


def main() -> None:
    utf8()
    depot = config("depot")

    titre(1, "LES DEUX DEFAUTS NE SONT PAS SYMETRIQUES")
    print("   « Default read behavior: read access to the entire computer. »")
    print("   « Default write behavior: the current working directory and its")
    print("     subdirectories, --add-dir, et le dossier temporaire. »\n")
    nu = Config(enabled=True)
    for chemin in ("./src/app.py", "/etc/hosts", "~/.aws/credentials",
                   "~/notes.md", "/usr/bin/curl"):
        lecture = "lit " if peut_lire(nu, chemin).autorise else "REFUS"
        ecriture = "ecrit" if peut_ecrire(nu, chemin).autorise else "REFUS"
        ligne(chemin, f"{lecture}   {ecriture}", 26)
    print()
    print("   Un bac a sable sans reglage lit donc ~/.aws/credentials et")
    print("   ~/.ssh/id_rsa. C'est le comportement documente, et c'est la")
    print("   raison d'etre du bloc « credentials » du chapitre 5 : l'isolation")
    print("   des fichiers protege ce que vous MODIFIEZ, pas ce que vous lisez.")

    titre(2, "CE QUE configs/depot.json CHANGE")
    print('   allowRead ["."]  denyRead ["~/"]  allowWrite ["/tmp/build", …]\n')
    for chemin in ("./src/app.py", "/etc/hosts", "~/notes.md",
                   "~/.aws/credentials", "/tmp/build/sortie.js", "/usr/bin"):
        verdict = peut_lire(depot, chemin)
        ligne(chemin, f"{'lit  ' if verdict.autorise else 'REFUS'}"
                      f"   {verdict.raison}", 22)

    titre(3, "LA REGLE : LA PLUS SPECIFIQUE GAGNE")
    print("   « A denyRead holds inside a wider allowRead, and a narrower")
    print("     allowRead reopens part of a denyRead. »\n")
    imbrique = Config(enabled=True, filesystem={
        "allowRead": [".", "~/projets/notes"],
        "denyRead": ["~/", "~/projets/notes/prive"],
    })
    for chemin in ("~/photos/a.jpg", "~/projets/notes/idees.md",
                   "~/projets/notes/prive/salaires.md"):
        verdict = peut_lire(imbrique, chemin)
        ligne(chemin, f"{'lit  ' if verdict.autorise else 'REFUS'}"
                      f"   {verdict.raison}", 34)
    print()
    print("   Trois verdicts differents pour trois chemins emboites les uns")
    print("   dans les autres. Un moteur « deny d'abord » rendrait REFUS aux")
    print("   trois ; un moteur « allow d'abord » rendrait lit aux trois.")

    titre(4, "DONC L'ORDRE DANS LE JSON NE CHANGE RIEN")
    regles = [("allowRead", "."), ("allowRead", "~/projets/notes"),
              ("allowRead", "~/projets/notes/brouillon"),
              ("denyRead", "~/"), ("denyRead", "~/projets/notes/prive"),
              ("denyRead", "~/projets/notes/brouillon/cles")]
    cibles = ["./a.py", "~/photos/a.jpg", "~/projets/notes/idees.md",
              "~/projets/notes/prive/x.md", "~/projets/notes/brouillon/b.md",
              "~/projets/notes/brouillon/cles/id_rsa"]

    verdicts = set()
    for ordre in itertools.permutations(regles):
        fs: dict[str, list[str]] = {"allowRead": [], "denyRead": []}
        for cle, chemin in ordre:
            fs[cle].append(chemin)
        melange = Config(enabled=True, filesystem=fs)
        verdicts.add(tuple(peut_lire(melange, c).autorise for c in cibles))

    print(f"   {len(list(itertools.permutations(regles)))} ordres possibles "
          f"pour ces six regles.")
    print(f"   Resultats distincts obtenus : {len(verdicts)}\n")
    (unique,) = verdicts
    for chemin, autorise in zip(cibles, unique):
        ligne(chemin, "lit" if autorise else "REFUS", 38)
    print()
    print("   Une seule reponse pour 720 ordres. Ce n'est pas une evidence :")
    print("   un pare-feu iptables, une ACL S3 ou un .gitignore rendraient")
    print("   des resultats DIFFERENTS selon l'ordre. Ici, non — et c'est ce")
    print("   qui permet a plusieurs fichiers de reglages de fusionner leurs")
    print("   listes sans que la fusion decide du resultat.")

    titre(5, "L'ECRITURE SUIT LA MEME REGLE, AVEC UN DEFAUT INVERSE")
    for chemin in ("./build/app.js", "/tmp/build/app.js", "/tmp/autre/x",
                   "~/.cache/npm/paquet.tgz", "~/Documents/rapport.md"):
        verdict = peut_ecrire(depot, chemin)
        ligne(chemin, f"{'ecrit' if verdict.autorise else 'REFUS'}"
                      f"   {verdict.raison}", 26)
    print()
    print("   « /tmp/autre » est refuse alors que « /tmp/build » est autorise :")
    print("   ouvrir un dossier n'ouvre pas son parent. C'est l'erreur qu'on")
    print("   fait en ecrivant « /tmp » et en croyant avoir ete precis.")

    print("\n   Au chapitre suivant : les chemins que ces regles ne peuvent")
    print("   PAS rouvrir, quoi qu'on y ecrive.\n")


if __name__ == "__main__":
    main()
