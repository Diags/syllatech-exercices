"""Lire un Dockerfile — vraiment, pas a coups d'expressions regulieres.

POURQUOI ECRIRE CE LECTEUR
--------------------------
Le cours enseigne le *cache de couches*, le *multi-stage* et ce qui reste
dans une image. Les trois sont des consequences de la STRUCTURE du fichier :
quelle instruction cree quelle couche, quelle etape copie depuis quelle
autre. Il faut donc un arbre, pas une suite de lignes.

CE QUI EST SUPPORTE
-------------------
- les commentaires `#`, y compris en fin de fichier ;
- la continuation de ligne par `\\`, avec commentaires intercales ;
- `ARG` avant le premier `FROM` (la seule instruction qui y est permise) ;
- `FROM image[:tag] [AS nom]`, autant de fois qu'on veut ;
- `COPY [--from=etape] [--chown=x] source... destination` et `ADD` ;
- les formes *exec* (`["a", "b"]`) et *shell* (`a b`) de `RUN`, `CMD` et
  `ENTRYPOINT` — la difference n'est pas cosmetique, le chapitre 1 la mesure ;
- `ENV`, `WORKDIR`, `USER`, `EXPOSE`, `LABEL`, `VOLUME`, `HEALTHCHECK`.

CE QUI NE L'EST PAS
-------------------
Les directives d'analyseur (`# syntax=`), les heredocs (`<<EOF`), les
montages BuildKit (`RUN --mount=type=cache`) et `ONBUILD`. Chacun leve une
`ErreurDockerfile` nommant la ligne, plutot que d'etre ignore en silence —
un fichier a moitie compris produirait un cache faux, donc une lecon fausse.
"""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Les instructions que ce lecteur connait. Toute autre leve.
CONNUES = {
    "FROM", "RUN", "COPY", "ADD", "ENV", "ARG", "WORKDIR", "USER",
    "EXPOSE", "LABEL", "VOLUME", "CMD", "ENTRYPOINT", "HEALTHCHECK",
}

# Celles dont l'execution cree une couche dans l'image finale. Les autres
# ne changent que les metadonnees — elles creent bien une entree dans
# l'historique, mais de taille nulle.
POSENT_UNE_COUCHE = {"FROM", "RUN", "COPY", "ADD"}

_REFUSEES = {
    "ONBUILD": "ONBUILD n'est pas gere",
    "STOPSIGNAL": "STOPSIGNAL n'est pas gere",
    "SHELL": "SHELL n'est pas gere",
}


class ErreurDockerfile(Exception):
    """Une syntaxe non geree, avec le numero de ligne."""


@dataclass
class Instruction:
    """Une instruction, telle qu'elle est ecrite et telle qu'elle se lit."""

    mot: str                       # FROM, RUN, COPY...
    arguments: str                 # tout ce qui suit, continuations recollees
    ligne: int
    drapeaux: dict[str, str] = field(default_factory=dict)   # --from=, --chown=

    @property
    def pose_une_couche(self) -> bool:
        return self.mot in POSENT_UNE_COUCHE

    @property
    def texte(self) -> str:
        """La forme normalisee, qui sert de CLE DE CACHE.

        ⚠️ C'est bien le texte qui compte, pas le resultat. Deux `RUN` qui
        font la meme chose ecrits differemment sont deux couches
        differentes ; et un `RUN apt-get update` inchange est reutilise
        depuis le cache meme si le depot distant a change depuis — c'est
        la cause du celebre « ca marchait hier ».
        """
        drapeaux = "".join(f" --{cle}={valeur}"
                           for cle, valeur in sorted(self.drapeaux.items()))
        return f"{self.mot}{drapeaux} {self.arguments}".strip()

    def __str__(self) -> str:
        return self.texte


@dataclass
class Etape:
    """Une etape de construction : un `FROM` et tout ce qui le suit."""

    base: str
    nom: str | None                # `AS nom`, ou None
    rang: int
    instructions: list[Instruction] = field(default_factory=list)

    @property
    def designation(self) -> str:
        return self.nom if self.nom else str(self.rang)

    def cherchees(self, mot: str) -> list[Instruction]:
        return [i for i in self.instructions if i.mot == mot]

    @property
    def utilisateur(self) -> str:
        """Le dernier `USER` de l'etape, ou « root » s'il n'y en a pas.

        ⚠️ « root » par defaut n'est pas une opinion : c'est la valeur par
        defaut de Docker. Une image sans `USER` tourne en root, et un
        echappement du conteneur y devient un root sur l'hote.
        """
        utilisateurs = self.cherchees("USER")
        return utilisateurs[-1].arguments.strip() if utilisateurs else "root"


