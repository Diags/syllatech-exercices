#!/usr/bin/env python3
"""Le harnais d'evasion — ou se situe exactement la frontiere.

    python outils/evasion.py            le tableau complet
    python outils/evasion.py --ci       code 1 si un niveau tient moins que prevu

Il rejoue chaque evasion du corpus contre chaque niveau executable sur CETTE
machine, et compare au niveau annonce. Les ecarts sont signales : un corpus
qui ne correspond plus a la realite est pire qu'aucun corpus, parce qu'on le
croit.
"""

from __future__ import annotations

import platform
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                    # noqa: E402
from jobportal.conteneur import OBLIGATOIRES, commande, verifier  # noqa: E402
from jobportal.evasions import CODE_HONNETE, EVASIONS            # noqa: E402
from jobportal.niveaux import NIVEAUX, bornes_disponibles        # noqa: E402

ORDRE = ["naif", "restreint", "processus"]


def mesurer() -> dict[str, dict[str, bool]]:
    """Rend {evasion: {niveau: a-t-elle echappe ?}}."""
    return {e.nom: {n: NIVEAUX[n](e.code).echappe for n in ORDRE}
            for e in EVASIONS}


def accord(evasion, ligne: dict[str, bool]) -> bool:
    """Le niveau annonce bloque-t-il vraiment, ici ?

    On ne verifie QUE ce qui est verifiable : « conteneur » n'est pas
    executable sur cette machine, et « (POSIX) » ne l'est pas sous Windows.
    Affirmer un accord qu'on n'a pas mesure serait exactement le defaut que
    ce projet denonce.
    """
    niveau = evasion.nommage
    if niveau not in ORDRE:
        return True         # non verifiable ici : on ne conclut pas
    return not ligne[niveau]


def tableau() -> int:
    console.utf8()
    print(f"\n  Machine : {platform.system()} — bornes « resource » "
          f"{'disponibles' if bornes_disponibles() else 'ABSENTES'}\n")
    if not bornes_disponibles():
        print("  ⚠️ Sous Windows, le module « resource » n'existe pas : le niveau")
        print("     « processus » applique un delai mais AUCUNE borne memoire.")
        print("     Les chiffres ci-dessous en tiennent compte, et c'est ainsi")
        print("     qu'il faut les lire — une isolation dont on ignore ce qu'elle")
        print("     fait sur la machine de production n'est pas une isolation.\n")

    mesures = mesurer()
    print(f"  {'evasion':<40}" + "".join(f"{n:>12}" for n in ORDRE)
          + "   niveau qui l'ARRETE")
    ecarts = 0
    for evasion in EVASIONS:
        ligne = mesures[evasion.nom]
        rendu = f"  {evasion.nom:<40}"
        for niveau in ORDRE:
            rendu += f"{('ECHAPPE' if ligne[niveau] else 'bloque'):>12}"
        ok = accord(evasion, ligne)
        verifiable = evasion.nommage in ORDRE
        marque = "" if ok else "  ← ANNONCE DEMENTIE"
        if not verifiable:
            marque = "  (non verifiable ici)"
        print(rendu + f"   {evasion.nommage:<18}{marque}")
        ecarts += not ok

    print(f"\n  {ecarts} annonce(s) dementie(s) par la mesure.")
    if ecarts:
        print("     Un corpus qui ne correspond plus a la realite est pire")
        print("     qu'aucun corpus : on le croit.")
    else:
        print("     Chaque niveau verifiable ici tient ce qu'il annonce.")

    print("\n  ⚠️ CES NIVEAUX NE SONT PAS UNE ECHELLE\n")
    total = len(EVASIONS)
    for niveau in ORDRE:
        arretees = sum(1 for e in EVASIONS if not mesures[e.nom][niveau])
        print(f"     {niveau:<14}{arretees:>3}/{total} ligne(s) arretee(s)")
    print(f"     {'conteneur':<14}{'?':>3}/{total}   NON MESURE ICI — demande un noyau Linux")
    print("\n     « restreint » arrete PLUS de lignes que « processus », et il")
    print("     est pourtant infiniment moins sur. Les deux ne font pas la")
    print("     meme chose :")
    print("\n       restreint   retire des NOMS. Rien n'est contenu : ce qui")
    print("                   s'echappe s'echappe dans VOTRE processus, avec")
    print("                   vos droits.")
    print("       processus   ne retire AUCUN nom — « import os » y marche.")
    print("                   Mais le dommage meurt avec le sous-processus.")
    print("\n     Compter les lignes bloquees melange donc deux axes. La bonne")
    print("     question n'est pas « combien ? » mais « QU'EST-CE QUI ATTEINT")
    print("     L'HOTE ? » — et la reponse est : rien, des le niveau processus,")
    print("     sauf ce qui passe par le reseau ou le disque.")

    print("\n  LE RESULTAT QUI COMPTE\n")
    subclasses = mesures["remontee par __subclasses__"]
    print(f"     « remontee par __subclasses__ » contre « restreint » : "
          f"{'ECHAPPE' if subclasses['restreint'] else 'bloque'}")
    print("\n     Six lignes de Python, publiees depuis vingt ans, et la liste")
    print("     blanche de builtins ne sert plus a rien. On NE PEUT PAS isoler")
    print("     Python depuis Python : l'arbre des classes est accessible")
    print("     depuis n'importe quel objet, et il mene a l'importateur.")
    print("\n     La frontiere n'est pas dans le langage. Elle est dans le")
    print("     systeme — un processus, puis un noyau.")

    print("\n  ET LE CAS QU'ON OUBLIE : LE CODE HONNETE\n")
    for niveau in ORDRE:
        resultat = NIVEAUX[niveau](CODE_HONNETE)
        etat = "ok" if resultat.echappe else f"CASSE ({resultat.erreur[:40]})"
        print(f"     {niveau:<14}{etat}")
    print("\n     Une isolation qui casse l'usage legitime sera retiree. Le")
    print("     verifier fait partie de la mesure.")

    print("\n  LE QUATRIEME NIVEAU — genere et verifie, pas lance\n")
    genere = commande("runner:python", "print(1)", runtime="runsc")
    for s in verifier(genere):
        print(f"     {s.gravite:<10}{s.drapeau}")
    print(f"     {len(verifier(genere))} souci(s) sur la commande generee.")
    print(f"\n     {len(OBLIGATOIRES)} drapeaux obligatoires, chacun rattache a")
    print("     l'evasion qu'il neutralise. Une commande de durcissement se")
    print("     relit comme du code — c'est ce que fait jobportal/conteneur.py,")
    print("     et il tourne sans Docker.")
    return ecarts


def main() -> int:
    ecarts = tableau()
    if "--ci" in sys.argv:
        # Sous Windows les ecarts sont attendus : on ne fait echouer que la
        # ou l'on peut vraiment conclure.
        return 1 if (ecarts and bornes_disponibles()) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
