"""Chapitre 6 — Trois couches, et les limites.

    uv run python chapitres/chapitre_6_limites.py

Les cinq chapitres précédents ont pris les couches une par une. Celui-ci les
prend ensemble, parce que c'est ensemble qu'elles se contredisent :

  · couper une couche ne coupe pas les protections que les autres portent ;
  · une configuration se relit au mauvais niveau — on lit ce qui est écrit,
    jamais ce qui s'applique ;
  · et la même erreur ne se voit pas au même endroit selon le fichier où on
    l'a écrite.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import RACINE, config, titre, utf8       # noqa: E402
from outils.resolveur import (CLES_PRIVILEGIEES, LIMITES,   # noqa: E402
                              appliquee)
from outils.verifier import verifier                        # noqa: E402


def main() -> None:
    utf8()

    titre(1, "LES TROIS COUCHES")
    for couche, porte, coupee_par in (
            ("fichiers", "allowRead/Write, denyRead/Write, chemins proteges, "
                         "credentials.files en deny", "filesystem.disabled"),
            ("reseau", "allowedDomains, deniedDomains, strictAllowlist",
             "rien — elle reste quand les fichiers tombent"),
            ("proxy / secrets", "credentials.envVars, masques de fichiers",
             "rien — independante de la couche fichiers")):
        print(f"   {couche.upper()}")
        print(f"      porte      {porte}")
        print(f"      coupee par {coupee_par}")

    titre(2, "CE QUE filesystem.disabled EMPORTE, ET CE QU'IL LAISSE")
    print("   « Setting filesystem.disabled lifts the protections the")
    print("     filesystem layer itself enforces. Protections that other")
    print("     layers enforce keep applying. »\n")
    for protection, etat in (
            ("filesystem.denyRead", "tombe"),
            ("credentials.files en mode deny", "tombe"),
            ("les chemins proteges", "tombent"),
            ("credentials.envVars deny et mask", "TIENNENT"),
            ("credentials.files en mode mask", "TIENNENT"),
            ("allowedDomains / deniedDomains", "TIENNENT")):
        print(f"   {protection:<34}{etat}")
    print()
    print("   La ligne a retenir : un secret protege par « deny » de fichier")
    print("   n'est plus protege du tout, alors qu'un secret protege par")
    print("   « mask » l'est encore. Couper une couche ne degrade pas la")
    print("   securite uniformement — elle enleve certaines protections")
    print("   entierement et n'en touche aucune autre.")

    titre(3, "LA MEME CONFIGURATION, RELUE AUX DEUX ENDROITS")
    print("   configs/a-corriger.json : huit cles qui n'ont pas l'effet")
    print("   qu'on croit, et pas une seule faute de syntaxe.\n")
    colonnes = {}
    for portee in ("projet", "utilisateur"):
        fautive = config("a-corriger", portee)
        soucis = verifier(fautive)
        _, ignorees = appliquee(fautive)
        colonnes[portee] = (soucis, ignorees)
        erreurs = [s for s in soucis if s.gravite == "erreur"]
        print(f"   portee « {portee} » : {len(erreurs)} erreurs, "
              f"{len(soucis) - len(erreurs)} avertissements, "
              f"{len(ignorees)} cles ignorees")

    ou: dict[str, dict[str, str]] = {}
    for portee, (soucis, _) in colonnes.items():
        for s in soucis:
            ou.setdefault(s.ou, {})[portee] = (
                "ERREUR" if s.gravite == "erreur" else "attention")
    print(f"\n   {'defaut':<40}{'projet':<12}utilisateur")
    for cle in sorted(ou):
        print(f"   {cle[:39]:<40}"
              f"{ou[cle].get('projet', '—'):<12}"
              f"{ou[cle].get('utilisateur', '—')}")

    communs = [c for c, p in ou.items() if len(p) == 2]
    bascules = [c for c, p in ou.items() if len(p) == 1]
    print(f"\n   {len(communs)} defauts ne dependent pas de l'endroit du "
          f"fichier ; {len(bascules)} en dependent,")
    print("   et chacun de ceux-la n'apparait que dans UNE des deux colonnes.")
    print()
    print("   Une ligne merite un arret : « filesystem.disabled » est dans les")
    print("   deux colonnes et ne dit pas la meme chose. En portee projet,")
    print("   c'est une ERREUR — la cle est ignoree. En portee utilisateur,")
    print("   c'est un AVERTISSEMENT — la cle marche, et c'est bien le")
    print("   probleme. Meme cle, meme valeur, deux reproches opposes.")
    print()
    print("   Consequence pratique : corriger la portee REVELE des erreurs")
    print("   qui n'existaient pas avant. Les masques ignores redeviennent")
    print("   des masques, donc leurs trois conditions redeviennent")
    print("   exigibles. On verifie donc deux fois — avant et apres.")

    titre(4, "LES CINQ CLES QUI NE S'APPLIQUENT PAS PARTOUT")
    for cle, pourquoi in CLES_PRIVILEGIEES.items():
        print(f"   {cle}")
        print(f"      {pourquoi}")
    print()
    print("   Elles ont toutes la meme forme : elles ELARGISSENT ce qu'une")
    print("   commande peut faire. Un fichier qu'un « git pull » modifie ne")
    print("   peut donc pas les porter. La regle est coherente — elle n'est")
    print("   simplement visible nulle part dans le JSON.")

    titre(5, "CE QUE CE PROJET NE PROUVE PAS")
    for ligne_ in LIMITES.strip().splitlines():
        print(f"   {ligne_}")
    print()
    print("   Deux limites qui comptent plus que les autres :")
    print()
    print("   · Aucune commande n'a ete executee sous un vrai bac a sable.")
    print("     Tout ce qui precede est le comportement DOCUMENTE, rendu")
    print("     interrogeable. Sur une machine macOS, Linux ou WSL2, la")
    print("     verification finale est « /sandbox », onglet Config.")
    print("   · Un modele qui se trompe se trompe en silence, exactement")
    print("     comme les defauts qu'il traque. C'est pourquoi chaque regle")
    print("     de outils/resolveur.py cite la phrase de la documentation")
    print("     dont elle sort : on peut la contredire.")

    titre(6, "LA SEULE CONCLUSION QUI SERVE")
    print("   Une configuration de bac a sable ne se relit pas — elle")
    print("   s'interroge. « Est-ce que ce chemin est ecrivable ? » a une")
    print("   reponse ; « est-ce que cette configuration est bonne ? » n'en a")
    print("   pas.")
    print()
    print(f"   {'':2}uv run python outils/verifier.py configs/a-corriger.json")
    print(f"   {'':2}uv run python outils/resolveur.py configs/depot.json "
          f"--ecrire .mcp.json")
    print()
    print(f"   Les 6 chapitres et les tests sont dans {RACINE.name}/.\n")


if __name__ == "__main__":
    main()
