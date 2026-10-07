"""Chapitre 4 — Sequentiel ou hierarchique : ce que chacun coute.

    uv run python chapitres/chapitre_4_processus.py
"""
from __future__ import annotations
import sys
from pathlib import Path
from typing import ClassVar
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                    # noqa: E402
from jobportal.equipe import (equipe_hierarchique, equipe_outillee,  # noqa: E402
                              equipe_sequentielle)
from jobportal.modele import ModeleFactice                       # noqa: E402


class Compteur(ModeleFactice):
    """Compte les appels au modele, tous agents confondus.

    `BaseLLM` est un modele Pydantic : un attribut de classe non annote y est
    refuse (« A non-annotated attribute was detected »). D'ou le ClassVar —
    piege classique quand on sous-classe un objet Pydantic sans y penser.
    """

    total: ClassVar[int] = 0

    def call(self, *a, **k):
        Compteur.total += 1
        return super().call(*a, **k)


def mesurer(fabrique, sujet="DevOps"):
    Compteur.total = 0
    m = Compteur()
    resultat = fabrique(m).kickoff(inputs={"sujet": sujet})
    return Compteur.total, m.appels, resultat


def main() -> None:
    console.utf8()

    print("1. LES TROIS FORMES, COTE A COTE\n")
    lignes = []
    for nom, fabrique in (("un agent outille", equipe_outillee),
                          ("sequentiel (2 agents)", equipe_sequentielle),
                          ("hierarchique (3 + manager)", equipe_hierarchique)):
        appels, outils, resultat = mesurer(fabrique)
        lignes.append((nom, appels, outils, resultat))
        print(f"   {nom:<30}{appels:>3} appel(s) au modele   outils={outils}")

    print("\n2. LE MANAGER EST UN AGENT DE PLUS\n")
    seul, sequentiel, hierarchique = (l[1] for l in lignes)
    print(f"   {'un agent':<30}{seul:>3}")
    print(f"   {'deux, en chaine':<30}{sequentiel:>3}")
    print(f"   {'trois, sous un manager':<30}{hierarchique:>3}")
    print("\n   `manager_llm` est OBLIGATOIRE en hierarchique, et c'est")
    print("   logique : le manager decompose, delegue, attend, controle et")
    print("   assemble. Une equipe de trois, ce sont quatre additions.")

    print("\n3. LE CONTEXTE NE CIRCULE PAS TOUT SEUL\n")
    print(f"   {str(lignes[1][3])[:104]}")
    print("\n   La seconde tache recoit la premiere par `context=[veille]`.")
    print("   Sans ce champ, elle repart de rien — et l'on obtient deux")
    print("   rapports independants la ou l'on croyait avoir une chaine.")
    print("   Aucune erreur ne le signale : les deux taches reussissent.")

    print("\n4. QUAND CHAQUE FORME VAUT SON PRIX\n")
    cas = [
        ("sequentiel", "les etapes sont connues d'avance", "veille → redaction"),
        ("hierarchique", "la decomposition demande du jugement", "une mission floue"),
        ("un seul agent", "une seule competence suffit", "chercher dans une base"),
    ]
    for forme, quand, exemple in cas:
        print(f"   {forme:<16}{quand:<40}{exemple}")
    print("\n   Le hierarchique impressionne en demonstration et coute cher en")
    print("   production. On y vient quand l'ordre des etapes DEPEND du sujet,")
    print("   pas parce qu'on a trois agents.")

    print("\n5. allow_delegation, EN SEQUENTIEL\n")
    print("   Agent(..., allow_delegation=True) donne a un agent le droit")
    print("   d'interroger ses collegues sans manager. C'est l'entraide")
    print("   ponctuelle — moins chere qu'un hierarchique, et moins previsible")
    print("   qu'une chaine : chaque delegation est un appel de plus, decide")
    print("   par le modele.")


if __name__ == "__main__":
    main()
