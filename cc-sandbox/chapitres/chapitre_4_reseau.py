"""Chapitre 4 — Isoler le réseau.

    uv run python chapitres/chapitre_4_reseau.py

Trois choses que la couche réseau fait autrement que la couche fichiers :

  · elle a **trois** issues, pas deux — autorisé, refusé, et DEMANDÉ ;
  · elle ne raisonne pas par spécificité : `deniedDomains` l'emporte, point ;
  · elle n'honore que deux formes de joker. Une troisième est acceptée,
    continue de fonctionner pour WebFetch, et ne fait rien ici.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from outils.commun import config, ligne, titre, utf8      # noqa: E402
from outils.resolveur import (Config, appliquee,          # noqa: E402
                              motif_inerte, peut_joindre)

HOTES = ["registry.npmjs.org", "api.github.com", "gist.github.com",
         "raw.githubusercontent.com", "pypi.org", "evil.example.com"]


def verdict_court(config_, hote: str) -> str:
    v = peut_joindre(config_, hote)
    if not v.autorise:
        return "REFUS  "
    return "DEMANDE" if v.raison.startswith("hors liste") else "passe  "


def main() -> None:
    utf8()
    depot = config("depot")

    titre(1, "RIEN N'EST PRE-AUTORISE")
    print("   « Claude Code pre-allows no domains by default. The first time a")
    print("     command needs a new domain, Claude Code prompts for approval. »\n")
    nu = Config(enabled=True)
    for hote in HOTES[:3]:
        ligne(hote, verdict_court(nu, hote) + "  " + peut_joindre(nu, hote).raison, 26)
    print()
    print("   La troisieme issue est ce qui rend le bac a sable tenable. Un")
    print("   pare-feu a deux issues force a tout prevoir d'avance ; ici, un")
    print("   domaine inconnu ouvre une question, pas un echec.")

    titre(2, "LE DENY L'EMPORTE — MEME SUR UN ALLOW PLUS PRECIS")
    for cle in ("allowedDomains", "deniedDomains"):
        print(f"   {cle:<15}{depot.network[cle]}")
    print()
    for hote in HOTES:
        v = peut_joindre(depot, hote)
        ligne(hote, f"{verdict_court(depot, hote)}   {v.raison}", 28)
    print()
    print("   « gist.github.com » est PLUS SPECIFIQUE que « *.github.com », et")
    print("   c'est aussi le refus : les deux raisonnements donnent ici la")
    print("   meme reponse. Inversons-les pour voir laquelle s'applique.\n")
    piege = Config(enabled=True, network={
        "allowedDomains": ["gist.github.com"],       # le plus specifique
        "deniedDomains": ["*.github.com"],           # le plus large
    })
    ligne("gist.github.com", verdict_court(piege, "gist.github.com")
          + "   " + peut_joindre(piege, "gist.github.com").raison, 28)
    print()
    print("   Refuse. Le refus large gagne contre l'autorisation precise :")
    print("   la couche reseau n'est PAS la couche fichiers. On ne peut pas")
    print("   « rouvrir un sous-domaine » d'un deniedDomains, comme on rouvre")
    print("   un sous-dossier d'un denyRead.")

    titre(3, "DEUX FORMES DE JOKER, ET UNE TROISIEME QUI NE FAIT RIEN")
    print("   « the sandbox honors two wildcard forms: a leading *. and a bare")
    print("     *. A wildcard in any other position, such as example.*, still")
    print("     matches fetches but has no effect on sandboxed commands. »\n")
    for motif, exemple in (("*.github.com", "api.github.com"),
                           ("*", "n-importe-quoi.fr"),
                           ("api.*.com", "api.github.com"),
                           ("github.*", "github.com")):
        essai = Config(enabled=True, network={"allowedDomains": [motif]})
        etat = "INERTE" if motif_inerte(motif) else "honore"
        ligne(f"{motif:<14} sur {exemple:<20}",
              f"{etat}   {verdict_court(essai, exemple)}", 40)
    print()
    print("   « api.*.com » n'autorise pas, ne refuse pas, et ne previent pas.")
    print("   Il continue pourtant d'agir sur l'outil WebFetch : la regle")
    print("   marche a moitie, et la moitie qui ne marche pas est celle qui")
    print("   compte pour les commandes. outils/verifier.py la signale.")

    titre(4, "strictAllowlist : SUPPRIMER LA TROISIEME ISSUE")
    strict = config("utilisateur", "utilisateur")
    for hote in ("api.github.com", "pypi.org"):
        ligne(hote, f"{verdict_court(strict, hote)}   "
                    f"{peut_joindre(strict, hote).raison}", 20)
    print()
    print("   « pypi.org » passe de DEMANDE a REFUS. C'est le reglage d'un")
    print("   agent qui tourne sans personne devant : une question a laquelle")
    print("   nul ne repondra bloque aussi surement qu'un refus, mais elle")
    print("   bloque APRES un delai, et sans trace.")

    titre(5, "ET LA MEME CLE, DANS LE DEPOT")
    fautive = config("a-corriger", "projet")
    _, ignorees = appliquee(fautive)
    for perdue in ignorees:
        if perdue.cle == "network.strictAllowlist":
            print(f"   {perdue.consequence}")
            print(f"   Pourquoi : {perdue.pourquoi}.")
    print()
    for hote in ("pypi.org",):
        for portee in ("projet", "utilisateur"):
            c = config("a-corriger", portee)
            ligne(f"{hote} en portee {portee}", verdict_court(c, hote), 34)
    print()
    print("   Le meme fichier, deux endroits, deux politiques de securite.")
    print("   Rien dans le JSON ne le dit : c'est le CHEMIN du fichier qui")
    print("   decide, et le chemin ne se relit pas dans une revue de code.")

    print("\n   Au chapitre suivant : ce que la commande voit de vos secrets.\n")


if __name__ == "__main__":
    main()
