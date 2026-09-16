"""Quelles routes peuvent attraper une requête — et quand plusieurs le peuvent.

Le prédicat d'une route est entièrement spécifié par le schéma publié :

    RouteMatch  : {path, method, headers, query}  — tous doivent passer (ET)
    LocalRoute.matches : une LISTE de RouteMatch  — un seul suffit (OU)
    PathMatch   : exact | pathPrefix | regex
    HeaderMatch : {name, value: exact|regex}
    défaut de `matches` : [{path: {pathPrefix: "/"}}]

Ce module l'implémente, et **s'arrête là**. Il ne désigne pas un vainqueur
quand plusieurs routes correspondent : la règle de précédence d'agentgateway
n'est écrite nulle part dans `amont/`, et deviner un ordre serait la pire
chose à faire dans un outil qui prétend vérifier une configuration.

Ce qu'il fait à la place est plus utile : il liste **toutes** les routes
candidates. Une configuration où deux routes attrapent la même requête est
une configuration dont l'auteur croit qu'une seule le fait.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

from jobportal.config import Config, Route


@dataclass(frozen=True)
class Requete:
    """Ce qu'il faut d'une requête HTTP pour décider d'une route."""

    chemin: str = "/"
    methode: str = "GET"
    entetes: dict[str, str] | None = None
    hote: str = ""

    def parametres(self) -> dict[str, list[str]]:
        return parse_qs(urlsplit(self.chemin).query)

    def chemin_seul(self) -> str:
        return urlsplit(self.chemin).path or "/"

    def entete(self, nom: str) -> str | None:
        """Les en-têtes HTTP sont insensibles à la casse (RFC 9110)."""
        for cle, valeur in (self.entetes or {}).items():
            if cle.lower() == nom.lower():
                return valeur
        # `:method` et `:authority` sont des pseudo-en-tetes : HeaderMatch les
        # accepte, et le schema le dit — « HTTP header or pseudo-header name
        # (such as `:method`) ».
        if nom == ":method":
            return self.methode
        if nom in (":authority", ":host"):
            return self.hote or None
        if nom == ":path":
            return self.chemin
        return None

    def __str__(self) -> str:
        entetes = " ".join(f"{c}={v}" for c, v in (self.entetes or {}).items())
        return f"{self.methode} {self.chemin}" + (f"  [{entetes}]" if entetes else "")


def chemin_correspond(regle: Any, chemin: str) -> bool:
    """PathMatch : exact | pathPrefix | regex.

    « pathPrefix » est un préfixe de SEGMENT dans la Gateway API — /v1 ne
    doit pas attraper /v10. Le schéma ne le précise pas ; on applique la
    convention, et `test_routage.py` fixe ce choix pour qu'il se conteste.
    """
    if not isinstance(regle, dict):
        return False
    # >>> depart: implanter les trois formes — exact, pathPrefix (par SEGMENT), regex
    #     return False
    if "exact" in regle:
        return chemin == regle["exact"]
    if "pathPrefix" in regle:
        prefixe = regle["pathPrefix"].rstrip("/") or "/"
        if prefixe == "/":
            return True
        return chemin == prefixe or chemin.startswith(prefixe + "/")
    if "regex" in regle:
        return re.search(regle["regex"], chemin) is not None
    return False
    # <<<


def valeur_correspond(regle: Any, valeur: str | None) -> bool:
    """HeaderValueMatch / QueryValueMatch : exact | regex."""
    if valeur is None or not isinstance(regle, dict):
        return False
    if "exact" in regle:
        return valeur == regle["exact"]
    if "regex" in regle:
        return re.search(regle["regex"], valeur) is not None
    return False


def correspondance_correspond(regle: dict[str, Any],
                              requete: Requete) -> tuple[bool, list[str]]:
    """Un RouteMatch : tous ses champs doivent passer.

    Rend (verdict, raisons de l'échec) — les raisons servent au chapitre 1,
    où il s'agit justement de comprendre pourquoi une route ne prend pas.
    """
    echecs = []
    # >>> depart: exiger que TOUS les champs poses passent — chemin, methode, en-tetes, parametres
    #     return True, []
    chemin = regle.get("path")
    if chemin is not None and not chemin_correspond(chemin, requete.chemin_seul()):
        echecs.append(f"chemin {requete.chemin_seul()!r} ≠ {chemin}")
    methode = regle.get("method")
    if methode is not None:
        attendue = methode.get("method") if isinstance(methode, dict) else methode
        if str(attendue).upper() != requete.methode.upper():
            echecs.append(f"methode {requete.methode} ≠ {attendue}")
    for entete in regle.get("headers") or []:
        if not isinstance(entete, dict):
            continue
        nom = entete.get("name", "")
        if not valeur_correspond(entete.get("value"), requete.entete(nom)):
            echecs.append(f"en-tete {nom} absent ou different")
    parametres = requete.parametres()
    for parametre in regle.get("query") or []:
        if not isinstance(parametre, dict):
            continue
        nom = parametre.get("name", "")
        valeurs = parametres.get(nom) or [None]
        if not any(valeur_correspond(parametre.get("value"), v) for v in valeurs):
            echecs.append(f"parametre {nom} absent ou different")
    return not echecs, echecs
    # <<<


def route_correspond(route: Route, requete: Requete) -> tuple[bool, list[str]]:
    """Une route : un seul de ses `matches` suffit."""
    raisons = []
    # >>> depart: un seul `matches` qui passe suffit — c'est un OU
    #     return False, ["a completer"]
    for regle in route.correspondances:
        ok, echecs = correspondance_correspond(regle, requete)
        if ok:
            return True, []
        raisons.extend(echecs)
    return False, raisons
    # <<<


@dataclass
class Candidate:
    route: Route
    attrape_par_defaut: bool


def candidates(config: Config, requete: Requete) -> list[Candidate]:
    """Toutes les routes qui peuvent attraper cette requête.

    `attrape_par_defaut` dit que la route n'écrit aucun `matches` : elle
    attrape tout, et rien dans le fichier ne le montre.
    """
    trouvees = []
    for route in config.routes():
        if route.noms_d_hote and requete.hote:
            if not any(_hote_correspond(h, requete.hote)
                       for h in route.noms_d_hote):
                continue
        ok, _ = route_correspond(route, requete)
        if ok:
            trouvees.append(Candidate(route, not route.correspondances_ecrites))
    return trouvees


def _hote_correspond(motif: str, hote: str) -> bool:
    """`hostnames` accepte un joker en tete — « Can be a wildcard »."""
    if motif.startswith("*."):
        return hote.endswith(motif[1:])
    return motif == hote


def routes_fourre_tout(config: Config) -> list[Route]:
    """Les routes qui attrapent tout parce qu'elles ne disent rien.

    Le défaut du schéma est `[{path: {pathPrefix: "/"}}]`. Une seule de ces
    routes rend toutes celles qui la suivent ambiguës.
    """
    return [r for r in config.routes() if not r.correspondances_ecrites]


def chevauchements(config: Config,
                   requetes: list[Requete]) -> list[tuple[Requete, list[Route]]]:
    """Les requêtes que plus d'une route peut attraper."""
    sorties = []
    for requete in requetes:
        trouvees = [c.route for c in candidates(config, requete)]
        if len(trouvees) > 1:
            sorties.append((requete, trouvees))
    return sorties