@dataclass
class Dockerfile:
    """Le fichier entier : ses `ARG` de tete, puis ses etapes."""

    arguments_de_tete: list[Instruction] = field(default_factory=list)
    etapes: list[Etape] = field(default_factory=list)
    chemin: Path | None = None

    @property
    def multi_etages(self) -> bool:
        return len(self.etapes) > 1

    @property
    def finale(self) -> Etape:
        return self.etapes[-1]

    def etape(self, designation: str) -> Etape | None:
        for etape in self.etapes:
            if etape.nom == designation or str(etape.rang) == designation:
                return etape
        return None

    @property
    def instructions(self) -> list[Instruction]:
        return [i for etape in self.etapes for i in etape.instructions]


# ── la lecture ───────────────────────────────────────────────────────────

_CONTINUE = re.compile(r"\\\s*$")


def _recoller(source: str) -> list[tuple[int, str]]:
    """Rend (numero de ligne, ligne complete), continuations recollees.

    Les commentaires places AU MILIEU d'une continuation sont retires, ce
    que fait Docker : ils ne coupent pas l'instruction.
    """
    # >>> depart: recoller les lignes terminees par « \ », commentaires intercales compris
    #     return [(n, l.strip()) for n, l in enumerate(source.splitlines(), 1)
    #             if l.strip() and not l.strip().startswith("#")]
    lignes: list[tuple[int, str]] = []
    tampon = ""
    depart = 0
    for numero, brute in enumerate(source.splitlines(), 1):
        nue = brute.strip()
        if tampon and nue.startswith("#"):
            continue                      # commentaire dans une continuation
        if not tampon:
            if not nue or nue.startswith("#"):
                continue
            depart = numero
        morceau = _CONTINUE.sub("", brute).strip()
        if _CONTINUE.search(brute):
            tampon = f"{tampon} {morceau}".strip()
            continue
        complete = f"{tampon} {morceau}".strip() if tampon else morceau
        lignes.append((depart, complete))
        tampon = ""
    if tampon:
        lignes.append((depart, tampon))
    return lignes
    # <<<


_DRAPEAU = re.compile(r"^--([A-Za-z0-9-]+)=(\S+)\s*")


def _decouper(ligne: str, numero: int) -> Instruction:
    mot, _, reste = ligne.partition(" ")
    mot = mot.upper()
    if mot in _REFUSEES:
        raise ErreurDockerfile(f"ligne {numero} : {_REFUSEES[mot]}")
    if mot not in CONNUES:
        raise ErreurDockerfile(
            f"ligne {numero} : instruction inconnue « {mot} »")
    reste = reste.strip()
    if reste.startswith("<<"):
        raise ErreurDockerfile(
            f"ligne {numero} : les heredocs ne sont pas geres")
    drapeaux: dict[str, str] = {}
    while True:
        trouve = _DRAPEAU.match(reste)
        if trouve is None:
            break
        cle, valeur = trouve.group(1), trouve.group(2)
        if cle == "mount":
            raise ErreurDockerfile(
                f"ligne {numero} : « --mount » (BuildKit) n'est pas gere")
        drapeaux[cle] = valeur
        reste = reste[trouve.end():]
    if not reste:
        raise ErreurDockerfile(f"ligne {numero} : « {mot} » sans argument")
    return Instruction(mot, reste.strip(), numero, drapeaux)


_FROM = re.compile(r"^(\S+)(?:\s+[Aa][Ss]\s+(\S+))?$")


