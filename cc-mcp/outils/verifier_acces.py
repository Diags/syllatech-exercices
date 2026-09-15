#!/usr/bin/env python3
"""Le vérificateur d'accès MCP — ce que Claude Code ne vérifie pas pour vous.

    python outils/verifier_acces.py [dossier]

POURQUOI CET OUTIL EXISTE

La documentation des permissions dit ceci :

    « A deny or ask rule whose tool name matches no known tool produces a
      startup warning to catch typos. Tool names containing `_` or `*` are
      exempt from the check. »

Or **tout** nom d'outil MCP contient `_` : il commence par `mcp__`. Les règles
MCP sont donc **exemptes du contrôle de faute de frappe**. Écrivez
`mcp__jobportal__supprimer_ofre` au lieu de `supprimer_offre`, et :

  · aucun avertissement au démarrage,
  · la règle ne correspond à rien,
  · l'outil de suppression reste **autorisé**.

C'est la même famille de défaut que la variable de hook qui n'existe pas :
il ne casse rien, il ne dit rien, il réussit en apparence. On ne le découvre
que le jour où l'agent supprime une offre — et ce jour-là, c'est trop tard.

Cet outil interroge le serveur pour connaître ses **vrais** noms d'outils,
puis les compare aux règles. Quinze lignes de Python, et un angle mort en
moins.

CE QU'IL CONTRÔLE

  1. règle deny/ask qui ne correspond à aucun outil réel (la faute de frappe)
  2. glob d'autorisation non ancré — `mcp__*` n'autorise RIEN
  3. outil d'écriture couvert par aucune règle deny
  4. secret écrit en clair dans un `.mcp.json` versionné
  5. règle allow rendue inutile par une règle deny plus large (précédence)
"""

from __future__ import annotations

import asyncio
import fnmatch
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

for _flux in (sys.stdout, sys.stderr):
    try:
        _flux.reconfigure(encoding="utf-8", errors="replace")
    except Exception:   # noqa: BLE001
        pass

# Les outils qui MODIFIENT. Un serveur MCP ne le dit pas ; c'est à vous de le
# savoir, et c'est la raison d'être d'une règle « deny ».
ECRITURE = {"supprimer_offre", "creer_offre", "modifier_offre"}

# Ce à quoi ressemble un secret écrit en clair. Volontairement large : un
# faux positif se lit en deux secondes, un secret versionné se paie longtemps.
SECRET = re.compile(r"(?:Bearer\s+|token|key|secret|password|pat)[\"'\s:=]*"
                    r"([A-Za-z0-9_\-]{16,})", re.IGNORECASE)


@dataclass
class Souci:
    gravite: str        # "erreur" ou "attention"
    ou: str
    message: str


def outils_reels() -> list[str]:
    """Demande au serveur ses noms d'outils. La seule source de vérité."""
    from jobportal.serveur import outils_exposes
    return [f"mcp__jobportal__{n}" for n in asyncio.run(outils_exposes())]


def regles(settings: dict) -> dict[str, list[str]]:
    p = settings.get("permissions", {})
    return {genre: [r for r in p.get(genre, []) if r.startswith("mcp__")]
            for genre in ("deny", "ask", "allow")}


def correspond(regle: str, outil: str) -> bool:
    """Un `*` est un glob, pas une expression régulière.

    La page MCP montre `mcp__serveur__.*` — c'est la forme des matchers de
    hooks, qui sont des regex. Les règles de permission, elles, utilisent des
    globs : `mcp__serveur__*`. Écrire `.*` dans une règle de permission ne
    correspond donc qu'à un outil littéralement nommé « .quelquechose ».
    """
    # >>> depart: faire correspondre la regle a l'outil par un GLOB (fnmatch), pas par une expression reguliere. Cinq tests parametres le verifient, dont celui qui exige que « mcp__jobportal__.* » ne corresponde PAS.
    #     return regle == outil
    return fnmatch.fnmatchcase(outil, regle)
    # <<<


def ancree(regle: str) -> bool:
    """Un glob d'autorisation doit nommer un serveur précis.

    « Allow rules accept tool-name globs only after a literal `mcp__<server>__`
    prefix. The server segment must be glob-free. » Une règle non ancrée comme
    `mcp__*` est ignorée avec un avertissement et **n'autorise rien**.
    """
    # >>> depart: rendre True seulement si la regle commence par « mcp__<serveur>__ » ou <serveur> ne contient aucun caractere de glob (* ? [ ]). Quatre tests parametres le verifient.
    #     return True
    m = re.match(r"^mcp__([^_*?\[\]]+(?:_[^_*?\[\]]+)*)__", regle)
    return bool(m)
    # <<<


