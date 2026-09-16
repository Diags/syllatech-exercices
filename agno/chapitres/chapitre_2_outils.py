"""Chapitre 2 — Outils et raisonnement : ce que chacun coute.

    uv run python chapitres/chapitre_2_outils.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                             # noqa: E402
from jobportal.agents import conseiller_outille           # noqa: E402
from jobportal.donnees import rechercher_offres           # noqa: E402
from jobportal.modele import ModeleFactice                # noqa: E402


class Compteur(ModeleFactice):
    """Compte les allers-retours, et garde les schemas d'outils recus."""

    def invoke(self, messages=None, tools=None, **kwargs):
        self.tours = getattr(self, "tours", 0) + 1
        self.schemas = tools or getattr(self, "schemas", [])
        self.signes = sum(len(str(m.content or "")) for m in (messages or []))
        return super().invoke(messages=messages, tools=tools, **kwargs)


def main() -> None:
    console.utf8()

    print("1. UN OUTIL EST UNE FONCTION ANNOTEE\n")
    modele = Compteur()
    resultat = conseiller_outille(modele).run("Le marche DevOps ?")
    for schema in modele.schemas:
        f = schema["function"] if isinstance(schema, dict) else {}
        print(f"   {f.get('name')}")
        print(f"     description : {(f.get('description') or '').splitlines()[0][:66]}")
        print(f"     arguments   : {list(f.get('parameters', {}).get('properties', {}))}")

    print("\n   La docstring devient la description, les annotations de type")
    print("   deviennent le schema. Une fonction sans docstring produit un")
    print("   outil que le modele n'appellera jamais a bon escient — et")
    print("   aucune erreur ne vous le signalera.")

    print("\n2. L'AGENT S'EST-IL SERVI DU RETOUR ?\n")
    print(f"   outils appeles : {[t.tool_name for t in (resultat.tools or [])]}")
    print(f"   reponse        : {resultat.content[:86]}")
    offres = json.loads(rechercher_offres("DevOps"))
    citee = any(o.split(" — ")[0] in resultat.content for o in offres)
    print(f"   cite une offre reelle de la base : {'oui' if citee else 'non'}")
    print("\n   C'est LE test qui compte. Un agent qui appelle bien ses outils")
    print("   mais dont la reponse ne depend pas de leur retour passe toute la")
    print("   plomberie et se trompe en production.")

    print("\n3. CE QUE COUTE UN OUTIL\n")
    sans = Compteur()
    conseiller_outille(sans).run("Bonjour")
    print(f"   {'agent + outils, question simple':<40}{sans.tours} tour(s)")
    print(f"   {'agent + outils, question qui declenche':<40}{modele.tours} tour(s)")
    print("\n   Un appel d'outil, c'est un aller-retour de PLUS : le modele")
    print("   demande, on execute, on renvoie, il repond. La latence double,")
    print("   et le contexte du second tour contient la reponse du premier.")

    print("\n4. ReasoningTools N'EST PAS UN MODELE DE RAISONNEMENT\n")
    raisonne = Compteur()
    conseiller_outille(raisonne, avec_raisonnement=True).run("Le marche DevOps ?")
    noms = [(s["function"]["name"] if isinstance(s, dict) else "?")
            for s in raisonne.schemas]
    print(f"   outils exposes : {noms}")
    print("\n   C'est un OUTIL, pas un modele : il donne a l'agent de quoi")
    print("   poser ses etapes avant de repondre. Il fonctionne donc avec")
    print("   n'importe quel modele — et il ajoute des tours, donc des tokens.")
    print("   A reserver aux questions qui se decomposent vraiment ; sur une")
    print("   recherche simple, il coute sans rien apporter.")


if __name__ == "__main__":
    main()
