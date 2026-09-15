"""Chapitre 4 — Gateway : vos API en outils MCP.

    uv run python chapitres/chapitre_4_gateway.py

Le cours affirme deux choses : qu'une spécification OpenAPI devient un
catalogue d'outils sans écrire d'adaptateur, et qu'exposer deux cents
opérations « noierait l'agent ». La première se dérive, la seconde se compte.
Ce chapitre fait les deux.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.api_jobportal import specification                 # noqa: E402
from jobportal.commun import ligne, titre, utf8                   # noqa: E402
from jobportal.passerelle import (chercher, cout_en_jetons,       # noqa: E402
                                  depuis_lambda, depuis_openapi,
                                  doublons)

DEMANDES = [
    "Trouve les offres DevOps a Lyon",
    "Cree une candidature pour ce candidat",
    "Planifie un entretien la semaine prochaine",
    "Quels sont les postes disponibles ?",       # synonyme : aucun mot commun
]


def main() -> None:
    utf8()
    spec = specification()
    outils = depuis_openapi(spec)

    titre(1, "UNE SPECIFICATION, UN CATALOGUE")
    ligne("chemins dans la spec", str(len(spec["paths"])), 32)
    ligne("outils MCP derives", str(len(outils)), 32)
    ligne("adaptateurs a ecrire a la main", "0", 32)
    print()
    for outil in outils[:4]:
        print(f"   {outil.nom:<22} {outil.description}")
    print(f"   {'…':<22} et {len(outils) - 4} autres")
    print()
    print("   Chaque operation devient un outil, avec son schema d'entree.")
    print("   C'est tout ce que la Gateway fait de « magique » — et ce n'est")
    print("   pas magique : c'est de la derivation. Ce qu'elle supprime, ce")
    print("   sont les quarante adaptateurs qu'on ecrirait a la main, et les")
    print("   quarante occasions de se tromper de nom de parametre.")

    titre(2, "UN outil MCP, EN ENTIER")
    print(f"   {outils[0].en_json()[:300]}")
    print()
    print("   C'est ce que le modele lit. La description compte autant que le")
    print("   nom : c'est elle qui lui fait choisir cet outil plutot qu'un")
    print("   autre. Un « summary » vide dans l'OpenAPI donne un outil que")
    print("   l'agent n'appellera jamais a propos.")

    titre(3, "CE QUE LE CATALOGUE ENTIER COUTE")
    total = cout_en_jetons(outils)
    ligne("catalogue complet",
          f"{len(outils):>2} outils, ~{total} jetons, a CHAQUE tour", 28)
    for demande in DEMANDES[:3]:
        selection = chercher(outils, demande, 5)
        cout = cout_en_jetons(selection)
        ligne(f"  « {demande[:24]}… »",
              f"{len(selection):>2} outils, ~{cout:>4} jetons   "
              f"({total / max(1, cout):.0f}× moins)", 28)
    print()
    print("   La recherche ne rend pas systematiquement cinq outils : elle")
    print("   rend ceux qui correspondent. Demander « les 10 plus pertinents »")
    print("   quand deux seulement correspondent en rend deux — le plafond")
    print("   est une limite, pas une cible.")
    print()
    print("   Le prix n'est pas paye une fois : il l'est a CHAQUE tour de la")
    print("   boucle de l'agent, puisque la liste des outils fait partie de")
    print("   la requete. Sur une conversation de dix tours, c'est dix fois.")
    print()
    print("   Et le cout en jetons n'est meme pas le pire : plus la liste est")
    print("   longue, plus le modele choisit mal. C'est la raison premiere de")
    print("   la recherche semantique — la facture n'est que la seconde.")

    titre(4, "LA RECHERCHE, DEMANDE PAR DEMANDE")
    for demande in DEMANDES:
        trouves = chercher(outils, demande, 3)
        print(f"   « {demande} »")
        if not trouves:
            print("      AUCUN outil — la demande n'a aucun mot en commun")
            continue
        for outil in trouves:
            print(f"      {outil.nom}")
    print()
    print("   Trois choses a remarquer, et deux sont genantes.")
    print()
    print("   · La derniere demande ne rend RIEN : « postes disponibles » n'a")
    print("     aucun mot commun avec « offres ». Une recherche qui compte")
    print("     les mots partages rate tous les synonymes.")
    print("   · « Cree une candidature » rend un « delete » en premier. Un")
    print("     mauvais selecteur ne se contente pas de rater : il peut")
    print("     proposer l'outil DESTRUCTEUR. C'est pourquoi un outil qui")
    print("     supprime doit demander confirmation, quel que soit le")
    print("     selecteur qui l'a choisi.")
    print("   · « getStatsOffres » apparait deux fois. Ce n'est pas un bug de")
    print("     l'affichage — c'est le doublon de la section 6.")
    print()
    print("   La vraie Gateway utilise des plongements vectoriels : elle")
    print("   rapproche « poste » de « offre » sans mot commun. Le principe")
    print("   est le meme — ne presenter que quelques outils — mais le")
    print("   rappel est d'un autre ordre. Le cours « Bases vectorielles »")
    print("   explique pourquoi.")

    titre(5, "LAMBDA, ET LE MELANGE DES SOURCES")
    maison = depuis_lambda(
        "calculerScoreCandidat",
        "Calcule le score d'adequation d'un candidat pour une offre",
        {"type": "object",
         "properties": {"candidat_id": {"type": "string"},
                        "offre_id": {"type": "string"}},
         "required": ["candidat_id", "offre_id"]})
    melange = outils + [maison]
    ligne("outils issus d'OpenAPI", str(len(outils)), 26)
    ligne("outils issus de Lambda", "1", 26)
    ligne("le modele voit", f"{len(melange)} outils, tous pareils", 26)
    print()
    for outil in chercher(melange, "score d'adequation d'un candidat", 2):
        print(f"   {outil.nom:<24} {outil.description[:44]}")
    print()
    print("   Une Lambda et une operation REST arrivent au modele sous la")
    print("   MEME forme. C'est ce qui permet de mutualiser : un outil defini")
    print("   une fois sert a tous les agents, sans code de colle duplique.")

    titre(6, "LE PIEGE : DEUX CHEMINS, UN SEUL NOM")
    repetes = doublons(outils)
    ligne("outils derives", str(len(outils)), 26)
    ligne("noms distincts", str(len({o.nom for o in outils})), 26)
    ligne("noms en double", ", ".join(repetes) or "aucun", 26)
    print()
    if repetes:
        for outil in [o for o in outils if o.nom in repetes]:
            print(f"      {outil.nom:<20} {outil.description}")
        print()
        print("   « /stats/offres » et « /stats/offres/ » n'ont pas")
        print("   d'operationId : la Gateway deduit un nom, et les deux")
        print("   tombent sur le meme. Un outil en masque un autre, et")
        print("   l'agent appelle le mauvais — ou plutot, appelle le bon nom")
        print("   et obtient l'autre operation.")
        print()
        print("   La parade tient en une ligne : un operationId sur CHAQUE")
        print("   operation de votre OpenAPI. Verifiez-le avant de brancher")
        print("   une spec que vous n'avez pas ecrite.")

    print("\n   Au chapitre suivant : ce que l'agent retient d'une fois sur")
    print("   l'autre.\n")


if __name__ == "__main__":
    main()
