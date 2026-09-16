"""Chapitre 6 — Distribuer et maintenir : le nom d'outil est un contrat.

    uv run python chapitres/chapitre_6_distribution.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

from jobportal import console                     # noqa: E402
from jobportal.serveur import outils_exposes      # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


async def main_async() -> None:
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))

    print("1. EMPAQUETER : une commande, partout\n")
    print(f"   nom        {projet['project']['name']}")
    print(f"   version    {projet['project']['version']}")
    print(f"   scripts    {projet['project']['scripts']}")
    config = json.loads((RACINE / ".mcp.json").read_text(encoding="utf-8"))
    jp = config["mcpServers"]["jobportal"]
    print(f"   .mcp.json  {jp['command']} {' '.join(jp['args'])}")
    print("\n   Le .mcp.json est versionne : un nouvel arrivant clone, et le")
    print("   serveur demarre. Rien a installer a la main, rien a expliquer")
    print("   dans un README que personne ne lit.")

    print("\n2. LA BORNE DE VERSION — le piege du chapitre 3, chiffre\n")
    bornes = [
        ('mcp[cli]>=1.2', "1.2 … 3.x", "peut resoudre vers 1.x : MCPServer n'existe pas"),
        ('mcp>=2.2', "2.2 … 4.x", "peut resoudre vers 3.x : rupture non testee"),
        ('mcp>=2.2,<3', "2.2 … 2.x", "la seule que le code du cours garantit"),
    ]
    print(f"   {'borne':<18}{'autorise':<14}consequence")
    for borne, plage, consequence in bornes:
        print(f"   {borne:<18}{plage:<14}{consequence}")
    print(f"\n   Ce projet declare : {projet['project']['dependencies']}")
    print("\n   Une borne qui autorise une version incompatible avec le code")
    print("   livre n'est pas une borne. Et le fichier de verrou (uv.lock) est")
    print("   livre lui aussi : un projet pedagogique doit tourner avec les")
    print("   versions exactes avec lesquelles il a ete verifie.")

    print("\n3. LE NOM D'OUTIL EST UN CONTRAT\n")
    noms = await outils_exposes()
    for nom in noms:
        print(f"   mcp__jobportal__{nom}")
    print("\n   Ces noms sont ecrits dans les regles de permission de chaque")
    print("   poste de l'equipe. Renommer « rechercher_offres » en")
    print("   « chercher_offres », c'est :")
    print("     · rendre caduques toutes les regles allow qui le nommaient,")
    print("     · SANS aucun avertissement (chapitre 4),")
    print("     · donc rendre l'outil demandeur d'approbation chez tout le monde.")
    print("\n   Un renommage est une RUPTURE : version majeure, et une ligne")
    print("   dans le message de commit. La regle de compatibilite d'une API")
    print("   publique s'applique mot pour mot.")

    print("\n4. CE QU'IL FAUT RELIRE A CHAQUE MONTEE DE VERSION\n")
    print("   · les DESCRIPTIONS d'outils : elles pilotent le declenchement,")
    print("     et une reformulation change le comportement de l'agent sans")
    print("     changer une ligne de code executee ;")
    print("   · les NOMS et parametres : contrat, donc versionnage semantique ;")
    print("   · les PERMISSIONS : un outil ajoute n'est couvert par aucune")
    print("     regle existante. Relancez le verificateur — c'est exactement")
    print("     ce qu'il signale.")

    print("\n5. LA COMMANDE QUI FERME LA BOUCLE\n")
    print("   uv run python outils/verifier_acces.py")
    print("\n   A brancher sur la CI : un outil ajoute sans regle, une regle")
    print("   devenue caduque, un secret glisse dans .mcp.json — les trois")
    print("   echouent la construction au lieu d'attendre la production.")


def main() -> None:
    console.utf8()
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
