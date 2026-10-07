"""Chapitre 4 — MCP : la description d'un outil est une surface d'attaque.

    uv run python chapitres/chapitre_4_mcp.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.attaques import (OUTIL_AJOUTE, OUTIL_EMPOISONNE,  # noqa: E402
                                OUTIL_SAIN)
from jobportal.defenses import (descriptions_suspectes,    # noqa: E402
                                filtrer_outils)

AUTORISES = {"chercher_offres", "lire_offre"}


def contexte(outils: list[dict]) -> str:
    return "\n".join(f"{o['name']}: {o['description']}" for o in outils)


def main() -> None:
    console.utf8()

    print("1. L'OUTIL EMPOISONNE — l'attaque n'est PAS dans les donnees\n")
    print(f"   nom         {OUTIL_EMPOISONNE['name']}")
    for ligne in OUTIL_EMPOISONNE["description"].split(". "):
        print(f"   description {ligne.strip()}")
    print("\n   Ce texte entre au contexte A LA CONNEXION, avant toute question")
    print("   de l'utilisateur. Le serveur n'a meme pas besoin qu'on appelle")
    print("   son outil : il lui suffit que sa description soit chargee.")

    print("\n2. LE FILTRE — ni le nom ni la DESCRIPTION n'entrent\n")
    v1_5 = [OUTIL_EMPOISONNE, OUTIL_AJOUTE]
    print(f"   sans filtre : {len(contexte(v1_5))} signes dans le contexte")
    filtres = filtrer_outils(v1_5, AUTORISES)
    print(f"   avec filtre : {len(contexte(filtres))} signes")
    print(f"   outils retenus : {[o['name'] for o in filtres]}")
    print("\n   ⚠️ « chercher_offres » EST dans la liste blanche : son nom passe.")
    print("   Sa description empoisonnee passe donc avec lui. Le filtre par")
    print("   NOM ne protege pas d'un outil legitime dont la description a")
    print("   change — c'est le « rug pull », et c'est le point du chapitre.")

    print("\n3. CE QUE LE FILTRE ARRETE VRAIMENT\n")
    print(f"   « {OUTIL_AJOUTE['name']} » ajoute en 1.5.0 : "
          f"{'passe' if any(o['name'] == OUTIL_AJOUTE['name'] for o in filtres) else 'BLOQUE'}")
    print("\n   Un outil que personne n'a demande n'entre pas au contexte. Ni")
    print("   son nom, ni sa description. C'est ce que le filtre garantit, et")
    print("   c'est deja beaucoup — mais ce n'est pas tout.")

    print("\n4. LA REVUE DE VERSION — ce qui manque au filtre\n")
    for nom, version in ((OUTIL_SAIN, "1.4.2"), (OUTIL_EMPOISONNE, "1.5.0")):
        suspects = descriptions_suspectes([nom])
        etat = f"SUSPECT : {suspects}" if suspects else "rien a signaler"
        print(f"   {version}  {etat}")
    print("\n   Un diff des DESCRIPTIONS entre deux versions, comme un diff de")
    print("   code. C'est ce qui attrape le rug pull que le filtre laisse")
    print("   passer. Le controle par motifs ne voit que les formes connues :")
    print("   il alerte, il ne protege pas.")

    print("\n5. EPINGLER LA VERSION\n")
    print('   "args": ["-y", "mcp-offres@1.4.2"]   ← epingle')
    print('   "args": ["-y", "mcp-offres"]         ← ce qui sort aujourd hui')
    print("\n   Sans epinglage, la description empoisonnee arrive au prochain")
    print("   demarrage, sans commit, sans revue, sans trace. La chaine")
    print("   d'approvisionnement d'un agent se traite comme celle du code :")
    print("   version epinglee, montee deliberee, diff relu.")


if __name__ == "__main__":
    main()
