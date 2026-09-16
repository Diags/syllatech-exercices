"""Les options d'une Feature deviennent des variables d'environnement.

`amont/devcontainer-features.md` donne la règle en JavaScript, exactement :

    (str: string) => str
        .replace(/[^\\w_]/g, '_')
        .replace(/^[\\d_]+/g, '_')
        .toUpperCase();

Trois substitutions, dans cet ordre. La deuxième est celle qu'on ne lit pas
bien : elle remplace **toute une suite** de chiffres ou de soulignés en tête
par **un seul** souligné. `2fa` devient donc `_FA`, pas `_2FA` — et `22fa`
devient `_FA` lui aussi. Deux options différentes, une seule variable.

Et : « Any options defined by a Feature's `devcontainer-feature.json` that
are omitted in the user's `devcontainer.json` will be implicitly exported as
its default value. » Une option qu'on ne passe pas est donc exportée quand
même.
"""

from __future__ import annotations

import re
from typing import Any

# `\w` contient deja `_` : `[^\w_]` vaut `[^\w]`. On garde la forme de
# l'amont pour que la transcription se relise a cote de sa source.
_NON_MOT = re.compile(r"[^\w_]")
_TETE = re.compile(r"^[\d_]+")


def nom_de_variable(option: str) -> str:
    """La regle amont, transcrite substitution par substitution."""
    # TODO : appliquer les trois substitutions, dans l'ordre de l'amont
    return option.upper()


def collisions(options: list[str]) -> dict[str, list[str]]:
    """Les options distinctes qui produisent la MEME variable.

    Ce n'est pas theorique : `2fa` et `22fa` collent toutes deux sur `_FA`.
    Une Feature qui declare les deux n'en verra qu'une.
    """
    par_variable: dict[str, list[str]] = {}
    for option in options:
        par_variable.setdefault(nom_de_variable(option), []).append(option)
    return {v: o for v, o in par_variable.items() if len(o) > 1}


def _valeur(brute: Any) -> str:
    """Le fichier `devcontainer-features.env` est du texte.

    Un booleen JSON y devient donc « true » ou « false » en minuscules, ce
    qui compte pour un `install.sh` qui teste `[ "$MON_OPTION" = "true" ]`.
    """
    if isinstance(brute, bool):
        return "true" if brute else "false"
    return str(brute)


def env(manifeste: dict[str, Any],
        passees: dict[str, Any]) -> dict[str, str]:
    """Le contenu de `devcontainer-features.env`, pour une Feature.

    Toutes les options DECLAREES par la Feature y sont, avec leur valeur par
    defaut si l'utilisateur ne l'a pas passee. Une option passee mais NON
    declaree n'y est pas : la Feature ne la connait pas.
    """
    declarees = manifeste.get("options")
    declarees = declarees if isinstance(declarees, dict) else {}
    # TODO : exporter TOUTES les options declarees, defaut compris
    return {nom_de_variable(n): _valeur(v) for n, v in passees.items()}


def ignorees(manifeste: dict[str, Any],
             passees: dict[str, Any]) -> list[str]:
    """Les options passees que la Feature ne declare pas.

    Elles ne sont pas exportees, et rien ne le signale : une faute de frappe
    dans un nom d'option est donc silencieuse, et la Feature s'installe avec
    sa valeur par defaut.
    """
    declarees = manifeste.get("options")
    declarees = declarees if isinstance(declarees, dict) else {}
    return sorted(set(passees) - set(declarees))


def utilisateurs(remote_user: str | None,
                 container_user: str | None) -> dict[str, str]:
    """Les variables que l'outil ajoute, en plus des options.

    `amont/features-user-env-variables.md` : « Pass `_REMOTE_USER` and
    `_CONTAINER_USER` environment variables to the features scripts […] If
    no `remoteUser` is configured, `_REMOTE_USER` is set to the same value
    as `_CONTAINER_USER`. »

    Les scripts d'installation tournent en `root` : sans ces variables, une
    Feature ne saurait pas a qui appartiendra le dossier qu'elle cree.
    """
    conteneur = container_user or "root"
    distant = remote_user or conteneur
    foyer = (lambda u: "/root" if u == "root" else f"/home/{u}")
    return {
        "_CONTAINER_USER": conteneur,
        "_REMOTE_USER": distant,
        "_CONTAINER_USER_HOME": foyer(conteneur),
        "_REMOTE_USER_HOME": foyer(distant),
    }
