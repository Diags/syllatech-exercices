"""Une configuration agentgateway, lue et normalisée.

Le fichier passé à `--file` est du YAML à **quatorze** sections de premier
niveau. Deux d'entre elles décrivent le même proxy à deux niveaux de
détail :

    binds:      « the low-level API for configuring the proxy »
    llm: / mcp: des raccourcis — un port, des modèles ou des cibles

Les trois quarts des exemples du dépôt utilisent `binds`, et c'est la
grammaire que le cours enseigne : un bind ouvre un port, un listener y
accepte le trafic, une route choisit la destination, un backend est la
destination. Ce module rend cette structure lisible et comptable, sans rien
inventer : tout ce qu'il affirme est vérifiable dans `amont/config.schema.json`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# Les quatorze sections de premier niveau de LocalConfig, dans l'ordre du
# schema publie. Une section absente n'est pas une erreur : aucune n'est
# obligatoire — un fichier vide est une configuration valide.
SECTIONS = (
    "config", "binds", "frontendPolicies", "policies", "workloads",
    "services", "backends", "routeGroups", "gateways", "routes",
    "tcpRoutes", "llm", "mcp", "ui",
)

# LocalRouteBackend : les dix branches du `oneOf`. Un backend en declare
# exactement une — « unevaluatedProperties: false » refuse les melanges.
TYPES_DE_BACKEND = (
    "service", "backend", "host", "internal", "dynamic",
    "mcp", "ai", "aws", "routeGroup", "invalid",
)

# LocalMcpTarget : les quatre facons d'atteindre un serveur MCP.
TYPES_DE_CIBLE_MCP = ("stdio", "sse", "mcp", "openapi")

# AIProvider : les huit fournisseurs. Noter la casse de `openAI`.
FOURNISSEURS = ("openAI", "gemini", "vertex", "anthropic", "bedrock",
                "azure", "copilot", "custom")

# PathMatch : les trois formes, plus la sentinelle « invalid ».
FORMES_DE_CHEMIN = ("exact", "pathPrefix", "regex")

# LocalRoute.matches — « default: [{"path": {"pathPrefix": "/"}}] ».
# Une route sans `matches` attrape donc TOUT. C'est le defaut le plus
# lourd de consequences de tout le schema, et il ne s'ecrit nulle part.
CORRESPONDANCE_PAR_DEFAUT: list[dict[str, Any]] = [
    {"path": {"pathPrefix": "/"}}]


@dataclass
class Route:
    """Une route, avec le chemin de sa position dans le fichier."""

    brut: dict[str, Any]
    bind: int
    listener: int
    rang: int

    @property
    def nom(self) -> str:
        return self.brut.get("name") or f"route[{self.rang}]"

    @property
    def correspondances(self) -> list[dict[str, Any]]:
        """`matches`, defaut compris.

        Le defaut n'est pas dans le fichier : il est dans le schema. Une
        route qui ne dit rien attrape tout ce qui commence par « / ».
        """
        # TODO : rendre `matches` s'il est ecrit, sinon le defaut du schema
        return self.brut.get("matches") or []

    @property
    def correspondances_ecrites(self) -> bool:
        return isinstance(self.brut.get("matches"), list) \
            and bool(self.brut["matches"])

    @property
    def politiques(self) -> dict[str, Any]:
        p = self.brut.get("policies")
        return p if isinstance(p, dict) else {}

    @property
    def backends(self) -> list[dict[str, Any]]:
        b = self.brut.get("backends")
        return [x for x in b if isinstance(x, dict)] if isinstance(b, list) else []

    @property
    def noms_d_hote(self) -> list[str]:
        h = self.brut.get("hostnames")
        return h if isinstance(h, list) else []

    def position(self) -> str:
        return f"binds[{self.bind}].listeners[{self.listener}].routes[{self.rang}]"


@dataclass
class Config:
    """Le fichier, et ce qu'on peut en dire sans le lancer."""

    brut: dict[str, Any]
    fichier: str = "(memoire)"

    @property
    def sections(self) -> list[str]:
        return [s for s in SECTIONS if s in self.brut]

    @property
    def sections_inconnues(self) -> list[str]:
        return sorted(k for k in self.brut if k not in SECTIONS)

    def ports(self) -> list[int]:
        ports = [b.get("port") for b in self.brut.get("binds") or []
                 if isinstance(b, dict) and isinstance(b.get("port"), int)]
        for raccourci in ("llm", "mcp"):
            bloc = self.brut.get(raccourci)
            if isinstance(bloc, dict) and isinstance(bloc.get("port"), int):
                ports.append(bloc["port"])
        # `gateways` est une TABLE nommee, pas une liste : la cle est le nom
        # auquel `llm.gateways` et `routes[].gateways` se rattachent.
        passerelles = self.brut.get("gateways")
        if isinstance(passerelles, dict):
            for passerelle in passerelles.values():
                if isinstance(passerelle, dict) and isinstance(passerelle.get("port"), int):
                    ports.append(passerelle["port"])
                for ecouteur in (passerelle or {}).get("listeners") or []:
                    if isinstance(ecouteur, dict) and isinstance(ecouteur.get("port"), int):
                        ports.append(ecouteur["port"])
        return sorted(set(ports))

    def routes(self) -> list[Route]:
        """Toutes les routes de tous les listeners, dans l'ordre du fichier.

        L'ordre compte : le chapitre 1 mesure ce qu'il decide.
        """
        sorties = []
        for i, bind in enumerate(self.brut.get("binds") or []):
            if not isinstance(bind, dict):
                continue
            for j, listener in enumerate(bind.get("listeners") or []):
                if not isinstance(listener, dict):
                    continue
                for k, route in enumerate(listener.get("routes") or []):
                    if isinstance(route, dict):
                        sorties.append(Route(route, i, j, k))
        return sorties

    def cibles_mcp(self) -> list[tuple[str, str, dict[str, Any]]]:
        """Les cibles MCP de tous les backends `mcp`, avec leur type.

        Rend (nom de la cible, type de cible, corps). Le type est la branche
        du `oneOf` de LocalMcpTarget : stdio, sse, mcp ou openapi.
        """
        sorties = []
        for route in self.routes():
            for backend in route.backends:
                bloc = backend.get("mcp")
                if not isinstance(bloc, dict):
                    continue
                for cible in bloc.get("targets") or []:
                    if not isinstance(cible, dict):
                        continue
                    type_ = next((t for t in TYPES_DE_CIBLE_MCP if t in cible),
                                 "(inconnu)")
                    sorties.append((cible.get("name") or "(sans nom)", type_,
                                    cible))
        # Le raccourci `mcp:` de premier niveau porte les memes cibles.
        raccourci = self.brut.get("mcp")
        if isinstance(raccourci, dict):
            for cible in raccourci.get("targets") or []:
                if not isinstance(cible, dict):
                    continue
                type_ = next((t for t in TYPES_DE_CIBLE_MCP if t in cible),
                             "(inconnu)")
                sorties.append((cible.get("name") or "(sans nom)", type_, cible))
        return sorties

    def type_de_backend(self, backend: dict[str, Any]) -> str:
        return next((t for t in TYPES_DE_BACKEND if t in backend), "(inconnu)")

    def politiques_posees(self) -> dict[str, int]:
        """Combien de routes posent chaque politique."""
        compte: dict[str, int] = {}
        for route in self.routes():
            for nom in route.politiques:
                compte[nom] = compte.get(nom, 0) + 1
        return dict(sorted(compte.items()))


def charger(chemin: Path | str) -> Config:
    chemin = Path(chemin)
    brut = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    if brut is None:
        brut = {}
    if not isinstance(brut, dict):
        raise ValueError(f"{chemin.name} : une configuration doit etre une table")
    return Config(brut, chemin.name)


def depuis_texte(texte: str, nom: str = "(memoire)") -> Config:
    brut = yaml.safe_load(texte) or {}
    return Config(brut, nom)


def charger_dossier(dossier: Path | str) -> list[Config]:
    return [charger(p) for p in sorted(Path(dossier).glob("*.yaml"))]
