"""Evaluer une politique IAM — l'algorithme, pas l'intuition.

POURQUOI ECRIRE CE MOTEUR
-------------------------
Parce que « qui a le droit de faire quoi » ne se lit pas : cela se CALCULE.
Une politique de vingt lignes peut accorder exactement l'inverse de ce que
son nom annonce, et personne ne s'en apercoit tant que quelqu'un n'essaie
pas. Ce module rend le calcul visible.

L'ORDRE D'EVALUATION, ET IL N'A QUE TROIS ETAPES
------------------------------------------------
1. on retient les declarations qui CORRESPONDENT a la demande — action,
   ressource et conditions, les trois a la fois ;
2. s'il en existe une seule avec `Deny`, la reponse est **refus**. Un refus
   explicite ne se rattrape jamais ;
3. sinon, s'il en existe une avec `Allow`, la reponse est **autorisation** ;
4. sinon, refus **implicite** : rien n'est permis par defaut.

⚠️ LE PIEGE QUI COUTE LE PLUS CHER
Une condition dont la CLE EST ABSENTE du contexte de la demande ne
correspond pas. Une declaration `Deny` conditionnee sur une cle absente ne
refuse donc RIEN — et c'est ainsi qu'une politique « interdire tout sans
MFA » laisse passer les appels qui n'annoncent pas de MFA du tout. C'est la
raison d'etre des operateurs `...IfExists`, et le chapitre 3 le mesure.

CE QUI EST SUPPORTE
-------------------
`Effect`, `Action` / `NotAction`, `Resource` / `NotResource`, `Condition`
avec `StringEquals`, `StringNotEquals`, `StringLike`, `StringNotLike`,
`Bool`, `NumericLessThan`, `NumericGreaterThan`, `IpAddress`,
`NotIpAddress`, `ArnLike`, `Null`, et le suffixe `IfExists`. Les jokers
`*` et `?`. Les politiques sont du JSON, tel qu'une console le rendrait.

CE QUI NE L'EST PAS
-------------------
Les politiques de ressource et leurs `Principal`, les frontieres de
permissions, les SCP d'organisation, les roles assumables et les cles de
contexte dynamiques (`${aws:username}`). Chacun leve plutot que d'etre
ignore en silence.
"""

from __future__ import annotations

import fnmatch
import ipaddress
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


class ErreurIam(Exception):
    """Une politique mal formee, ou un operateur non gere."""


AUTORISE = "autorise"
REFUSE_EXPLICITEMENT = "refuse explicitement"
REFUSE_IMPLICITEMENT = "refuse implicitement"


@dataclass(frozen=True)
class Demande:
    """Ce qu'un appel d'API presente au moteur d'autorisation."""

    action: str                       # « s3:GetObject »
    ressource: str                    # « arn:aws:s3:::cv-candidats/x.pdf »
    contexte: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.action} sur {self.ressource}"


@dataclass
class Declaration:
    """Un element de `Statement`."""

    effet: str                        # Allow | Deny
    actions: list[str]
    actions_exclues: list[str]
    ressources: list[str]
    ressources_exclues: list[str]
    conditions: dict[str, dict[str, Any]]
    identifiant: str = ""

    def correspond(self, demande: Demande) -> tuple[bool, str]:
        """Rend (correspond, raison) — la raison sert au chapitre."""
        # >>> depart: faire correspondre action, ressource et conditions — les trois
        #     return True, "correspond"
        if self.actions_exclues:
            # ⚠️ `NotAction` est une INVERSION, pas une exclusion polie :
            # « tout sauf ceci » veut dire « absolument tout le reste ».
            if any(_joker(motif, demande.action)
                   for motif in self.actions_exclues):
                return False, "l'action est dans NotAction"
        elif not any(_joker(motif, demande.action) for motif in self.actions):
            return False, "aucune action ne correspond"

        if self.ressources_exclues:
            if any(_joker(motif, demande.ressource)
                   for motif in self.ressources_exclues):
                return False, "la ressource est dans NotResource"
        elif not any(_joker(motif, demande.ressource)
                     for motif in self.ressources):
            return False, "aucune ressource ne correspond"

        for operateur, tests in self.conditions.items():
            passe, raison = _condition(operateur, tests, demande.contexte)
            if not passe:
                return False, raison
        return True, "correspond"
        # <<<


