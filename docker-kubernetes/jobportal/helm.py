"""Helm : des gabarits, des valeurs fusionnees, et un historique.

CE QU'UN CHART EST VRAIMENT
---------------------------
Un generateur de texte. `helm template` ne parle pas a Kubernetes : il lit
des gabarits, les remplit avec des valeurs, et rend du YAML. C'est tout —
et c'est ce qui rend Helm a la fois commode et piegeux :

- **une valeur absente rend une chaine vide**, pas une erreur. Le manifeste
  produit reste du YAML valide, et c'est Kubernetes qui refusera plus tard,
  avec un message qui ne parle pas de votre `values.yaml`. `required` est la
  seule facon d'echouer tot, et le chapitre 6 le mesure ;
- **`helm upgrade` compare des manifestes, pas des images**. Deux
  deploiements avec `image: …:latest` produisent le MEME manifeste :
  Kubernetes ne voit aucun changement, ne cree aucun ReplicaSet, et ne
  redemarre aucun pod. Votre nouvelle version n'est jamais partie.

⚠️ CE MOTEUR N'EST PAS CELUI DE HELM. Helm utilise `text/template` de Go et
les 60 fonctions de Sprig. Celui-ci couvre ce que le cours utilise —
`.Values`, `.Release`, `.Chart`, `if`/`else`/`end`, `range`, `include`,
`required`, `default`, `quote`, `upper`, `nindent`, `toYaml`, et le
rognage d'espaces `{{-` / `-}}`. Une construction non geree leve plutot que
de rendre du vide ; les ecarts de rendu sur les cas limites de Go ne sont
pas mesures.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import yaml_minimal


class ErreurHelm(Exception):
    """Une valeur `required` manquante, une fonction inconnue, un `end` oublie."""


# ── les valeurs ──────────────────────────────────────────────────────────

def fusionner(base: dict[str, Any], dessus: dict[str, Any]) -> dict[str, Any]:
    """Fusion PROFONDE : `values-production.yaml` ne remplace pas tout.

    ⚠️ Une liste, elle, est REMPLACEE en entier — jamais concatenee. C'est
    la regle de Helm, et la source d'une surprise reguliere : surcharger un
    seul element d'une liste demande de la reecrire entierement.
    """
    # >>> depart: fusionner en PROFONDEUR — une table se fond, une liste se remplace
    #     return {**base, **(dessus or {})}
    resultat = copy.deepcopy(base)
    for cle, valeur in (dessus or {}).items():
        if isinstance(valeur, dict) and isinstance(resultat.get(cle), dict):
            resultat[cle] = fusionner(resultat[cle], valeur)
        else:
            resultat[cle] = copy.deepcopy(valeur)
    return resultat
    # <<<


def poser(valeurs: dict[str, Any], chemin: str, valeur: Any) -> dict[str, Any]:
    """`--set image.tag=abc123` — le dernier mot, au-dessus de tout."""
    resultat = copy.deepcopy(valeurs)
    courant = resultat
    morceaux = chemin.split(".")
    for morceau in morceaux[:-1]:
        suivant = courant.get(morceau)
        if not isinstance(suivant, dict):
            suivant = {}
            courant[morceau] = suivant
        courant = suivant
    courant[morceaux[-1]] = valeur
    return resultat


def appliquer_set(valeurs: dict[str, Any],
                  affectations: list[str]) -> dict[str, Any]:
    resultat = valeurs
    for affectation in affectations:
        chemin, _, brute = affectation.partition("=")
        resultat = poser(resultat, chemin.strip(), _typer(brute.strip()))
    return resultat


def _typer(texte: str) -> Any:
    if texte in ("true", "false"):
        return texte == "true"
    if re.fullmatch(r"-?\d+", texte):
        return int(texte)
    return texte


# ── le moteur de gabarits ────────────────────────────────────────────────

_ACTION = re.compile(r"\{\{(-?)\s*(.*?)\s*(-?)\}\}", re.S)


@dataclass
class _Action:
    avant: str
    expression: str
    rogne_avant: bool
    rogne_apres: bool


def _decouper(gabarit: str) -> tuple[list[_Action], str]:
    """Decoupe en actions, et applique le ROGNAGE une bonne fois pour toutes.

    ⚠️ `{{-` retire les espaces AVANT l'action, `-}}` ceux d'APRES, saut de
    ligne compris. C'est un simple traitement de texte, independant de la
    logique : on le fait donc ici, en une passe, plutot que de le trainer
    dans le rendu des blocs. C'est aussi ce qui explique le YAML « colle »
    qu'on obtient quand on oublie un tiret.
    """
    actions: list[_Action] = []
    position = 0
    for trouve in _ACTION.finditer(gabarit):
        actions.append(_Action(gabarit[position:trouve.start()],
                               trouve.group(2), trouve.group(1) == "-",
                               trouve.group(3) == "-"))
        position = trouve.end()
    fin = gabarit[position:]

    for indice, action in enumerate(actions):
        if action.rogne_avant:
            action.avant = action.avant.rstrip()
        if action.rogne_apres:
            if indice + 1 < len(actions):
                actions[indice + 1].avant = actions[indice + 1].avant.lstrip()
            else:
                fin = fin.lstrip()
    return actions, fin


class Moteur:
    """Rend un gabarit dans un contexte."""

    def __init__(self, definitions: dict[str, str] | None = None) -> None:
        self.definitions = definitions or {}

    def rendre(self, gabarit: str, contexte: dict[str, Any]) -> str:
        actions, fin = _decouper(gabarit)
        sortie, position = self._bloc(actions, 0, contexte)
        if position != len(actions):
            raise ErreurHelm("« {{ end }} » en trop")
        return sortie + fin

    # -- le coeur -------------------------------------------------------

    def _bloc(self, actions: list[_Action], depart: int,
              contexte: dict[str, Any]) -> tuple[str, int]:
        """Rend jusqu'au premier `end` ou `else` de CE niveau.

        Les blocs imbriques sont consommes par `_conditionnelle` et
        `_boucle`, qui rendent l'indice d'apres leur propre `end` : le
        `end` que cette boucle rencontre est donc toujours le sien.
        """
        sortie = ""
        indice = depart
        while indice < len(actions):
            action = actions[indice]
            sortie += action.avant
            tete = (action.expression.split() or [""])[0]

            if tete in ("end", "else"):
                return sortie, indice
            if tete == "if":
                rendu, indice = self._conditionnelle(actions, indice, contexte)
                sortie += rendu
                continue
            if tete == "range":
                rendu, indice = self._boucle(actions, indice, contexte)
                sortie += rendu
                continue
            if tete in ("define", "with", "template", "block"):
                raise ErreurHelm(
                    f"construction non geree par ce moteur : « {tete} »")

            sortie += _texte(self._evaluer(action.expression, contexte))
            indice += 1
        return sortie, indice

    def _fin_du_bloc(self, actions: list[_Action],
                     depart: int) -> tuple[int, int]:
        """Rend (indice du `else` ou -1, indice du `end`)."""
        profondeur = 0
        sinon = -1
        for indice in range(depart + 1, len(actions)):
            tete = (actions[indice].expression.split() or [""])[0]
            if tete in ("if", "range", "with"):
                profondeur += 1
            elif tete == "else" and profondeur == 0:
                sinon = indice
            elif tete == "end":
                if profondeur == 0:
                    return sinon, indice
                profondeur -= 1
        raise ErreurHelm("« {{ end }} » manquant")

    def _conditionnelle(self, actions: list[_Action], depart: int,
                        contexte: dict[str, Any]) -> tuple[str, int]:
        condition = actions[depart].expression[len("if"):].strip()
        sinon, fin = self._fin_du_bloc(actions, depart)
        if _verite(self._evaluer(condition, contexte)):
            rendu, _ = self._bloc(actions, depart + 1, contexte)
        elif sinon != -1:
            rendu, _ = self._bloc(actions, sinon + 1, contexte)
        else:
            rendu = ""
        return rendu, fin + 1

    def _boucle(self, actions: list[_Action], depart: int,
                contexte: dict[str, Any]) -> tuple[str, int]:
        expression = actions[depart].expression[len("range"):].strip()
        _, fin = self._fin_du_bloc(actions, depart)
        collection = self._evaluer(expression, contexte)
        morceaux: list[str] = []
        for element in (collection or []):
            local = dict(contexte)
            local["."] = element
            rendu, _ = self._bloc(actions, depart + 1, local)
            morceaux.append(rendu)
        return "".join(morceaux), fin + 1

    # -- les expressions ------------------------------------------------

    def _evaluer(self, expression: str, contexte: dict[str, Any]) -> Any:
        etapes = [morceau.strip() for morceau in expression.split("|")]
        valeur = self._terme(etapes[0], contexte)
        for etape in etapes[1:]:
            valeur = self._tuyau(etape, valeur, contexte)
        return valeur

    def _terme(self, texte: str, contexte: dict[str, Any]) -> Any:
        texte = texte.strip()
        if not texte:
            return ""
        if texte.startswith(('"', "'")):
            return texte[1:-1]
        mots = _mots(texte)
        tete = mots[0]

        if tete == "required":
            if len(mots) != 3:
                raise ErreurHelm(f"« required » mal forme : {texte}")
            message = mots[1].strip('"\'')
            valeur = self._terme(mots[2], contexte)
            if valeur in (None, "", [], {}):
                raise ErreurHelm(message)
            return valeur
        if tete == "include":
            nom = mots[1].strip('"\'')
            if nom not in self.definitions:
                raise ErreurHelm(f"« include » d'un gabarit inconnu : {nom}")
            return self.rendre(self.definitions[nom], contexte).strip()
        if tete == "default":
            valeur = self._terme(mots[2], contexte) if len(mots) > 2 else None
            return valeur if _verite(valeur) else _litteral(mots[1])
        if tete == "printf":
            modele = mots[1].strip('"\'')
            return modele % tuple(self._terme(m, contexte) for m in mots[2:])
        if len(mots) > 1:
            raise ErreurHelm(f"expression non geree : « {texte} »")
        return _chercher(tete, contexte)

    def _tuyau(self, etape: str, valeur: Any,
               contexte: dict[str, Any]) -> Any:
        mots = _mots(etape)
        nom = mots[0]
        if nom == "quote":
            return f'"{_texte(valeur)}"'
        if nom == "upper":
            return _texte(valeur).upper()
        if nom == "lower":
            return _texte(valeur).lower()
        if nom == "default":
            return valeur if _verite(valeur) else _litteral(mots[1])
        if nom == "required":
            if not _verite(valeur):
                raise ErreurHelm(mots[1].strip('"\''))
            return valeur
        if nom == "nindent":
            retrait = " " * int(mots[1])
            return "\n" + "\n".join(retrait + ligne
                                    for ligne in _texte(valeur).splitlines())
        if nom == "indent":
            retrait = " " * int(mots[1])
            return "\n".join(retrait + ligne
                             for ligne in _texte(valeur).splitlines())
        if nom == "toYaml":
            return _en_yaml(valeur)
        raise ErreurHelm(f"fonction inconnue dans un tuyau : « {nom} »")


def _mots(texte: str) -> list[str]:
    """Decoupe en respectant les chaines entre guillemets."""
    morceaux: list[str] = []
    courant: list[str] = []
    guillemet: str | None = None
    for caractere in texte.strip():
        if guillemet:
            courant.append(caractere)
            if caractere == guillemet:
                guillemet = None
            continue
        if caractere in "\"'":
            guillemet = caractere
            courant.append(caractere)
            continue
        if caractere.isspace():
            if courant:
                morceaux.append("".join(courant))
                courant = []
            continue
        courant.append(caractere)
    if courant:
        morceaux.append("".join(courant))
    return morceaux


def _litteral(texte: str) -> Any:
    texte = texte.strip()
    if texte.startswith(('"', "'")):
        return texte[1:-1]
    return _typer(texte)


def _chercher(chemin: str, contexte: dict[str, Any]) -> Any:
    """`.Values.image.tag` — et une cle absente rend None, pas une erreur."""
    if chemin == ".":
        return contexte.get(".")
    if not chemin.startswith("."):
        return _litteral(chemin)
    courant: Any = contexte
    for morceau in chemin.lstrip(".").split("."):
        if not isinstance(courant, dict):
            return None
        courant = courant.get(morceau)
        if courant is None:
            return None
    return courant


def _verite(valeur: Any) -> bool:
    """La verite de Go : 0, "", nil, liste vide sont faux."""
    if valeur is None or valeur is False:
        return False
    if valeur in (0, "", [], {}):
        return False
    return True


def _texte(valeur: Any) -> str:
    if valeur is None:
        return ""
    if valeur is True:
        return "true"
    if valeur is False:
        return "false"
    return str(valeur)


def _en_yaml(valeur: Any, retrait: int = 0) -> str:
    espaces = " " * retrait
    if isinstance(valeur, dict):
        return "\n".join(f"{espaces}{cle}: {_en_yaml(sous, retrait + 2).lstrip()}"
                         if not isinstance(sous, (dict, list))
                         else f"{espaces}{cle}:\n{_en_yaml(sous, retrait + 2)}"
                         for cle, sous in valeur.items())
    if isinstance(valeur, list):
        return "\n".join(f"{espaces}- {_en_yaml(sous, retrait + 2).lstrip()}"
                         for sous in valeur)
    return f"{espaces}{_texte(valeur)}"


# ── le chart ─────────────────────────────────────────────────────────────

@dataclass
class Chart:
    nom: str
    version: str
    valeurs: dict[str, Any] = field(default_factory=dict)
    gabarits: dict[str, str] = field(default_factory=dict)
    definitions: dict[str, str] = field(default_factory=dict)
    dossier: Path | None = None


_DEFINE = re.compile(
    r'\{\{-?\s*define\s+"([^"]+)"\s*-?\}\}(.*?)\{\{-?\s*end\s*-?\}\}', re.S)


def charger(dossier: Path | str) -> Chart:
    base = Path(dossier)
    metadonnees = yaml_minimal.charger(
        (base / "Chart.yaml").read_text(encoding="utf-8")) or {}
    valeurs = yaml_minimal.charger(
        (base / "values.yaml").read_text(encoding="utf-8")) or {}
    chart = Chart(metadonnees.get("name", base.name),
                  str(metadonnees.get("version", "0.1.0")), valeurs,
                  dossier=base)
    for fichier in sorted((base / "templates").glob("*")):
        texte = fichier.read_text(encoding="utf-8")
        if fichier.name.startswith("_"):
            for nom, corps in _DEFINE.findall(texte):
                chart.definitions[nom] = corps
            continue
        chart.gabarits[fichier.name] = texte
    return chart


def valeurs_de(chart: Chart, fichiers: list[Path | str] | None = None,
               set_: list[str] | None = None) -> dict[str, Any]:
    """`values.yaml`, puis les `-f`, puis les `--set`. Dans cet ordre."""
    valeurs = copy.deepcopy(chart.valeurs)
    for fichier in (fichiers or []):
        valeurs = fusionner(valeurs, yaml_minimal.charger(
            Path(fichier).read_text(encoding="utf-8")) or {})
    return appliquer_set(valeurs, set_ or [])


def rendre(chart: Chart, valeurs: dict[str, Any],
           publication: str = "jobportal") -> dict[str, str]:
    """`helm template` : du YAML, fichier par fichier."""
    moteur = Moteur(chart.definitions)
    contexte = {
        "Values": valeurs,
        "Release": {"Name": publication, "Namespace": "default",
                    "Service": "Helm"},
        "Chart": {"Name": chart.nom, "Version": chart.version},
    }
    return {nom: moteur.rendre(gabarit, contexte)
            for nom, gabarit in sorted(chart.gabarits.items())}


# ── les publications ─────────────────────────────────────────────────────

@dataclass
class Revision:
    numero: int
    valeurs: dict[str, Any]
    manifestes: dict[str, str]
    action: str


class Publication:
    """Une release : un historique de manifestes RENDUS.

    ⚠️ C'est bien le YAML rendu qui est conserve, pas le chart. Un
    `helm rollback 1` reapplique les manifestes de la revision 1 — meme si
    le chart a change dix fois depuis. C'est ce qui rend le retour arriere
    fiable, et c'est aussi ce qui fait qu'il ne « rejoue » pas votre
    `values.yaml` d'aujourd'hui.
    """

    def __init__(self, nom: str, chart: Chart) -> None:
        self.nom = nom
        self.chart = chart
        self.revisions: list[Revision] = []

    def installer(self, valeurs: dict[str, Any]) -> Revision:
        return self._poser(valeurs, "install")

    def mettre_a_jour(self, valeurs: dict[str, Any]) -> Revision:
        return self._poser(valeurs, "upgrade")

    def annuler(self, numero: int) -> Revision:
        cible = self.revisions[numero - 1]
        revision = Revision(len(self.revisions) + 1,
                            copy.deepcopy(cible.valeurs),
                            dict(cible.manifestes),
                            f"rollback vers {numero}")
        self.revisions.append(revision)
        return revision

    def _poser(self, valeurs: dict[str, Any], action: str) -> Revision:
        revision = Revision(len(self.revisions) + 1, copy.deepcopy(valeurs),
                            rendre(self.chart, valeurs, self.nom), action)
        self.revisions.append(revision)
        return revision

    @property
    def courante(self) -> Revision:
        return self.revisions[-1]

    def identiques(self, a: int, b: int) -> bool:
        """⚠️ Deux revisions au manifeste identique ne changent RIEN."""
        return self.revisions[a - 1].manifestes == self.revisions[b - 1].manifestes

    def manifeste(self, revision: int | None = None) -> str:
        choisie = self.revisions[(revision or len(self.revisions)) - 1]
        return "\n---\n".join(choisie.manifestes[nom]
                              for nom in sorted(choisie.manifestes))