def analyser(source: str, chemin: Path | None = None) -> Dockerfile:
    """Le Dockerfile, en etapes."""
    fichier = Dockerfile(chemin=chemin)

    # ⚠️ La directive d'analyseur se lit AVANT le recollage : c'est un
    # commentaire, et `_recoller` jette les commentaires. Elle doit de plus
    # etre la premiere ligne non vide du fichier — ailleurs, Docker
    # l'ignore, ce qui est une source de perplexite a soi seule.
    for numero, brute in enumerate(source.splitlines(), 1):
        if not brute.strip():
            continue
        if brute.strip().startswith("# syntax"):
            raise ErreurDockerfile(
                f"ligne {numero} : les directives d'analyseur "
                f"(« # syntax= ») ne sont pas gerees")
        break

    for numero, ligne in _recoller(source):
        instruction = _decouper(ligne, numero)

        if instruction.mot == "FROM":
            trouve = _FROM.match(instruction.arguments)
            if trouve is None:
                raise ErreurDockerfile(
                    f"ligne {numero} : « FROM » mal forme — "
                    f"« {instruction.arguments} »")
            base, nom = trouve.group(1), trouve.group(2)
            etape = Etape(base, nom, len(fichier.etapes), [instruction])
            fichier.etapes.append(etape)
            continue

        if not fichier.etapes:
            # ⚠️ Avant le premier FROM, SEUL `ARG` est permis. C'est ce qui
            # permet de parametrer la version de l'image de base.
            if instruction.mot != "ARG":
                raise ErreurDockerfile(
                    f"ligne {numero} : « {instruction.mot} » avant le premier "
                    f"« FROM » — seul « ARG » y est permis")
            fichier.arguments_de_tete.append(instruction)
            continue

        fichier.etapes[-1].instructions.append(instruction)

    if not fichier.etapes:
        raise ErreurDockerfile("aucun « FROM » : rien a construire")
    return fichier


def analyser_fichier(chemin: Path | str) -> Dockerfile:
    fichier = Path(chemin)
    return analyser(fichier.read_text(encoding="utf-8"), fichier)


# ── lire une instruction ─────────────────────────────────────────────────

def forme_exec(instruction: Instruction) -> bool:
    """`["java", "-jar"]` plutot que `java -jar`.

    ⚠️ La difference n'est pas cosmetique. En forme *shell*, Docker lance
    `/bin/sh -c "votre commande"` : le PID 1 est le shell, et il ne
    transmet PAS le SIGTERM a votre programme. A l'arret, Kubernetes
    attend donc la fin du delai de grace puis tue le conteneur — d'ou des
    coupures de connexions et des transactions perdues, a chaque
    deploiement.
    """
    return instruction.arguments.strip().startswith("[")


def arguments_exec(instruction: Instruction) -> list[str]:
    """Les arguments, quelle que soit la forme."""
    brut = instruction.arguments.strip()
    if forme_exec(instruction):
        try:
            valeurs = json.loads(brut)
        except json.JSONDecodeError as erreur:
            raise ErreurDockerfile(
                f"ligne {instruction.ligne} : forme exec mal formee — "
                f"{erreur}") from erreur
        return [str(v) for v in valeurs]
    return shlex.split(brut)


def sources_et_destination(instruction: Instruction) -> tuple[list[str], str]:
    """Les chemins d'un `COPY` ou d'un `ADD`."""
    morceaux = shlex.split(instruction.arguments)
    if len(morceaux) < 2:
        raise ErreurDockerfile(
            f"ligne {instruction.ligne} : « {instruction.mot} » attend au "
            f"moins une source et une destination")
    return morceaux[:-1], morceaux[-1]


def tag_de_base(etape: Etape) -> str:
    """Le tag de l'image de base, ou « latest » s'il est absent.

    ⚠️ Un `FROM openjdk` sans tag vaut `openjdk:latest` : l'image change
    sous vos pieds sans qu'une ligne du depot n'ait bouge. C'est la
    premiere chose que releve un audit, et la derniere qu'on corrige.
    """
    base = etape.base
    if "@" in base:
        return base.split("@", 1)[1]
    nom = base.rsplit("/", 1)[-1]
    return nom.split(":", 1)[1] if ":" in nom else "latest"


def resume(fichier: Dockerfile) -> list[str]:
    """Le fichier, tel qu'on le lit dans un terminal."""
    lignes: list[str] = []
    for etape in fichier.etapes:
        titre = (f"etape {etape.rang} « {etape.nom} »" if etape.nom
                 else f"etape {etape.rang}")
        lignes.append(f"{titre} — FROM {etape.base}")
        for instruction in etape.instructions[1:]:
            marque = "couche" if instruction.pose_une_couche else "     "
            lignes.append(f"   {marque}  {instruction.texte}")
    return lignes


def contributions(fichier: Dockerfile) -> dict[str, Any]:
    """Ce que le multi-stage laisse entrer dans l'image finale."""
    finale = fichier.finale
    venues = []
    for instruction in finale.instructions:
        source = instruction.drapeaux.get("from")
        if source:
            venues.append((source, instruction.arguments))
    return {
        "etapes": len(fichier.etapes),
        "etape_finale": finale.designation,
        "venues_d_ailleurs": venues,
        "utilisateur": finale.utilisateur,
    }
