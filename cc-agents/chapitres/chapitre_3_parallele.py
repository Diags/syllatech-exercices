"""Chapitre 3 — Le fan-out : trois agents en meme temps, et sa limite.

    uv run python chapitres/chapitre_3_parallele.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, travaux                 # noqa: E402
from jobportal.agents import Session, conflit, fan_out  # noqa: E402

MODULES = ("auth", "offres", "candidatures")


def main() -> None:
    console.utf8()
    taches = [("explorateur", f"cartographie le module {m}", travaux.explorer(m))
              for m in MODULES]

    print("1. L'UN APRES L'AUTRE\n")
    session = Session()
    debut = time.perf_counter()
    sequentiels = [session.deleguer(*t) for t in taches]
    duree_sequentielle = time.perf_counter() - debut
    print(f"   {len(MODULES)} explorations : {duree_sequentielle:.2f} s")

    print("\n2. EN MEME TEMPS\n")
    session = Session()
    debut = time.perf_counter()
    rapports = fan_out(session, taches)
    duree_parallele = time.perf_counter() - debut
    print(f"   {len(MODULES)} explorations : {duree_parallele:.2f} s "
          f"→ {duree_sequentielle / duree_parallele:.1f}x")
    print("\n   On n'attend qu'une fois. La latence des modeles se recouvre,")
    print("   c'est tout — et c'est la moitie de l'interet seulement.")

    print("\n3. L'AUTRE MOITIE : L'ISOLATION\n")
    interne = sum(r.tokens_internes for r in rapports)
    print(f"   {'lu par les trois agents':<34}{interne:>7} tokens")
    print(f"   {'recu par l orchestrateur':<34}{session.contexte.taille:>7} tokens")
    print(f"\n   {interne / max(session.contexte.taille, 1):.0f}x moins. Et aucun des trois")
    print("   n'a vu le contexte des deux autres : ils ne peuvent pas se")
    print("   polluer mutuellement, ce qu'une seule session ne garantit jamais.")

    print("\n4. LA SYNTHESE — le role de l'orchestrateur\n")
    for r in rapports:
        lignes = r.texte.splitlines()
        print("   " + lignes[1].split(". ", 1)[1])
        print("     " + lignes[4].strip())

    print("\n5. QUAND LE FAN-OUT EST UNE ERREUR\n")
    cibles = ["offres/api.py", "offres/api.py", "candidatures/depot.py"]
    disputees = conflit(taches, cibles)
    print(f"   Trois agents, ces cibles : {cibles}")
    print(f"   Cible(s) disputee(s) : {disputees}")
    print("\n   Deux agents qui ecrivent le meme fichier, ce n'est pas « un peu")
    print("   plus lent » : c'est le travail du premier ecrase par le second,")
    print("   sans erreur et sans trace. Le fan-out ne vaut que pour des taches")
    print("   VRAIMENT independantes.")
    print("\n   Et une tache qui attend le resultat d'une autre n'est pas un")
    print("   fan-out : c'est un pipeline. C'est le chapitre 5.")


if __name__ == "__main__":
    main()
