"""Chapitre 2 — Code Interpreter : la sandbox d'exécution.

    uv run python chapitres/chapitre_2_sandbox.py

Le SDK réel est installé : ce chapitre affiche d'abord la vraie signature de
`code_session` et de `CodeInterpreter.invoke`, puis exécute le même cycle sur
un bac local — parce qu'ouvrir une vraie session demande un compte AWS, une
région et un rôle IAM.

Ce qu'on peut donc vérifier ici : le cycle, la persistance de l'état, et le
flux de données vers le modèle. Ce qu'on ne peut pas : l'isolation réelle.
Le chapitre le dit à la fin, sans le contourner.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8                   # noqa: E402
from jobportal.metier import CATALOGUE                            # noqa: E402
from jobportal.sandbox import (SessionFermee, avec_sandbox,       # noqa: E402
                               code_session, cout_en_signes,
                               sans_sandbox, sdk_reel)

CSV = "titre,ville,contrat,salaire\n" + "\n".join(
    f"{t},{v},{c},{s}" for t, v, c, s in CATALOGUE)

# Le code que l'agent ecrit. Il LIT le fichier televerse : les donnees ne
# passent donc jamais par le contexte du modele — seul le resultat remonte.
ANALYSE = """
import csv, io
lignes = list(csv.DictReader(io.StringIO(FICHIERS["candidatures.csv"])))
par_ville = {}
for l in lignes:
    par_ville[l["ville"]] = par_ville.get(l["ville"], 0) + 1
print(sorted(par_ville.items(), key=lambda x: -x[1]))
""".strip()


def main() -> None:
    utf8()

    titre(1, "CE QUE LE SDK EXPOSE VRAIMENT")
    reel = sdk_reel()
    ligne("code_session", reel["code_session"], 16)
    ligne("invoke", reel["invoke"], 16)
    print(f"   methodes      {', '.join(reel['methodes'][:9])}…")
    print()
    print("   Tout cela existe dans le paquet installe. Ce qui manque pour")
    print("   l'appeler : un compte AWS, une region, un role IAM. La suite")
    print("   du chapitre rejoue le meme cycle sur un bac local.")

    titre(2, "LE CYCLE : SESSION, EXECUTIONS, DESTRUCTION")
    with code_session("eu-west-1") as bac:
        ligne("session ouverte", bac.session_id, 20)
        bac.invoke("writeFiles", {"content": [
            {"path": "candidatures.csv", "text": CSV}]})
        ligne("fichier televerse", bac.invoke("listFiles")[0].contenu, 20)

        evenements = bac.invoke("executeCode",
                                {"language": "python", "code": ANALYSE})
        for evenement in evenements:
            ligne(f"  {evenement.type}", evenement.contenu, 18)
        ligne("executions", str(bac.executions), 20)
        session = bac.session_id

    ligne("apres le bloc with", f"session_id = {bac.session_id}", 20)
    try:
        bac.invoke("executeCode", {"code": "1"})
    except SessionFermee as erreur:
        ligne("un appel de plus", f"refuse — {erreur}", 20)
    print()
    print(f"   La session « {session} » n'existe plus, et tout ce qu'elle")
    print("   contenait avec elle. Un code malveillant execute au tour 3 ne")
    print("   peut donc rien laisser pour le tour 4 : la destruction est la")
    print("   moitie de la securite, l'isolation etant l'autre.")

    titre(3, "L'ETAT PERSISTE ENTRE LES EXECUTIONS")
    with code_session() as bac:
        bac.invoke("executeCode", {"code":
                                   "def moyenne(xs): return sum(xs)/len(xs)"})
        salaires = [s for *_, s in CATALOGUE]
        bac.espace["SALAIRES"] = salaires
        sortie = bac.invoke("executeCode",
                            {"code": "print(round(moyenne(SALAIRES), 1))"})
        ligne("tour 1", "def moyenne(...)  — rien n'est affiche", 12)
        ligne("tour 2", f"moyenne(SALAIRES) → {sortie[0].contenu}", 12)
    print()
    print("   C'est ce qui permet a l'agent de construire son calcul en")
    print("   plusieurs tours. C'est aussi ce qui fait qu'une variable mal")
    print("   nommee au tour 1 empoisonne le tour 5 — l'etat est un acquis")
    print("   ET une dette.")

    titre(4, "CE QUI REMONTE AU MODELE : LE RESULTAT, PAS LE CODE")
    with code_session() as bac:
        bac.invoke("writeFiles", {"content": [
            {"path": "candidatures.csv", "text": CSV}]})
        evenements = bac.invoke("executeCode", {"code": ANALYSE})
        resultat = avec_sandbox(evenements)

    naif = sans_sandbox(ANALYSE, resultat)
    ligne("sans sandbox (code + calcul)",
          f"{cout_en_signes(naif):>5} signes remontent", 32)
    ligne("avec sandbox (resultat seul)",
          f"{cout_en_signes(resultat):>5} signes remontent", 32)
    print(f"\n   Rapport : {cout_en_signes(naif) / max(1, cout_en_signes(resultat)):.1f}×"
          f" sur UN appel.")
    print()
    print("   Le gain n'est pas la : c'est qu'il se cumule. A la dixieme")
    print("   iteration, l'agent sans sandbox traine dix versions de son")
    print("   code dans son contexte — et les relit a chaque tour. Avec, il")
    print("   ne traine que dix resultats.")
    print()
    print("   Et surtout : le resultat est JUSTE. Un modele qui compte de")
    print("   tete se trompe sur les additions longues ; celui-ci ne compte")
    print("   pas, il fait compter.")

    titre(5, "UNE ERREUR NE TUE PAS LA SESSION")
    with code_session() as bac:
        rate = bac.invoke("executeCode", {"code": "1/0"})
        ligne("code fautif", rate[0].contenu, 20)
        suite = bac.invoke("executeCode", {"code": "print('la session vit')"})
        ligne("appel suivant", suite[0].contenu, 20)
    print()
    print("   L'agent peut donc corriger et reessayer, ce qui est tout")
    print("   l'interet : le code genere par un modele est faux une fois sur")
    print("   trois, et la boucle « executer, lire l'erreur, corriger » est")
    print("   ce qui le rend utilisable.")

    titre(6, "CE QUE CE CHAPITRE NE PROUVE PAS")
    for limite in (
            "l'isolation reelle : le bac local separe des VARIABLES, pas des",
            "   privileges. La sandbox AgentCore est un environnement distant,",
            "   sans acces a votre reseau interne ni a vos secrets ;",
            "l'installation de paquets (install_packages) et le telechargement",
            "   de fichiers, qui passent par l'API AWS ;",
            "les langages JavaScript et TypeScript, egalement supportes."):
        print(f"   · {limite}" if not limite.startswith("   ") else limite)
    print()
    print("   Le cours « Sandboxing securise » mesure, lui, ce qu'une vraie")
    print("   isolation arrete — et ce qu'elle n'arrete pas.")

    print("\n   Au chapitre suivant : le meme cycle, pour un navigateur.\n")


if __name__ == "__main__":
    main()