@dataclass
class Politique:
    nom: str
    declarations: list[Declaration] = field(default_factory=list)


@dataclass
class Verdict:
    """Le resultat, et ce qui l'a produit."""

    resultat: str
    declaration: Declaration | None = None
    examinees: list[tuple[Declaration, bool, str]] = field(default_factory=list)

    @property
    def autorise(self) -> bool:
        return self.resultat == AUTORISE

    def __str__(self) -> str:
        if self.declaration is None:
            return self.resultat
        return f"{self.resultat} par « {self.declaration.identifiant} »"


# ── la lecture ───────────────────────────────────────────────────────────

_OPERATEURS = {
    "StringEquals", "StringNotEquals", "StringEqualsIgnoreCase",
    "StringLike", "StringNotLike", "Bool", "NumericLessThan",
    "NumericGreaterThan", "NumericEquals", "IpAddress", "NotIpAddress",
    "ArnLike", "ArnNotLike", "Null", "DateLessThan", "DateGreaterThan",
}

_REFUSES = {
    "Principal": "les politiques de ressource (`Principal`) ne sont pas gerees",
    "NotPrincipal": "`NotPrincipal` n'est pas gere",
}


def _liste(valeur: Any) -> list[str]:
    if valeur is None:
        return []
    if isinstance(valeur, str):
        return [valeur]
    return [str(v) for v in valeur]


def charger(brut: dict[str, Any], nom: str = "politique") -> Politique:
    version = brut.get("Version")
    if version and version != "2012-10-17":
        raise ErreurIam(f"version de politique non geree : {version}")
    declarations = brut.get("Statement")
    if declarations is None:
        raise ErreurIam("politique sans « Statement »")
    if isinstance(declarations, dict):
        declarations = [declarations]

    politique = Politique(nom)
    for rang, element in enumerate(declarations, 1):
        for interdit, message in _REFUSES.items():
            if interdit in element:
                raise ErreurIam(message)
        effet = element.get("Effect")
        if effet not in ("Allow", "Deny"):
            raise ErreurIam(
                f"declaration {rang} : « Effect » doit valoir Allow ou Deny")
        if "Action" in element and "NotAction" in element:
            raise ErreurIam(
                f"declaration {rang} : « Action » et « NotAction » ensemble")
        conditions = element.get("Condition") or {}
        for operateur in conditions:
            nu = operateur.removesuffix("IfExists")
            if nu not in _OPERATEURS:
                raise ErreurIam(
                    f"declaration {rang} : operateur de condition inconnu "
                    f"« {operateur} »")
        politique.declarations.append(Declaration(
            effet,
            _liste(element.get("Action")), _liste(element.get("NotAction")),
            _liste(element.get("Resource")), _liste(element.get("NotResource")),
            conditions,
            element.get("Sid") or f"declaration {rang}"))
    return politique


def charger_fichier(chemin: Path | str) -> Politique:
    fichier = Path(chemin)
    return charger(json.loads(fichier.read_text(encoding="utf-8")),
                   fichier.stem)


# ── l'evaluation ─────────────────────────────────────────────────────────

def evaluer(politiques: list[Politique] | Politique,
            demande: Demande) -> Verdict:
    """L'algorithme, dans l'ordre : Deny explicite, puis Allow, puis refus."""
    # >>> depart: appliquer l'ordre — Deny explicite, puis Allow, puis refus implicite
    #     return Verdict(REFUSE_IMPLICITEMENT)
    liste = [politiques] if isinstance(politiques, Politique) else politiques
    examinees: list[tuple[Declaration, bool, str]] = []
    autorisation: Declaration | None = None

    for politique in liste:
        for declaration in politique.declarations:
            correspond, raison = declaration.correspond(demande)
            examinees.append((declaration, correspond, raison))
            if not correspond:
                continue
            if declaration.effet == "Deny":
                # ⚠️ On s'arrete la : un refus explicite l'emporte sur
                # toutes les autorisations, de toutes les politiques.
                return Verdict(REFUSE_EXPLICITEMENT, declaration, examinees)
            if autorisation is None:
                autorisation = declaration

    if autorisation is not None:
        return Verdict(AUTORISE, autorisation, examinees)
    return Verdict(REFUSE_IMPLICITEMENT, None, examinees)
    # <<<


