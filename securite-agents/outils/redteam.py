#!/usr/bin/env python3
"""Le harnais de red teaming — rejouer les attaques contre SES PROPRES defenses.

    python outils/redteam.py              le tableau complet
    python outils/redteam.py --couche delimitation    une couche seule
    python outils/redteam.py --ci         code de sortie 1 si une attaque passe

Le chapitre 6 propose `promptfoo redteam run`, qui attaque une application HTTP
en la sollicitant vraiment. C'est le bon outil pour une vraie application, et
ce harnais ne le remplace pas : il fait la meme chose sans reseau, sans cle et
sans fournisseur, pour que la boucle dure une seconde pendant qu'on ECRIT les
defenses.

CE QU'IL MESURE, ET QU'ON NE PEUT PAS OBTENIR EN LISANT

  1. combien d'attaques passent sans aucune defense ;
  2. combien passent avec chaque couche PRISE SEULE ;
  3. combien passent avec toutes.

Le point 2 est celui qui compte, et il est deconcertant la premiere fois :
aucune couche seule n'arrete tout. C'est ce que « defense en profondeur »
veut dire, et c'est mesurable plutot que declaratif.

A BRANCHER SUR LA CI. Le chapitre 6 le dit et c'est exact : une defense qu'on
ne rejoue pas se degrade sans bruit. Une regle ajoutee au prompt, un outil
ajoute a la liste, et la couverture baisse — sans qu'aucun test fonctionnel
ne bouge. `--ci` rend 1 des qu'une attaque passe.
"""

from __future__ import annotations

import sys
from dataclasses import fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.attaques import ATTAQUES, CV_HONNETE, Attaque    # noqa: E402
from jobportal.defenses import Agent, Configuration             # noqa: E402

COUCHES = [f.name for f in fields(Configuration)]


def rejouer(configuration: Configuration, attaques=ATTAQUES) -> list[tuple[Attaque, object]]:
    return [(a, Agent(configuration).analyser_cv(a.charge)) for a in attaques]


def passees(configuration: Configuration) -> int:
    """Le nombre d'attaques qui obtiennent une CONSEQUENCE REELLE.

    Pas le nombre d'injections reussies : le nombre de fois ou quelque chose
    s'est reellement passe. C'est la seule mesure sur laquelle on peut viser
    zero — voir Resultat.impact.
    """
    return sum(1 for _, r in rejouer(configuration) if r.impact)


def obeissances(configuration: Configuration) -> int:
    return sum(1 for _, r in rejouer(configuration) if r.obeie)


def une_couche(nom: str) -> Configuration:
    return Configuration(**{nom: True})


def sauf_une(nom: str) -> Configuration:
    return Configuration(**{c: c != nom for c in COUCHES})


def faux_positif() -> bool:
    """Une defense qui bloque un CV honnete est une defense qu'on desactivera.

    C'est la mesure qu'on oublie, et c'est celle qui decide de l'adoption :
    un garde-fou penible est un garde-fou retire dans la semaine.
    """
    return Agent(Configuration.toutes()).analyser_cv(CV_HONNETE).bloquee_par is not None


def tableau() -> int:
    total = len(ATTAQUES)

    print(f"\n  {total} attaques du corpus OWASP, rejouees contre nos defenses.\n")
    print("  1. SANS AUCUNE DEFENSE — l'anti-patron du chapitre 1\n")
    for attaque, resultat in rejouer(Configuration.aucune()):
        marque = "IMPACT" if resultat.impact else ("obeie " if resultat.obeie else "bloque")
        print(f"     {marque}  {attaque.code:<14}{attaque.nom:<44}{resultat.effet or ''}")
    nu = passees(Configuration.aucune())
    print(f"\n     {nu}/{total} attaques avec une CONSEQUENCE REELLE,")
    print(f"     {obeissances(Configuration.aucune())}/{total} injections suivies par le modele.")

    print("\n  2. CHAQUE COUCHE, PRISE SEULE\n")
    print(f"     {'couche':<22}{'passent':>9}{'arretees':>10}")
    for couche in COUCHES:
        reste = passees(une_couche(couche))
        print(f"     {couche:<22}{reste:>9}{nu - reste:>10}")
    print("\n     AUCUNE ne suffit. C'est le resultat qui compte, et il est")
    print("     deconcertant la premiere fois : chaque couche laisse passer")
    print("     quelque chose. « Defense en profondeur » n'est pas une")
    print("     precaution rhetorique, c'est une necessite arithmetique.")

    print("\n  3. TOUTES LES COUCHES SAUF UNE — ce que chacune apporte VRAIMENT\n")
    print(f"     {'sans...':<22}{'passent':>9}")
    for couche in COUCHES:
        print(f"     {couche:<22}{passees(sauf_une(couche)):>9}")
    print("\n     Lecture du tableau, et elle demande de l'attention : une")
    print("     couche dont le retrait ne change RIEN n'est pas inutile — elle")
    print("     est redondante AVEC LES AUTRES, SUR CE CORPUS. Retirez-en deux,")
    print("     et le compte remonte.")
    print("\n     Le seul retrait qui coute ici est celui de la delimitation :")
    print("     c'est la couche la plus rentable, et de loin. Elle reste")
    print("     insuffisante seule (tableau 2), parce qu'elle repose sur")
    print("     l'obeissance du modele. Les autres ne servent qu'aux cas ou")
    print("     elle fuit — et ce sont exactement les cas graves.")

    print("\n  4. TOUTES LES COUCHES\n")
    for attaque, resultat in rejouer(Configuration.toutes()):
        marque = "IMPACT" if resultat.impact else ("obeie " if resultat.obeie else "bloque")
        print(f"     {marque}  {attaque.code:<14}{attaque.nom:<44}"
              f"{resultat.bloquee_par or 'modele cadre'}")
    complet = passees(Configuration.toutes())
    obeies = obeissances(Configuration.toutes())
    print(f"\n     {obeies}/{total} injection(s) encore suivie(s) par le modele,")
    print(f"     {complet}/{total} avec une CONSEQUENCE REELLE.")
    print("\n     C'est le vrai resultat, et il est plus honnete qu'un zero")
    print("     triomphant : l'injection reussit encore, et elle ne peut rien.")
    print("     Aucune consigne de prompt ne fait tomber la premiere colonne a")
    print("     zero — c'est une propriete du modele, pas de votre code. Les")
    print("     couches font tomber la seconde, et c'est le seul objectif")
    print("     reellement atteignable.")

    print("\n  5. ET LE CAS QU'ON OUBLIE : UN CV HONNETE\n")
    print(f"     bloque a tort : {'OUI — a corriger' if faux_positif() else 'non'}")
    print("\n     Une defense qui bloque les utilisateurs legitimes sera")
    print("     desactivee dans la semaine. Le taux de faux positifs fait")
    print("     partie de la mesure, pas des bonnes intentions.")
    return complet


def main() -> int:
    console.utf8()
    if "--couche" in sys.argv:
        nom = sys.argv[sys.argv.index("--couche") + 1]
        if nom not in COUCHES:
            print(f"  couches : {', '.join(COUCHES)}")
            return 2
        for attaque, resultat in rejouer(une_couche(nom)):
            marque = "IMPACT" if resultat.impact else ("obeie " if resultat.obeie else "bloque")
            print(f"  {marque}  {attaque.nom:<44}{resultat.bloquee_par or ''}")
        return 0

    restantes = tableau()
    if "--ci" in sys.argv:
        print(f"\n  code de sortie : {1 if restantes else 0}")
        return 1 if restantes else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
