"""Chapitre 4 — Sandbox applicatif : pourquoi Python ne peut pas, pourquoi Wasm peut.

    uv run python chapitres/chapitre_4_wasm.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.evasions import EVASIONS                        # noqa: E402
from jobportal.niveaux import BUILTINS_AUTORISES, restreint    # noqa: E402


def main() -> None:
    console.utf8()
    remontee = next(e for e in EVASIONS if "__subclasses__" in e.nom)

    print("1. LA LISTE BLANCHE QU'ON ECRIT SPONTANEMENT\n")
    print(f"   {len(BUILTINS_AUTORISES)} builtins autorises, « open » et")
    print("   « __import__ » retires. Elle a l'air prudente — c'est le piege.")

    print("\n2. ELLE TIENT... CONTRE LES DEUX PREMIERES LIGNES\n")
    for e in EVASIONS[:2]:
        r = restreint(e.code)
        print(f"   {'ECHAPPE' if r.echappe else 'bloque ':<9}{e.nom:<42}{r.motif}")

    print("\n3. ET ELLE TOMBE EN SIX LIGNES\n")
    for ligne in remontee.code.splitlines():
        print(f"     {ligne}")
    r = restreint(remontee.code)
    print(f"\n   resultat : {'ECHAPPE — ' + r.sortie if r.echappe else 'bloque'}")
    print("\n   L'arbre des classes est accessible depuis N'IMPORTE QUEL objet.")
    print("   Un tuple vide suffit. De la, on atteint l'importateur, donc os,")
    print("   donc tout. Retirer des builtins n'y change rien — et cette")
    print("   technique est publiee depuis vingt ans.")

    print("\n4. CE N'EST PAS UN BUG DE PYTHON\n")
    print("   Python est CONCU pour l'introspection : c'est ce qui rend les")
    print("   ORM, les serialiseurs et les frameworks de test possibles. La")
    print("   meme propriete rend l'isolation en-langage impossible. On ne")
    print("   peut pas garder l'une sans l'autre.")
    print("\n   Le module « rexec » de la bibliotheque standard a ete RETIRE")
    print("   pour cette raison. Refaire ce que le langage a abandonne en")
    print("   2003 n'est pas un projet.")

    print("\n5. CE QUE WEBASSEMBLY FAIT DIFFEREMMENT\n")
    print("     config.consume_fuel = True     # un compteur d'instructions")
    print("     store.set_fuel(10_000_000)     # un budget DUR")
    print("     instance = Instance(store, module, [])   # [] = zero capacite")
    print("\n   La difference tient dans ce « [] » : un module Wasm ne peut")
    print("   appeler QUE les fonctions qu'on lui fournit. Aucun fichier,")
    print("   aucune socket, aucun appel systeme — non pas retires, mais")
    print("   JAMAIS PRESENTS. Il n'y a pas d'arbre de classes a remonter,")
    print("   parce qu'il n'y a rien au bout.")
    print("\n   Le « fuel » fait le reste : une boucle infinie s'arrete au")
    print("   budget, sans horloge ni signal.")
    print("\n   Prix a payer : votre code doit compiler vers Wasm. Python ne")
    print("   s'y prete qu'au travers d'un interprete embarque, qui pese et")
    print("   ralentit. C'est pourquoi le chapitre 5 revient aux conteneurs")
    print("   pour executer du Python — et Wasm reste imbattable pour des")
    print("   extensions ecrites en Rust ou en Go.")


if __name__ == "__main__":
    main()
