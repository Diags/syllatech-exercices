"""Le proxy — le VRAI `litellm.Router`, monté depuis un vrai `config.yaml`.

Rien n'est simulé ici : c'est la bibliothèque `litellm` qui lit `model_list`,
traduit vers le format de chaque fournisseur, applique les `fallbacks`, les
`num_retries` et calcule le coût depuis sa table de prix.

CE QUI EST SUBSTITUÉ, ET RIEN D'AUTRE

Chaque déploiement porte un `mock_response`. C'est un champ **de litellm**,
pas un artifice de ce projet : le proxy fait tout son travail — routage,
bascule, comptage de jetons, calcul du coût — et rend la réponse annoncée au
lieu d'appeler le réseau. On peut donc tout mesurer sans clé et sans dépense.

    mock_response: "réponse"                 → une réponse
    mock_response: "litellm.RateLimitError"  → une vraie RateLimitError

Remplacer ces deux lignes par de vraies `api_key` suffit pour brancher le
projet sur de vrais fournisseurs : rien d'autre ne change.

⚠️ `import litellm` prend une trentaine de secondes la première fois. Ce n'est
pas ce projet : c'est le paquet, qui charge sa table de prix et ses cent
intégrations. En production, c'est du démarrage de conteneur, payé une fois —
mais c'est à savoir avant de mettre une sonde de vivacité à 10 secondes.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

RACINE = Path(__file__).resolve().parent.parent


@dataclass
class Appel:
    """Ce qu'on sait d'un appel une fois qu'il est revenu."""

    alias: str                 # ce que l'application a demandé
    modele_reel: str           # ce qui a répondu — pas forcément le même
    contenu: str
    cout: float
    jetons: int
    latence_ms: float
    bascule: bool              # un fallback s'est-il produit ?


class Proxy:
    """Un `litellm.Router` et le peu qu'il faut autour."""

    def __init__(self, config: dict) -> None:
        from litellm import Router          # import tardif : il coûte 30 s
        import litellm

        litellm.suppress_debug_info = True
        self.config = config
        reglages = config.get("litellm_settings") or {}
        self.alias = [m["model_name"] for m in config["model_list"]]
        self.routeur = Router(
            model_list=_resoudre_environnement(config["model_list"]),
            fallbacks=reglages.get("fallbacks") or [],
            num_retries=reglages.get("num_retries", 0),
        )

    @classmethod
    def depuis(cls, chemin: str | Path) -> "Proxy":
        return cls(charger(chemin))

    async def appeler(self, alias: str, question: str) -> Appel:
        import time

        debut = time.perf_counter()
        reponse = await self.routeur.acompletion(
            model=alias, messages=[{"role": "user", "content": question}])
        latence = (time.perf_counter() - debut) * 1000

        caches = getattr(reponse, "_hidden_params", {}) or {}
        reel = reponse.model or ""
        return Appel(
            alias=alias,
            modele_reel=reel,
            contenu=reponse.choices[0].message.content or "",
            cout=float(caches.get("response_cost") or 0.0),
            jetons=int(getattr(reponse.usage, "total_tokens", 0) or 0),
            latence_ms=latence,
            # Le modèle qui a répondu n'est pas celui du premier déploiement
            # de l'alias : c'est la signature d'une bascule. L'application,
            # elle, ne voit qu'une réponse réussie — c'est le but, et c'est
            # aussi pourquoi il faut la journaliser.
            bascule=not _correspond(reel, self._vrai_modele(alias)),
        )

    def _vrai_modele(self, alias: str) -> str:
        for entree in self.config["model_list"]:
            if entree["model_name"] == alias:
                return entree["litellm_params"]["model"]
        return ""

    def deploiements(self, alias: str) -> list[dict]:
        return [m for m in self.config["model_list"]
                if m["model_name"] == alias]


def charger(chemin: str | Path) -> dict:
    return yaml.safe_load(Path(chemin).read_text(encoding="utf-8"))


def _resoudre_environnement(modeles: list[dict]) -> list[dict]:
    """`api_key: os.environ/ANTHROPIC_API_KEY` → la variable, ou un marqueur.

    C'est ce que fait le proxy au démarrage. Le marqueur évite que le projet
    exige des clés : avec `mock_response`, aucune n'est envoyée nulle part.
    """
    resolus = []
    for entree in modeles:
        params = dict(entree["litellm_params"])
        for champ, valeur in list(params.items()):
            if isinstance(valeur, str) and valeur.startswith("os.environ/"):
                nom = valeur.removeprefix("os.environ/")
                params[champ] = os.environ.get(nom, f"absente:{nom}")
        resolus.append({**entree, "litellm_params": params})
    return resolus


def _correspond(modele_rendu: str, declare: str) -> bool:
    """« gpt-4o » correspond-il à « openai/gpt-4o » ?

    litellm rend le nom du modèle sans son préfixe de fournisseur, et parfois
    avec une date (« claude-sonnet-4-5-20250929 »). Comparer les chaînes
    brutes ferait voir une bascule à chaque appel.
    """
    nu = declare.split("/")[-1]
    rendu = modele_rendu.split("/")[-1]
    return rendu == nu or rendu.startswith(nu) or nu.startswith(rendu)


ENVIRONNEMENT = re.compile(r"^os\.environ/[A-Z0-9_]+$")
