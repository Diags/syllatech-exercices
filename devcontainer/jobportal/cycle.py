"""Le cycle de vie : l'ordre, la fréquence, et ce que `waitFor` décide.

L'ordre n'est pas une convention : il est **écrit dans le schéma publié**,
chaque commande citant ses voisines dans sa propre description.

    initializeCommand     « before anything else », sur l'HÔTE
    onCreateCommand       « after initializeCommand and before
                            updateContentCommand »
    updateContentCommand  « after onCreateCommand and before
                            postCreateCommand »
    postCreateCommand     « after updateContentCommand and before
                            postStartCommand »
    postStartCommand      « after postCreateCommand and before
                            postAttachCommand »
    postAttachCommand     « after postStartCommand »

Et `waitFor` : « The user command to wait for before continuing execution in
the background while the UI is starting up. **The default is
"updateContentCommand"**. »

Ce module en tire ce qui compte : ce qui a fini quand on vous rend la main.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jobportal.config import COMMANDES, Config

# Ou la commande s'execute. Une seule est sur la machine de l'utilisateur.
HOTE = "hote"
CONTENEUR = "conteneur"

OU = {
    "initializeCommand": HOTE,
    "onCreateCommand": CONTENEUR,
    "updateContentCommand": CONTENEUR,
    "postCreateCommand": CONTENEUR,
    "postStartCommand": CONTENEUR,
    "postAttachCommand": CONTENEUR,
}

# A quelle frequence. C'est la nuance qui coute cher : une installation de
# dependances dans `postAttachCommand` se rejoue a chaque onglet de terminal.
CREATION = "a la creation, une fois"
DEMARRAGE = "a chaque demarrage"
ATTACHEMENT = "a chaque connexion d'un outil"

QUAND = {
    "initializeCommand": CREATION,
    "onCreateCommand": CREATION,
    "updateContentCommand": CREATION,
    "postCreateCommand": CREATION,
    "postStartCommand": DEMARRAGE,
    "postAttachCommand": ATTACHEMENT,
}


def forme(valeur: Any) -> str:
    """Les trois formes qu'une commande accepte, et ce qu'elles changent.

    Le schema les decrit pour chacune des six : « If this is a single
    string, it will be run in a shell. If this is an array of strings, it
    will be run as a single command without shell. If this is an object,
    each provided command will be run in parallel. »
    """
    if isinstance(valeur, str):
        return "chaine — passee au shell"
    if isinstance(valeur, list):
        return "tableau — execute SANS shell"
    if isinstance(valeur, dict):
        return f"objet — {len(valeur)} commande(s) en PARALLELE"
    return "(absente)"


def utilise_le_shell(valeur: Any) -> bool:
    """Un tableau n'est PAS passe au shell : `&&`, `|`, `>` et `$VAR` y
    sont des arguments litteraux, pas des operateurs.
    """
    if isinstance(valeur, str):
        return True
    if isinstance(valeur, dict):
        return all(utilise_le_shell(v) for v in valeur.values())
    return False


def piege_de_shell(valeur: Any) -> list[str]:
    """Les operateurs de shell trouves dans un tableau — donc inertes."""
    if not isinstance(valeur, list):
        return []
    operateurs = ("&&", "||", "|", ">", ">>", "<", ";", "$")
    return sorted({o for element in valeur if isinstance(element, str)
                   for o in operateurs if o in element})


@dataclass
class Etape:
    nom: str
    ou: str
    quand: str
    valeur: Any
    avant_la_main: bool          # a-t-elle fini quand l'outil rend la main ?


def deroulement(config: Config) -> list[Etape]:
    """Les commandes posees, dans l'ordre, avec ce que `waitFor` en fait.

    `avant_la_main` est vrai jusqu'a la commande designee par `waitFor`
    INCLUSE : c'est la definition de « the command to wait for ».
    """
    # TODO : marquer comme finies les commandes jusqu'a `waitFor` INCLUSE
    return [Etape(n, OU[n], QUAND[n], config.brut[n], True)
            for n in COMMANDES if n in config.brut]


def apres_la_main(config: Config) -> list[str]:
    """Les commandes qui tournent ENCORE quand vous avez la main.

    « si vos migrations de base sont dans postCreateCommand, vous obtenez la
    main avant qu'elles soient finies » — mesure-le sur votre fichier.
    """
    return [e.nom for e in deroulement(config) if not e.avant_la_main]


def cout_par_onglet(config: Config) -> list[str]:
    """Ce qui se rejoue a chaque connexion d'un outil.

    Le symptome que le cours decrit : « depuis quelque temps, ouvrir un
    terminal prend vingt secondes ».
    """
    return [e.nom for e in deroulement(config) if e.quand == ATTACHEMENT]


def cout_par_demarrage(config: Config) -> list[str]:
    return [e.nom for e in deroulement(config)
            if e.quand in (DEMARRAGE, ATTACHEMENT)]


def tout_dans_post_create(config: Config) -> bool:
    """La faute classique : les trois commandes de creation reduites a une.

    « on perd la decoupe : les outils qui preconstruisent des images ne
    peuvent alors rien mettre en cache. »
    """
    creation = [n for n in ("onCreateCommand", "updateContentCommand",
                            "postCreateCommand") if n in config.brut]
    return creation == ["postCreateCommand"]


def creation_apres_la_main(config: Config) -> list[str]:
    """Les commandes de CREATION qui tournent encore quand on a la main.

    C'est la mesure qui interesse : `postStartCommand` et
    `postAttachCommand` sont apres `waitFor` par nature, et ont leurs
    propres avertissements. Ce qui surprend, c'est une preparation qu'on
    croyait finie — une migration de base, typiquement.
    """
    return [e.nom for e in deroulement(config)
            if not e.avant_la_main and e.quand == CREATION]
