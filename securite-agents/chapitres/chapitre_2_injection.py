"""Chapitre 2 — Injection de prompt : delimiter, puis valider la sortie.

    uv run python chapitres/chapitre_2_injection.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.attaques import ATTAQUES                    # noqa: E402
from jobportal.defenses import (AnalyseCv, Agent, Configuration,  # noqa: E402
                                construire_prompt)
from jobportal.modele import TAUX_DE_FUITE                 # noqa: E402


def main() -> None:
    console.utf8()
    attaque = ATTAQUES[0]        # la note forcee

    print("1. LE CV PIEGE — rien d'invisible, juste une phrase de plus\n")
    for ligne in attaque.charge.strip().splitlines():
        print(f"   {ligne}")

    print("\n2. SANS DELIMITEUR : le modele obeit\n")
    resultat = Agent(Configuration.aucune()).analyser_cv(attaque.charge)
    print(f"   obeie  : {resultat.obeie}")
    print(f"   effet  : {resultat.effet}")

    print("\n3. AVEC DELIMITEUR ET REGLE\n")
    prompt, zone = construire_prompt("…le CV…", "Developpeur Java", delimite=True)
    for ligne in prompt.strip().splitlines()[:8]:
        print(f"   {ligne}")
    resultat = Agent(Configuration(delimitation=True)).analyser_cv(attaque.charge)
    print(f"\n   obeie  : {resultat.obeie}")
    if resultat.analyse is None:
        print("   (sans validation de sortie, on ne voit pas le signalement)")

    print("\n4. ET SURTOUT : LE MODELE SIGNALE CE QU'IL A VU\n")
    avec = Configuration(delimitation=True, validation_sortie=True)
    resultat = Agent(avec).analyser_cv(attaque.charge)
    analyse: AnalyseCv | None = resultat.analyse
    if analyse:
        print(f"   score                          {analyse.score}")
        print(f"   instruction_suspecte_detectee  {analyse.instruction_suspecte_detectee}")
        print("\n   Ce booleen vaut plus que le blocage : il donne un SIGNAL.")
        print("   Un CV qui contient des instructions n'est pas un accident —")
        print("   c'est une tentative, et elle merite une alerte (chapitre 6).")

    print(f"\n5. POURQUOI CA NE SUFFIT PAS ({TAUX_DE_FUITE:.0%} de fuite simulee)\n")
    configuration = Configuration(delimitation=True)
    fuites = [a for a in ATTAQUES if Agent(configuration).analyser_cv(a.charge).obeie]
    for a in fuites:
        print(f"   passe encore : {a.nom}")
    print(f"\n   {len(fuites)}/{len(ATTAQUES)} passent MALGRE la consigne.")
    print("\n   Une consigne de prompt demande au modele de se comporter. Elle")
    print("   ne l'y contraint pas — et il suffit d'une fois. C'est la raison")
    print("   d'etre des chapitres 3 a 5 : les couches suivantes ne demandent")
    print("   rien au modele, elles bornent ce qu'il peut PROVOQUER.")

    print("\n6. LA VALIDATION DE SORTIE — un formulaire web, pas un oracle\n")
    for essai in ({"synthese": "ok", "competences": ["Java"], "score": 8},
                  {"synthese": "ok", "competences": ["Java"], "score": 42},
                  {"synthese": "x" * 500, "competences": [], "score": 5}):
        try:
            AnalyseCv(**essai)
            print(f"   accepte  score={essai['score']} synthese={len(essai['synthese'])} signes")
        except Exception as e:
            souci = e.errors()[0]
            print(f"   REFUSE   {souci['loc'][0]} : {souci['msg']}")
    print("\n   La sortie d'un modele vient d'un service qui vient de lire un")
    print("   document hostile. La traiter comme une entree utilisateur n'est")
    print("   pas de la paranoia : c'est la seule lecture exacte.")


if __name__ == "__main__":
    main()
