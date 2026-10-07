"""Chapitre 2 — Installer un serveur : la portee decide de tout.

    uv run python chapitres/chapitre_2_installer.py

`claude mcp add` ecrit dans trois endroits differents selon la portee, et
c'est le choix qui a le plus de consequences — y compris sur ce qui finit
dans votre depot.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console          # noqa: E402

RACINE = Path(__file__).resolve().parent.parent

PORTEES = [
    ("local (defaut)", "~/.claude.json, sous le chemin du projet",
     "non", "vos serveurs a vous, sur ce projet"),
    ("project", ".mcp.json a la racine du projet",
     "OUI", "l'outillage commun de l'equipe"),
    ("user", "~/.claude.json, au niveau superieur",
     "non", "vos serveurs, sur TOUS vos projets"),
]

VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def etendre(valeur: str, environnement: dict) -> tuple[str, list[str]]:
    """Reproduit l'expansion `${VAR}` et `${VAR:-defaut}` de Claude Code.

    Le point qui compte : une variable absente SANS defaut n'est pas une
    erreur. Claude Code avertit dans `claude mcp list`, puis laisse le texte
    `${VAR}` tel quel. Un en-tete d'autorisation devient donc littéralement
    « Bearer ${GITHUB_PAT} », le serveur repond 401, et l'on cherche du cote
    du reseau pendant une heure.
    """
    absentes = []

    def remplacer(m):
        nom, defaut = m.group(1), m.group(2)
        if nom in environnement:
            return environnement[nom]
        if defaut is not None:
            return defaut
        absentes.append(nom)
        return m.group(0)

    return VARIABLE.sub(remplacer, valeur), absentes


def main() -> None:
    console.utf8()

    print("1. LES TROIS PORTEES\n")
    print(f"   {'portee':<16}{'ecrit dans':<44}{'versionne':<11}pour")
    for portee, fichier, versionne, usage in PORTEES:
        print(f"   {portee:<16}{fichier:<44}{versionne:<11}{usage}")
    print("\n   Une seule est partagee : « project ». C'est celle qu'il faut")
    print("   pour l'outillage d'equipe — et c'est exactement pour cela qu'un")
    print("   secret ne doit JAMAIS y etre ecrit en clair. Le chapitre 4 y")
    print("   revient ; le verificateur du projet le refuse.")

    print("\n2. LE .mcp.json DE CE PROJET\n")
    config = json.loads((RACINE / ".mcp.json").read_text(encoding="utf-8"))
    for nom, serveur in config["mcpServers"].items():
        transport = serveur.get("type", "?")
        cible = serveur.get("url") or f"{serveur.get('command')} " \
                                      f"{' '.join(serveur.get('args', []))}"
        print(f"   {nom:<14}{transport:<8}{cible}")

    print("\n3. L'EXPANSION DES VARIABLES\n")
    entete = config["mcpServers"]["github"]["headers"]["Authorization"]
    print(f"   ecrit dans le fichier : {entete}")

    sans, absentes = etendre(entete, {})
    print(f"   sans GITHUB_PAT       : {sans}")
    print(f"     variable(s) absente(s) : {absentes}")
    avec, _ = etendre(entete, {"GITHUB_PAT": "ghp_UNEVALEURDEXEMPLE"})
    print(f"   avec GITHUB_PAT       : {avec}")

    print("\n   Une variable absente n'est pas une erreur : le texte reste")
    print("   tel quel. L'en-tete envoye devient donc « Bearer ${GITHUB_PAT} »,")
    print("   le serveur repond 401, et rien dans le message ne pointe vers")
    print("   la vraie cause. `claude mcp list` l'avertit — encore faut-il")
    print("   le lancer avant de chercher du cote du reseau.")

    dsn = config["mcpServers"]["jobportal"]["env"]["JOBPORTAL_DSN"]
    valeur, absentes = etendre(dsn, dict(os.environ))
    print(f"\n   Avec un defaut : {dsn}")
    print(f"   → {valeur}   (absente(s) : {absentes or 'aucune'})")
    print("\n   La forme ${VAR:-defaut} est la bonne pour tout ce qui n'est pas")
    print("   un secret : le projet demarre sans configuration prealable, et")
    print("   celui qui veut pointer ailleurs pose la variable.")

    print("\n4. VERIFIER, PLUTOT QUE CROIRE\n")
    print("   claude mcp list          l'etat reel des connexions")
    print("   claude mcp get jobportal le detail d'un serveur, variables etendues")
    print("   /mcp                     dans la session : outils, ressources, invites")
    print("\n   Un serveur declare n'est pas un serveur connecte. La commande")
    print("   `claude mcp list` est le seul endroit ou la difference se voit.")


if __name__ == "__main__":
    main()
