"""Chapitre 2 — Sorties fiables : outils typés et validation.

    uv run python chapitres/chapitre_2_sortie_typee.py

L'agent de ce chapitre est un VRAI `agno.agent.Agent`, avec un vrai
`output_schema`. Le modèle est un substitut déterministe : ce qu'on mesure
ici est ce que la VALIDATION accepte et refuse, pas le comportement d'un LLM.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError                          # noqa: E402

from jobportal.commun import ligne, plier, titre, utf8        # noqa: E402
from jobportal.evaluateur import Evaluateur                   # noqa: E402
from jobportal.executeurs import Bride                        # noqa: E402
from jobportal.soumissions import CORPUS                      # noqa: E402
from jobportal.verdict import LONGUEUR_RESUME, Verdict        # noqa: E402


def main() -> None:
    utf8()

    titre(1, "LE PARAMETRE S'APPELLE output_schema")
    from agno.agent import Agent

    try:
        Agent(response_model=Verdict)
        ligne("Agent(response_model=…)", "accepte", 30)
    except TypeError as erreur:
        ligne("Agent(response_model=…)", "TypeError", 30)
        for morceau in plier(str(erreur), 62):
            print(f"   {'':30} {morceau}")
    agent = Agent(output_schema=Verdict)
    ligne("Agent(output_schema=…)", f"accepte → {agent.output_schema.__name__}",
          30)
    print()
    print("   La suggestion de Python est le piege : « reasoning_model »")
    print("   EXISTE. L'accepter donne un agent qui demarre, ne type plus")
    print("   rien, et facture un modele de raisonnement. Une erreur qui")
    print("   propose une correction plausible et fausse coute plus cher")
    print("   qu'une erreur seche.")

    titre(2, "CE QUE LE SCHEMA ACCEPTE")
    bon = Verdict(score=80, tests_passes=["tri decroissant"],
                  comportement_suspect=False,
                  resume="La fonction trie dans l'ordre demande.")
    ligne("un verdict valide", f"score={bon.score} suspect={bon.comportement_suspect}",
          26)
    print()
    print("   Et ce qu'il refuse :\n")
    essais = [
        ("score au-dela de 100", {"score": 120, "resume": "x"}),
        ("score en toutes lettres", {"score": "excellent", "resume": "x"}),
        ("resume trop long",
         {"score": 50, "resume": "x" * (LONGUEUR_RESUME + 1)}),
        ("champ invente",
         {"score": 50, "resume": "x", "acces_admin": True}),
        ("21 tests passes",
         {"score": 50, "resume": "x", "tests_passes": [str(n) for n in range(21)]}),
    ]
    for etiquette, donnees in essais:
        try:
            Verdict(**donnees)
            ligne(etiquette, "ACCEPTE", 28)
        except ValidationError as erreur:
            (premiere,) = erreur.errors()[:1]
            ligne(etiquette, f"refuse — {premiere['type']}", 28)
    print()
    print("   Le plus important est l'avant-dernier. Sans")
    print("   « extra: forbid », un champ invente serait IGNORE : le verdict")
    print("   validerait, et la ligne en trop finirait dans un dictionnaire")
    print("   que quelqu'un lira un jour. Refuser vaut mieux qu'ignorer.")

    titre(3, "LA BORNE QUI COMPTE VRAIMENT")
    hostile = next(s for s in CORPUS if s.nom == "plainte-affective")
    evaluation = Evaluateur(executeur=Bride()).evaluer(hostile)
    ligne("texte hostile produit",
          f"{len(evaluation.execution.sortie)} signes", 30)
    ligne("ce qui atteint le modele",
          f"{evaluation.signes_hostiles_au_modele} signes", 30)
    ligne("ce que le verdict peut porter",
          f"{LONGUEUR_RESUME} signes au maximum (resume)", 30)
    print()
    print("   Typer la reponse ne rend pas l'agent honnete : cela rend son")
    print("   enveloppe PREVISIBLE. Un attaquant qui controle la sortie du")
    print("   programme controle une partie de ce que l'agent ecrira — mais")
    print("   il ne peut ecrire que dans un champ de 400 signes, jamais dans")
    print("   « score » qui est un entier, jamais dans un champ qu'il")
    print("   inventerait.")
    print()
    print("   C'est exactement une contrainte VARCHAR(400) : elle n'empeche")
    print("   pas d'ecrire des betises, elle empeche d'ecrire n'importe ou.")

    titre(4, "CE QUE LA SORTIE TYPEE NE FAIT PAS")
    ligne("le verdict rendu", str(evaluation), 22)
    print()
    print("   Le score est 100 pour une soumission dont le tri est correct")
    print("   mais qui a demande un traitement de faveur dans sa sortie. La")
    print("   structure est parfaite, la validation passe, et le contenu est")
    print("   faux.")
    print()
    print("   Une sortie typee borne le DEGAT, elle ne detecte pas la")
    print("   manipulation. C'est le chapitre 4 qui s'en occupe — et le")
    print("   chapitre 3 d'abord, parce qu'il faut commencer par empecher le")
    print("   code de toucher la machine.")

    titre(5, "LE VERDICT EST UN OBJET, DONC IL S'UTILISE")
    for soumission in ("tri-correct", "tri-inverse", "tri-qui-plante"):
        s = next(x for x in CORPUS if x.nom == soumission)
        e = Evaluateur(executeur=Bride()).evaluer(s)
        ligne(soumission, f"score={e.verdict.score:>3}  "
                          f"tests={e.verdict.tests_passes}", 20)
    print()
    print("   Ces trois lignes s'inserent dans une base, un tableau de bord")
    print("   ou un courriel sans qu'aucune analyse de texte ne soit ecrite.")
    print("   C'est le gain quotidien de la sortie typee ; la securite n'en")
    print("   est que la moitie.")

    print("\n   Au chapitre suivant : empecher le code de toucher la machine.\n")


if __name__ == "__main__":
    main()
