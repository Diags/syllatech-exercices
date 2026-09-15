"""Les chemins se résolvent par rapport au FICHIER, pas au dépôt.

C'est la phrase du chapitre 1 — « plusieurs propriétés se résolvent
relativement à ce fichier, pas à la racine du dépôt » — et c'est la source
d'erreur numéro un. Le schéma publié le dit lui-même pour `build.dockerfile`
(« The path is relative to the devcontainer.json file »).

Conséquence : comme `devcontainer.json` vit dans `.devcontainer/`, la racine
du dépôt s'écrit `".."`. Écrire `"."` donne un contexte réduit au dossier
`.devcontainer`, où le `pom.xml` n'est pas — et le message d'erreur parle de
fichiers introuvables, pas de contexte.

Ce module ne devine rien : il résout, puis il regarde si le fichier existe.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from jobportal.config import Config


@dataclass
class Resolution:
    propriete: str
    ecrit: str
    resolu: Path
    existe: bool
    depuis_la_racine: str        # ce que le meme chemin donnerait, lu de la racine

    @property
    def verdict(self) -> str:
        return "trouve" if self.existe else "INTROUVABLE"


def _relatif(base: Path, racine: Path, chemin: str) -> Resolution | None:
    resolu = (base / chemin).resolve()
    return Resolution("", chemin, resolu, resolu.exists(),
                      str((racine / chemin).resolve()))


def resoudre(config: Config, racine: Path | None = None,
             base: Path | None = None) -> list[Resolution]:
    """Les chemins relatifs d'une configuration, resolus et verifies.

    `base` est le dossier du fichier — c'est de LA que partent les chemins.
    On peut l'imposer pour repondre a « et si ce fichier etait pose dans
    .devcontainer/ ? », ce que les chapitres font pour mesurer une faute de
    contexte sans deplacer le fichier.

    `racine` sert de point de comparaison : c'est la ou un lecteur presse
    croit que le chemin part.
    """
    if config.fichier is None and base is None:
        return []
    base = base or config.fichier.parent
    racine = racine or base.parent
    sorties = []

    construction = config.construction
    for propriete, valeur in (("build.dockerfile", construction.get("dockerfile")),
                              ("build.context", construction.get("context"))):
        if isinstance(valeur, str):
            r = _relatif(base, racine, valeur)
            r.propriete = propriete
            sorties.append(r)

    for i, fichier in enumerate(config.fichiers_compose()):
        r = _relatif(base, racine, fichier)
        r.propriete = f"dockerComposeFile[{i}]"
        sorties.append(r)

    return sorties


def contexte_est_la_racine(config: Config, base: Path | None = None) -> bool | None:
    """`build.context` designe-t-il bien la racine du depot ?

    Rend None si aucune construction n'est declaree. La question a un sens
    independamment de l'endroit ou le fichier est range : ce qui compte est
    que le contexte remonte d'un cran au-dessus du dossier qui le contient.
    """
    # TODO : dire si le contexte remonte bien d'un cran au-dessus du fichier
    return None


def manquants(config: Config, racine: Path | None = None,
              base: Path | None = None) -> list[Resolution]:
    return [r for r in resoudre(config, racine, base) if not r.existe]


def visible_dans_le_contexte(config: Config, fichier: str,
                             base: Path | None = None) -> bool | None:
    """Le fichier que la construction attend est-il DANS le contexte ?

    C'est la question qui compte, et elle n'a pas la meme reponse que
    « le contexte existe-t-il ? ». Un `context: "."` designe un dossier bien
    reel — `.devcontainer/` — ou le `pom.xml` ne se trouve pas. Docker
    repond alors « file not found », ce qui envoie chercher au mauvais
    endroit.
    """
    contexte = config.construction.get("context")
    if contexte is None:
        return None
    base = base or (config.fichier.parent if config.fichier else None)
    if base is None:
        return None
    return ((base / contexte).resolve() / fichier).exists()