def _joker(motif: str, valeur: str) -> bool:
    """`s3:*` contre `s3:GetObject`. Insensible a la casse, comme AWS."""
    return fnmatch.fnmatchcase(valeur.lower(), motif.lower())


def _condition(operateur: str, tests: dict[str, Any],
               contexte: dict[str, Any]) -> tuple[bool, str]:
    """⚠️ Une cle absente fait echouer la condition — sauf `...IfExists`."""
    # >>> depart: une cle ABSENTE fait echouer la condition — sauf avec « IfExists »
    #     return True, "conditions satisfaites"
    si_existe = operateur.endswith("IfExists")
    nu = operateur.removesuffix("IfExists")

    for cle, attendus in tests.items():
        if cle not in contexte:
            if si_existe:
                continue
            return False, (f"la cle « {cle} » est absente de la demande "
                           f"(condition {operateur})")
        valeur = contexte[cle]
        if not _comparer(nu, valeur, attendus):
            return False, f"« {cle} » = {valeur!r} ne satisfait pas {operateur}"
    return True, "conditions satisfaites"
    # <<<


def _comparer(operateur: str, valeur: Any, attendus: Any) -> bool:
    candidats = attendus if isinstance(attendus, list) else [attendus]

    if operateur in ("StringEquals", "ArnLike", "StringLike",
                     "StringEqualsIgnoreCase", "ArnNotLike",
                     "StringNotEquals", "StringNotLike"):
        texte = str(valeur)
        if operateur in ("StringEquals",):
            resultat = any(texte == str(c) for c in candidats)
        elif operateur == "StringEqualsIgnoreCase":
            resultat = any(texte.lower() == str(c).lower() for c in candidats)
        elif operateur in ("StringLike", "ArnLike"):
            resultat = any(fnmatch.fnmatchcase(texte, str(c))
                           for c in candidats)
        elif operateur == "StringNotEquals":
            resultat = all(texte != str(c) for c in candidats)
        else:      # StringNotLike, ArnNotLike
            resultat = all(not fnmatch.fnmatchcase(texte, str(c))
                           for c in candidats)
        return resultat

    if operateur == "Bool":
        return any(bool(valeur) == (str(c).lower() == "true")
                   for c in candidats)

    if operateur == "Null":
        # `Null` teste la PRESENCE de la cle, pas sa valeur.
        return any((valeur is None) == (str(c).lower() == "true")
                   for c in candidats)

    if operateur.startswith("Numeric"):
        nombre = float(valeur)
        cibles = [float(c) for c in candidats]
        if operateur == "NumericLessThan":
            return any(nombre < c for c in cibles)
        if operateur == "NumericGreaterThan":
            return any(nombre > c for c in cibles)
        return any(nombre == c for c in cibles)

    if operateur in ("IpAddress", "NotIpAddress"):
        adresse = ipaddress.ip_address(str(valeur))
        dedans = any(adresse in ipaddress.ip_network(str(c), strict=False)
                     for c in candidats)
        return dedans if operateur == "IpAddress" else not dedans

    if operateur.startswith("Date"):
        texte = str(valeur)
        if operateur == "DateLessThan":
            return any(texte < str(c) for c in candidats)
        return any(texte > str(c) for c in candidats)

    raise ErreurIam(f"operateur non gere a l'evaluation : « {operateur} »")


# ── mise en lumiere ──────────────────────────────────────────────────────

def expliquer(verdict: Verdict, demande: Demande) -> list[str]:
    """Le raisonnement, declaration par declaration."""
    lignes = [f"{demande}"]
    for declaration, correspond, raison in verdict.examinees:
        marque = "✓" if correspond else "·"
        lignes.append(f"   {marque} {declaration.effet:<5} "
                      f"{declaration.identifiant:<28} {raison}")
    lignes.append(f"   → {verdict}")
    return lignes


def actions_accordees(politiques: list[Politique] | Politique,
                      catalogue: list[str], ressource: str,
                      contexte: dict[str, Any] | None = None) -> list[str]:
    """Ce que la politique accorde VRAIMENT, sur un catalogue d'actions.

    C'est la seule facon honnete de repondre a « cette politique est-elle
    en lecture seule ? » : on essaie, action par action.
    """
    return [action for action in catalogue
            if evaluer(politiques,
                       Demande(action, ressource, contexte or {})).autorise]
