#!/usr/bin/env python3
"""La matrice : corpus × niveaux d'execution, et corpus × gardes.

    uv run python outils/mesurer.py
    uv run python outils/mesurer.py --gardes

C'est l'outil qui produit les deux tableaux des chapitres 3 et 4. Il est
separe pour qu'on puisse ajouter une soumission ou un niveau et relancer la
mesure sans lire un chapitre.

POURQUOI « EnLocal » N'EST PAS TESTE SUR LA FAMILLE « ressource »

Une boucle infinie dans un exec() local bloque le processus qui mesure. Il
n'y a pas de delai possible : c'est precisement ce que le niveau local ne
sait pas faire, et le tableau l'ecrit au lieu de le contourner.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import utf8                             # noqa: E402
from jobportal.evaluateur import Evaluateur                   # noqa: E402
from jobportal.executeurs import NIVEAUX, Bride, EnLocal      # noqa: E402
from jobportal.gardes import GARDES                           # noqa: E402
from jobportal.soumissions import CORPUS, Soumission          # noqa: E402

NON_TESTABLE = "(bloquerait)"


def etat(soumission: Soumission, niveau, execution) -> str:
    if soumission.hostile:
        if soumission.a_reussi(execution.sortie):
            return "REUSSIE"
        return "interrompue" if execution.interrompu else "arretee"
    return "exercice ok" if execution.reussie else "exercice ko"


def matrice_execution() -> list[tuple[Soumission, dict[str, str]]]:
    lignes = []
    for soumission in CORPUS:
        par_niveau: dict[str, str] = {}
        for niveau in NIVEAUX:
            if isinstance(niveau, EnLocal) and soumission.famille == "ressource":
                par_niveau[niveau.nom] = NON_TESTABLE
                continue
            execution = niveau.executer(soumission.code)
            par_niveau[niveau.nom] = etat(soumission, niveau, execution)
        lignes.append((soumission, par_niveau))
    return lignes


def matrice_gardes() -> list[tuple[Soumission, dict[str, tuple[int, int]]]]:
    """Pour chaque garde : (score rendu, signes hostiles atteignant le modele).

    La seconde valeur est la seule qui ne depende d'aucun modele — c'est
    celle qu'il faut lire.
    """
    lignes = []
    for soumission in CORPUS:
        if soumission.famille == "ressource":
            continue
        par_garde: dict[str, tuple[int, int]] = {}
        for garde in GARDES:
            evaluation = Evaluateur(executeur=Bride(), garde=garde).evaluer(
                soumission)
            par_garde[garde.nom] = (evaluation.verdict.score,
                                    evaluation.signes_hostiles_au_modele)
        lignes.append((soumission, par_garde))
    return lignes


def _afficher_execution() -> None:
    lignes = matrice_execution()
    entete = "".join(f"{n.nom:<16}" for n in NIVEAUX)
    print(f"\n  {'soumission':<28}{'famille':<12}{entete}")
    for soumission, par_niveau in lignes:
        colonnes = "".join(f"{par_niveau[n.nom]:<16}" for n in NIVEAUX)
        print(f"  {soumission.nom:<28}{soumission.famille:<12}{colonnes}")

    print()
    for niveau in NIVEAUX:
        hostiles = [s for s, p in lignes if s.hostile
                    and p[niveau.nom] != NON_TESTABLE]
        arretees = [s for s, p in lignes if s.hostile
                    and p[niveau.nom] not in ("REUSSIE", NON_TESTABLE)]
        print(f"  {niveau.nom:<16}{len(arretees)}/{len(hostiles)} attaques "
              f"arretees")
    print()


def _afficher_gardes() -> None:
    lignes = matrice_gardes()
    entete = "".join(f"{g.nom:<20}" for g in GARDES)
    print(f"\n  {'soumission':<28}{'famille':<12}{entete}")
    for soumission, par_garde in lignes:
        colonnes = "".join(
            f"{score:>3} / {signes:>4} sg     " for score, signes in
            (par_garde[g.nom] for g in GARDES))
        print(f"  {soumission.nom:<28}{soumission.famille:<12}{colonnes}")
    print()
    for garde in GARDES:
        total = sum(par_garde[garde.nom][1] for _, par_garde in lignes)
        print(f"  {garde.nom:<16}{total:>5} signes hostiles atteignent le "
              f"modele, au total")
    print()


def main() -> int:
    utf8()
    if "--gardes" in sys.argv:
        _afficher_gardes()
    else:
        _afficher_execution()
    return 0


if __name__ == "__main__":
    sys.exit(main())
