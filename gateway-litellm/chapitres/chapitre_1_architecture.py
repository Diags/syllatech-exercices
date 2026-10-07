"""Chapitre 1 — L'architecture d'une passerelle IA.

    uv run python chapitres/chapitre_1_architecture.py

Le maillage N×M n'est pas une image : il se compte. Ce chapitre le compte,
puis paie le prix de l'étoile — parce qu'une passerelle en a un, et qu'un
cours qui ne le dit pas vend une solution sans facture.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import config, ligne, titre, utf8    # noqa: E402
from jobportal.proxy import charger                        # noqa: E402

APPLICATIONS = ["job portal", "back-office RH", "matching", "analytics"]
FOURNISSEURS = ["Anthropic", "OpenAI", "Gemini", "Ollama local"]


def main() -> None:
    utf8()

    titre(1, "LE MAILLAGE N×M, COMPTE")
    n, m = len(APPLICATIONS), len(FOURNISSEURS)
    print(f"   {n} applications, {m} fournisseurs.\n")
    ligne("integrations a ecrire", f"{n} × {m} = {n * m}")
    ligne("depots ou une cle est copiee", f"{n}")
    ligne("endroits a modifier pour ajouter", f"{n}  (un par application)")
    ligne("endroits a modifier pour revoquer", f"{n}")
    ligne("endroit ou lire le cout total", "aucun")
    print()
    print("   La derniere ligne est la pire. Les autres coutent du temps ;")
    print("   celle-la interdit toute decision — on ne peut ni arbitrer entre")
    print("   deux modeles, ni voir une equipe deriver, ni refacturer.")

    titre(2, "L'ETOILE")
    ligne("integrations a ecrire", f"{n} + {m} = {n + m}")
    ligne("depots ou une cle est copiee", "0  (le proxy les detient)")
    ligne("endroits pour ajouter un modele", "1  (une entree de YAML)")
    ligne("endroits pour revoquer une equipe", "1  (une cle virtuelle)")
    ligne("endroit ou lire le cout total", "1")
    print()
    print(f"   {n * m} integrations deviennent {n + m}. Le gain n'est pas le")
    print("   nombre : c'est que les quatre dernieres lignes passent de N a 1.")

    titre(3, "CE QUE L'ETOILE COUTE")
    print("   Une passerelle n'est pas gratuite. Trois factures, dont deux")
    print("   qu'on decouvre en production :\n")
    ligne("un saut reseau de plus", "latence + un point de panne")
    ligne("un service a exploiter", "proxy + PostgreSQL + Redis")
    ligne("un demarrage lent", "mesure juste en dessous")
    print()
    debut = time.perf_counter()
    import litellm                                          # noqa: F401
    duree = time.perf_counter() - debut
    print(f"   « import litellm » : {duree:.1f} s sur cette machine.")
    print()
    print("   C'est la bibliotheque, pas ce projet : elle charge sa table de")
    print("   prix et ses cent integrations. En production c'est du demarrage")
    print("   de conteneur, paye une fois — mais c'est a savoir AVANT de")
    print("   regler une sonde de vivacite a 10 secondes, ou de croire qu'un")
    print("   redemarrage est instantane.")

    titre(4, "DEUX COUCHES, ET POURQUOI PAS UNE")
    for couche, role, ce_qu_elle_ignore in (
            ("Spring Cloud Gateway", "JWT, debit, routage global",
             "les fournisseurs et leurs cles"),
            ("Proxy LiteLLM", "traduction, cles, budgets, bascule",
             "vos utilisateurs")):
        print(f"   {couche}")
        print(f"      fait      {role}")
        print(f"      ignore    {ce_qu_elle_ignore}")
    print()
    print("   La seconde ligne de chaque bloc est la raison d'etre du")
    print("   decoupage. Une couche unique connaitrait a la fois vos")
    print("   utilisateurs et vos cles de fournisseur : sa compromission")
    print("   donnerait les deux. Chaque maillon ne connait que le secret du")
    print("   maillon suivant — jamais celui d'apres.")

    titre(5, "LE config.yaml DE CE PROJET")
    declaration = charger(config())
    for entree in declaration["model_list"]:
        params = entree["litellm_params"]
        ligne(f"alias « {entree['model_name']} »",
              f"{params['model']:<30}"
              f"{'cle: ' + params.get('api_key', '(aucune)').split('/')[-1]}",
              22)
    print()
    print("   L'application ne connait que la colonne de gauche. Changer la")
    print("   colonne du milieu ne demande aucun redeploiement applicatif.")

    print("\n   Au chapitre suivant : ce que LiteLLM fait vraiment de ces")
    print("   trois lignes.\n")


if __name__ == "__main__":
    main()
