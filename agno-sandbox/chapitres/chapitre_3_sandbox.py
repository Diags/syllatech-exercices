"""Chapitre 3 — Isoler l'exécution : brancher un sandbox.

    uv run python chapitres/chapitre_3_sandbox.py

Trois niveaux, treize soumissions, une matrice. Le résultat n'est pas
flatteur, et c'est le point du chapitre : **ce qu'on peut faire en Python pur
et portable arrête moins de la moitié des attaques machine.**
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8               # noqa: E402
from jobportal.executeurs import DELAI, NIVEAUX, EnLocal      # noqa: E402
from jobportal.soumissions import CORPUS, par_famille         # noqa: E402
from outils.mesurer import NON_TESTABLE, matrice_execution    # noqa: E402


def main() -> None:
    utf8()

    titre(1, "LES TROIS NIVEAUX, ET CE QU'ILS AJOUTENT")
    for niveau in NIVEAUX:
        ligne(niveau.nom, ", ".join(niveau.protege) or "rien", 18)
    print()
    print("   Chaque ligne ajoute a la precedente. Et chacune coute quelque")
    print("   chose : un sous-processus demarre en ~200 ms la ou un exec()")
    print("   local prend 1 ms. C'est le prix a payer, et il est modeste.")

    titre(2, "LA MATRICE")
    lignes = matrice_execution()
    entete = "".join(f"{n.nom:<16}" for n in NIVEAUX)
    print(f"   {'soumission':<28}{'famille':<12}{entete}")
    for soumission, par_niveau in lignes:
        colonnes = "".join(f"{par_niveau[n.nom]:<16}" for n in NIVEAUX)
        print(f"   {soumission.nom:<28}{soumission.famille:<12}{colonnes}")

    titre(3, "CE QUE CHAQUE NIVEAU ARRETE")
    for niveau in NIVEAUX:
        testables = [s for s, p in lignes
                     if s.hostile and p[niveau.nom] != NON_TESTABLE]
        arretees = [s for s, p in lignes if s.hostile
                    and p[niveau.nom] not in ("REUSSIE", NON_TESTABLE)]
        ligne(niveau.nom,
              f"{len(arretees)}/{len(testables)} attaques arretees", 18)
    print()
    print("   ⚠️ Les denominateurs different, et il faut le dire : « en local »")
    print("   n'est teste que sur 8 attaques, parce que les deux soumissions")
    print("   « ressource » bloqueraient le processus de mesure. Ce n'est pas")
    print("   un avantage pour lui — c'est sa faiblesse la plus grave, et")
    print("   elle est si grave qu'elle empeche de la mesurer.")

    titre(4, "CE QUE « bride » N'ARRETE PAS, ET POURQUOI")
    restantes = [s for s, p in lignes
                 if s.famille == "machine" and p["bride"] == "REUSSIE"]
    for soumission in restantes:
        ligne(soumission.nom, soumission.vise, 26)
    print()
    print("   Les trois qui restent demandent ce que Python ne sait pas faire")
    print("   depuis Python :")
    print()
    print("   · couper le reseau demande un espace de noms reseau, un")
    print("     conteneur ou un pare-feu ;")
    print("   · empecher de lancer un processus demande un cgroup, seccomp")
    print("     ou une politique du systeme ;")
    print("   · l'evasion par __subclasses__ ne se corrige pas par un filtre")
    print("     d'imports : elle n'importe rien.")
    print()
    print("   Conclusion honnete : `Bride` est ce qu'on peut ecrire en Python")
    print("   portable, et c'est insuffisant. La suite est un CONTENEUR — le")
    print("   cours « Sandboxing securise » et « Docker & Kubernetes » y vont.")

    titre(5, "LE DELAI EST LA SEULE GARDE QUI TIENNE SEULE")
    par_nom = {s.nom: p for s, p in lignes}
    for soumission in par_famille("ressource"):
        etats = par_nom[soumission.nom]
        ligne(soumission.nom,
              ", ".join(f"{n.nom} : {etats[n.nom]}" for n in NIVEAUX), 20)
    print()
    print(f"   Le delai est de {DELAI:.0f} s. Il ne depend d'aucune liste de")
    print("   motifs, d'aucune analyse du code, et ne se contourne pas en")
    print("   reformulant : c'est une borne, pas une detection.")
    print()
    print("   Les bornes se comportent autrement que les filtres. Un filtre")
    print("   attrape ce qu'il a prevu ; une borne arrete ce qui la depasse,")
    print("   quelle qu'en soit la raison.")

    titre(6, "CE QU'AUCUN NIVEAU NE CHANGE")
    print(f"   {'soumission':<28}" + "".join(f"{n.nom:<16}" for n in NIVEAUX))
    for soumission, par_niveau in lignes:
        if soumission.famille != "verdict":
            continue
        print(f"   {soumission.nom:<28}"
              + "".join(f"{par_niveau[n.nom]:<16}" for n in NIVEAUX))
    print()
    print("   Trois soumissions, trois niveaux, neuf REUSSIE. C'est normal :")
    print("   ces trois-la ne touchent a rien. Elles ecrivent du texte sur")
    print("   leur sortie standard — ce que fait tout programme honnete.")
    print()
    print("   Un bac a sable parfait ne changerait pas une case de ce")
    print("   tableau. Il protege la MACHINE ; la ligne qui remonte vers le")
    print("   modele n'est pas de son ressort. C'est le chapitre 4.")

    print("\n   Au chapitre suivant : ce que le modele lit, et combien.\n")


if __name__ == "__main__":
    main()