def verifier(dossier: Path) -> list[Souci]:
    soucis: list[Souci] = []
    reels = outils_reels()

    mcp_json = dossier / ".mcp.json"
    settings_json = dossier / ".claude" / "settings.json"

    # --- 1. le fichier de serveurs -------------------------------------
    if mcp_json.exists():
        brut = mcp_json.read_text(encoding="utf-8")
        for m in SECRET.finditer(brut):
            if "${" in brut[max(0, m.start() - 40):m.end()]:
                continue
            soucis.append(Souci("erreur", ".mcp.json",
                                f"secret en clair « {m.group(1)[:8]}… » : ce fichier est "
                                "versionné (portée projet). Utilisez ${VARIABLE}."))
        config = json.loads(brut)
        for nom, serveur in config.get("mcpServers", {}).items():
            if "type" not in serveur and "url" in serveur:
                soucis.append(Souci("attention", f".mcp.json/{nom}",
                                    "« url » sans « type » : precisez http, sse ou ws"))
            if serveur.get("type") == "sse":
                soucis.append(Souci("attention", f".mcp.json/{nom}",
                                    "transport « sse » deprecie — utilisez « http »"))

    # --- 2. les règles de permission ------------------------------------
    if not settings_json.exists():
        soucis.append(Souci("erreur", "settings.json",
                            "absent : aucune regle, donc aucun garde-fou"))
        return soucis

    reglages = json.loads(settings_json.read_text(encoding="utf-8"))
    r = regles(reglages)

    # LE contrôle central.
    # >>> depart: signaler toute regle deny ou ask qui ne correspond a AUCUN outil reellement expose. C'est LE controle central : les noms MCP contiennent « _ », donc Claude Code est exempte du controle de faute de frappe et ne dit rien. Deux tests le verifient.
    #     pass
    for genre in ("deny", "ask"):
        for regle in r[genre]:
            if not any(correspond(regle, o) for o in reels):
                soucis.append(Souci("erreur", f"{genre} / {regle}",
                                    "ne correspond a AUCUN outil expose. Les noms "
                                    "MCP contiennent « _ » : Claude Code n'avertit "
                                    "donc pas. La regle ne protege rien."))
    # <<<

    for regle in r["allow"]:
        if not ancree(regle):
            soucis.append(Souci("erreur", f"allow / {regle}",
                                "glob non ancre : le segment serveur doit etre "
                                "litteral. Cette regle est ignoree et n'autorise rien."))
        elif not any(correspond(regle, o) for o in reels):
            soucis.append(Souci("attention", f"allow / {regle}",
                                "ne correspond a aucun outil expose (sans "
                                "avertissement au demarrage : allow n'est pas verifie)"))

    # --- 3. les outils d'écriture doivent être couverts ------------------
    for outil in reels:
        court = outil.rsplit("__", 1)[-1]
        if court not in ECRITURE:
            continue
        if not any(correspond(regle, outil) for regle in r["deny"] + r["ask"]):
            soucis.append(Souci("erreur", outil,
                                "outil d'ECRITURE couvert par aucune regle deny "
                                "ou ask : il s'executera apres une seule "
                                "approbation, puis sans rien demander."))

    # --- 4. la précédence : deny, puis ask, puis allow -------------------
    for autorise in r["allow"]:
        for refuse in r["deny"]:
            couverts = [o for o in reels if correspond(autorise, o)]
            if couverts and all(correspond(refuse, o) for o in couverts):
                soucis.append(Souci("attention", f"allow / {autorise}",
                                    f"entierement recouvert par deny « {refuse} ». "
                                    "Les regles s'evaluent deny, puis ask, puis "
                                    "allow : cet allow ne s'applique jamais."))
    return soucis


def main() -> int:
    dossier = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE
    reels = outils_reels()

    print(f"\n  Outils reellement exposes par le serveur ({len(reels)}) :")
    for o in reels:
        marque = "  (ECRITURE)" if o.rsplit("__", 1)[-1] in ECRITURE else ""
        print(f"     {o}{marque}")

    print(f"\n  Configuration verifiee : {dossier}\n")
    soucis = verifier(dossier)
    for s in soucis:
        marque = "ERREUR    " if s.gravite == "erreur" else "attention "
        print(f"  {marque} {s.ou}")
        print(f"             {s.message}")
    if not soucis:
        print("  Aucun probleme detecte.")

    erreurs = [s for s in soucis if s.gravite == "erreur"]
    print(f"\n  {len(erreurs)} erreur(s), {len(soucis) - len(erreurs)} avertissement(s)")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
