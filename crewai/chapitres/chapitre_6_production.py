"""Chapitre 6 — Production : memoire, couts, observabilite.

    uv run python chapitres/chapitre_6_production.py
"""
from __future__ import annotations
import sys
import tomllib
from pathlib import Path
from typing import ClassVar
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                     # noqa: E402
from jobportal.equipe import (chercheur, equipe_hierarchique,      # noqa: E402
                              equipe_outillee, redacteur)
from jobportal.modele import ModeleFactice                        # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


class Compteur(ModeleFactice):
    total: ClassVar[int] = 0
    signes: ClassVar[int] = 0

    def call(self, messages, *a, **k):
        Compteur.total += 1
        texte = messages if isinstance(messages, str) else "\n".join(
            str(m.get("content", "")) for m in messages)
        Compteur.signes += len(texte)
        return super().call(messages, *a, **k)


def main() -> None:
    console.utf8()

    print("1. CE QUE COUTE UN EQUIPAGE, MESURE\n")
    for nom, fabrique in (("un agent outille", equipe_outillee),
                          ("hierarchique", equipe_hierarchique)):
        Compteur.total = Compteur.signes = 0
        resultat = fabrique(Compteur()).kickoff(inputs={"sujet": "DevOps"})
        print(f"   {nom:<22}{Compteur.total:>3} appel(s)"
              f"{Compteur.signes:>9} signes envoyes")
    print("\n   `resultat.token_usage` donne les tokens du run cote CrewAI.")
    print("   Avec un modele factice il vaut zero — c'est normal, rien n'a ete")
    print("   facture. Avec un vrai modele, c'est LA mesure a agreger par")
    print("   requete utilisateur, pas par appel.")

    print("\n2. LE BON MODELE PAR AGENT\n")
    print("   chercheur  llm='claude-haiku'      il lit et resume")
    print("   redacteur  llm='claude-sonnet-5'   il redige, le jugement compte")
    print("\n   Le champ `llm` est PAR AGENT, et c'est le levier le plus")
    print("   rentable : on paie la puissance la ou elle change le resultat.")
    print("   Un explorateur sur un modele cher, c'est une facture triplee")
    print("   pour un resultat identique.")

    print("\n3. LA MEMOIRE : trois choses sous un seul booleen\n")
    print("   Crew(..., memory=True) active :")
    print("     · la memoire COURTE   — le fil de l'execution en cours")
    print("     · la memoire LONGUE   — ce qui survit d'un run a l'autre")
    print("     · la memoire d'ENTITES — les gens, lieux et objets rencontres")
    print("\n   ⚠️ Elle demande un magasin vectoriel et un EMBEDDER, donc une")
    print("   cle. Ce projet ne l'active pas : `memory=True` echouerait sans")
    print("   fournisseur, et un projet qui ne demarre pas n'enseigne rien.")
    print("   La forme est d'une ligne ; ce sont ses dependances qui coutent.")

    print("\n4. LES VERSIONS\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   Borne des deux cotes. CrewAI 1.x a change trois choses que le")
    print("   cours enseigne : LiteLLM n'est plus embarque, crewai_tools est")
    print("   un paquet separe, et un @listen ne peut plus porter le nom de")
    print("   son evenement. Une borne haute est ce qui distingue « ca")
    print("   marchait hier » d'un projet qu'on peut donner a quelqu'un.")

    print("\n5. CE QU'IL FAUT SURVEILLER\n")
    for quoi, pourquoi in (
            ("token_usage par run", "la facture se fait dans les allers-retours"),
            ("le nombre d'appels", "un hierarchique en fait 2x un sequentiel"),
            ("les actions echouees", "une erreur d'outil revient au modele en silence"),
            ("max_iter par agent", "un agent qui boucle epuise son budget, pas le votre")):
        print(f"   {quoi:<26}{pourquoi}")


if __name__ == "__main__":
    main()
