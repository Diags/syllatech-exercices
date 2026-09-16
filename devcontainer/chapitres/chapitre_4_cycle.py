"""Chapitre 4 — Le cycle de vie : six commandes, et une qu'on n'attend pas.

    uv run python chapitres/chapitre_4_cycle.py

L'ordre des six commandes n'est pas une convention : il est écrit dans le
schéma publié, chacune citant ses voisines. Ce qui coûte cher n'est pas
l'ordre — c'est **la fréquence**, et **ce que `waitFor` laisse derrière**.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import cycle, schema_publie                        # noqa: E402
from jobportal.commun import (                                    # noqa: E402
    A_CORRIGER, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import COMMANDES, charger, depuis_texte     # noqa: E402


def principal() -> None:
    utf8()
    portail = charger(PORTAIL / "devcontainer.json")

    titre(1, "L'ORDRE EST DANS LE SCHEMA, PAS DANS UNE CONVENTION")
    for nom in COMMANDES:
        phrase = schema_publie.description(nom)
        # On ne garde que la premiere phrase : la suite decrit les formes.
        essentiel = phrase.split(". If this is")[0]
        print(f"   {nom}")
        for l in plier(essentiel, 60):
            print(f"        {l}")
    print()
    for l in plier(
        "Chaque description cite ses voisines. L'ordre est donc verifiable "
        "sans le lancer, et il ne depend d'aucun outil : c'est le contrat."):
        print(f"   {l}")

    titre(2, "OU, ET COMBIEN DE FOIS")
    tableau(["commande", "s'execute", "frequence"],
            [[nom, cycle.OU[nom], cycle.QUAND[nom]] for nom in COMMANDES],
            [24, 12, 32])
    print()
    for l in plier(
        "Une seule ligne dit « hote » : c'est ce qui garantit l'identite "
        "d'une machine a l'autre. Et les deux dernieres lignes sont celles "
        "qui coutent : `postStartCommand` se rejoue a chaque demarrage, "
        "`postAttachCommand` a chaque onglet de terminal."):
        print(f"   {l}")

    titre(3, "`waitFor` — CE QUI A FINI QUAND ON VOUS REND LA MAIN")
    ligne("valeur par defaut", schema_publie.description("waitFor")
          .split("The default is ")[-1].strip('."'), 30)
    ligne("valeurs acceptees",
          ", ".join(schema_publie.enum("waitFor")), 30)
    print()
    for l in plier(
        "Cinq valeurs, et `postAttachCommand` n'en fait pas partie : on ne "
        "peut pas attendre la derniere. Le fichier "
        "`configs/a-corriger/06-waitfor-trop-loin.json` le tente, et le "
        "schema le refuse."):
        print(f"   {l}")
    print()
    sans_waitfor = depuis_texte("""{
      "image": "x",
      "onCreateCommand": "mvn dependency:go-offline",
      "updateContentCommand": "mvn compile",
      "postCreateCommand": "mvn flyway:migrate"
    }""")
    avec = depuis_texte("""{
      "image": "x",
      "onCreateCommand": "mvn dependency:go-offline",
      "updateContentCommand": "mvn compile",
      "postCreateCommand": "mvn flyway:migrate",
      "waitFor": "postCreateCommand"
    }""")
    tableau(["configuration", "waitFor", "encore en cours quand vous tapez"],
            [["sans la ligne `waitFor`", sans_waitfor.attend,
              ", ".join(cycle.creation_apres_la_main(sans_waitfor)) or "rien"],
             ["avec `waitFor`", avec.attend,
              ", ".join(cycle.creation_apres_la_main(avec)) or "rien"]],
            [26, 24, 34])
    print()
    for l in plier(
        "Les deux fichiers ne different que d'une ligne, et les migrations de "
        "base ne sont pas finies dans le premier. Le symptome est une "
        "premiere requete qui echoue sur une table absente, une seule fois, "
        "et jamais quand on cherche a la reproduire."):
        print(f"   {l}")

    titre(4, "LA FAUTE CLASSIQUE : TOUT DANS `postCreateCommand`")
    tout = charger(A_CORRIGER / "07-tout-dans-postcreate.json")
    ligne("le schema accepte ?",
          "oui" if schema_publie.valide(tout) else "non", 34)
    ligne("commandes de creation posees",
          ", ".join(e.nom for e in cycle.deroulement(tout)
                    if e.quand == cycle.CREATION), 34)
    ligne("decoupe perdue ?",
          "oui" if cycle.tout_dans_post_create(tout) else "non", 34)
    ligne("encore en cours quand vous tapez",
          ", ".join(cycle.creation_apres_la_main(tout)), 34)
    print()
    for l in plier(
        "Ce n'est pas faux — c'est valide, et cela marche. Ce qu'on perd est "
        "la decoupe : un outil qui preconstruit une image peut mettre en "
        "cache `onCreateCommand` et `updateContentCommand`, pas ce qui arrive "
        "apres. Tout reunir a la fin, c'est renoncer au cache ET obtenir la "
        "main avant la fin."):
        print(f"   {l}")

    titre(5, "TROIS FORMES, ET CELLE QUI N'A PAS DE SHELL")
    exemples = [
        ("chaine", "mvn compile && echo fini"),
        ("tableau", ["mvn", "compile", "&&", "echo", "fini"]),
        ("objet", {"deps": "mvn dependency:go-offline", "front": "npm ci"}),
    ]
    tableau(["forme", "ce que le schema en dit", "shell ?"],
            [[nom, cycle.forme(valeur),
              "oui" if cycle.utilise_le_shell(valeur) else "NON"]
             for nom, valeur in exemples], [12, 40, 10])
    print()
    tableau_ = charger(A_CORRIGER / "08-tableau-avec-shell.json")
    ligne("le schema accepte ?",
          "oui" if schema_publie.valide(tableau_) else "non", 34)
    for nom in tableau_.commandes_posees:
        pieges = cycle.piege_de_shell(tableau_.commande(nom))
        if pieges:
            ligne(f"  {nom}",
                  f"operateurs inertes : {', '.join(pieges)}", 32)
    print()
    for l in plier(
        "Un tableau est « run as a single command without shell ». Le `&&` "
        "devient donc un ARGUMENT de `mvn`, et `$HOME` une chaine de cinq "
        "caracteres. La commande ne plante pas forcement : elle fait autre "
        "chose, ce qui est pire."):
        print(f"   {l}")

    titre(6, "L'OBJET, ET LE PARALLELISME")
    phrase = schema_publie.description("postCreateCommand")
    parallele = "If this is an object" + phrase.split("If this is an object")[-1]
    print("   Ce que le schema dit de la troisieme forme :")
    print()
    for l in plier(parallele, 62):
        print(f"      {l}")
    print()
    for l in plier(
        "C'est la seule facon de gagner du temps sans rien deplacer : deux "
        "preparations independantes qui prennent chacune une minute en "
        "prennent une au total. Le prix est que leurs sorties s'entremelent "
        "dans le journal."):
        print(f"   {l}")

    titre(7, "LE CYCLE DU PORTAIL")
    tableau(["commande", "ou", "frequence", "finie a la main ?"],
            [[e.nom, e.ou, e.quand, "oui" if e.avant_la_main else "non"]
             for e in cycle.deroulement(portail)], [24, 12, 28, 20])
    print()
    ligne("waitFor ecrit ?",
          "oui" if portail.attend_est_ecrit else "non (defaut)", 30)
    ligne("encore en cours quand vous tapez",
          ", ".join(cycle.creation_apres_la_main(portail)) or "rien", 34)
    ligne("rejoue a chaque onglet",
          ", ".join(cycle.cout_par_onglet(portail)) or "rien", 30)
    print()
    for l in plier(
        "Rien ne traine, et rien ne se rejoue a l'ouverture d'un terminal. "
        "Ce n'est pas un hasard : c'est la ligne `waitFor: postCreateCommand` "
        "et l'absence de `postAttachCommand` — deux decisions, quatre mots."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : ports, utilisateur et montages.\n")


if __name__ == "__main__":
    principal()
