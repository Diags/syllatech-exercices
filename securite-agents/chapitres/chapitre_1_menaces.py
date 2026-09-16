"""Chapitre 1 — L'anti-patron, execute : ce qu'il concede exactement.

    uv run python chapitres/chapitre_1_menaces.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.attaques import ATTAQUES                    # noqa: E402
from jobportal.defenses import Agent, Configuration        # noqa: E402

OWASP = {
    "LLM01": "Injection de prompt",
    "LLM02": "Divulgation d'informations sensibles",
    "LLM05": "Sortie mal geree en aval",
    "LLM06": "Agence excessive",
    "LLM07": "Fuite du prompt systeme",
    "LLM10": "Consommation illimitee",
}


def main() -> None:
    console.utf8()

    print("1. LE TOP 10, RAMENE A CE QUI NOUS CONCERNE\n")
    for code, nom in OWASP.items():
        print(f"   {code}  {nom}")

    print("\n2. L'ANTI-PATRON DU CHAPITRE — trois lignes, six concessions\n")
    print("     .defaultSystem(\"Tu es l'assistant RH. Rends service au mieux.\")")
    print("     .defaultTools(offres, mail, db)   // TOUS les outils, tout le temps")
    print("     .user(\"Analyse ce CV : \" + texteCv)  // donnee melangee aux consignes")
    print("\n   Ce qu'il concede, mesure par mesure :\n")

    vulnerable = Configuration.aucune()
    for attaque in ATTAQUES:
        resultat = Agent(vulnerable).analyser_cv(attaque.charge)
        marque = "IMPACT" if resultat.impact else ("obeie " if resultat.obeie else "bloque")
        print(f"   {marque}  {attaque.code:<14}{attaque.nom}")

    impacts = sum(1 for a in ATTAQUES
                  if Agent(vulnerable).analyser_cv(a.charge).impact)
    print(f"\n   {impacts}/{len(ATTAQUES)} attaques obtiennent une consequence REELLE :")
    print("   une note faussee, des donnees parties, un fichier lu, une offre")
    print("   supprimee. Aucune n'a demande de competence particuliere — il a")
    print("   suffi d'ecrire une phrase dans un CV.")

    print("\n3. POURQUOI C'EST STRUCTUREL, ET NON UN BUG A CORRIGER\n")
    print("   Un modele de langage ne distingue pas, PAR NATURE, une")
    print("   instruction d'une donnee. Tout arrive dans la meme fenetre,")
    print("   sous la meme forme : du texte. La separation qu'on croit")
    print("   evidente — « ceci est mon prompt, cela est le CV » — n'existe")
    print("   que dans notre tete.")
    print("\n   C'est pourquoi la defense ne peut pas etre « mieux prompter ».")
    print("   Le chapitre 2 commence par la, et montre pourquoi ca ne suffit pas.")


if __name__ == "__main__":
    main()
