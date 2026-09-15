"""Chapitre 1 — Un agent Agno qui exécute du code.

    uv run python chapitres/chapitre_1_agent.py

Le cours commence par un agent naïf : `PythonTools()`, et le code du candidat
tourne dans votre processus. Ce chapitre regarde ce que fait vraiment cet
outil, puis mesure ce qu'un code de candidat obtient à ce niveau-là.

⚠️ Le corpus de ce projet est INOFFENSIF par construction : ses soumissions
hostiles lisent, comptent et impriment. Aucune n'efface, n'envoie rien à
l'extérieur ni ne modifie quoi que ce soit.
"""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal.commun import ligne, titre, utf8               # noqa: E402
from jobportal.executeurs import EnLocal                      # noqa: E402
from jobportal.soumissions import CORPUS, compter, par_famille  # noqa: E402


def main() -> None:
    utf8()

    titre(1, "CE QUE PythonTools FAIT VRAIMENT")
    from agno.tools.python import PythonTools

    source = inspect.getsource(PythonTools.run_python_code)
    executantes = [l.strip() for l in source.splitlines()
                   if "exec(" in l or "eval(" in l]
    ligne("outils exposes", ", ".join(
        m for m in dir(PythonTools) if m.startswith(("run_", "save_")))[:56], 22)
    print()
    for l in executantes:
        print(f"      {l}")
    print()
    print("   « safe_globals » ne qualifie que le dictionnaire de noms. Le")
    print("   code s'execute dans VOTRE processus : vos descripteurs de")
    print("   fichiers, vos variables d'environnement, votre reseau, vos")
    print("   droits. Un dictionnaire de noms ne separe pas des privileges.")

    titre(2, "LE CORPUS DU JOB PORTAL")
    for famille, combien in compter().items():
        exemples = ", ".join(s.nom for s in par_famille(famille)[:3])
        ligne(f"{famille} ({combien})", exemples, 18)
    print()
    print("   Quatre familles, et la troisieme est celle qu'on oublie :")
    print("   « verdict » ne touche a RIEN. Elle ecrit du texte sur sa sortie")
    print("   standard, et ce texte remonte jusqu'au modele qui note.")

    titre(3, "CE QU'OBTIENT UN CANDIDAT, EN LOCAL")
    local = EnLocal()
    print(f"   {'soumission':<28}{'vise':<44}resultat")
    for soumission in CORPUS:
        if soumission.famille == "ressource":
            print(f"   {soumission.nom:<28}{soumission.vise[:43]:<44}"
                  f"non teste ici : bloquerait ce processus")
            continue
        execution = local.executer(soumission.code)
        if soumission.hostile:
            etat = ("REUSSIE" if soumission.a_reussi(execution.sortie)
                    else "arretee")
        else:
            etat = "exercice ok" if execution.reussie else "exercice ko"
        print(f"   {soumission.nom:<28}{soumission.vise[:43]:<44}{etat}")
    print()
    reussies = [s for s in CORPUS if s.hostile and s.famille != "ressource"
                and s.a_reussi(local.executer(s.code).sortie)]
    print(f"   {len(reussies)} attaques sur "
          f"{len([s for s in CORPUS if s.hostile and s.famille != 'ressource'])} "
          f"reussissent a ce niveau.")
    print()
    print("   Et les deux soumissions « ressource » ne sont meme pas")
    print("   testables ici : une boucle infinie dans votre processus bloque")
    print("   l'agent, le serveur web qui l'heberge, et tout ce qu'il servait.")
    print("   Il n'y a pas de delai possible sur un exec() local.")

    titre(4, "LE DECOUPAGE DU PROBLEME")
    for quoi, qui, chapitre in (
            ("le code touche la machine", "un bac a sable", "3"),
            ("le code ne rend pas la main", "un delai, donc un processus", "3"),
            ("le code parle au modele", "une garde sur le prompt", "4"),
            ("le modele repond n'importe quoi", "une sortie typee", "2")):
        print(f"   {quoi:<34}{qui:<30}ch. {chapitre}")
    print()
    print("   Les quatre lignes sont independantes, et c'est la seule chose")
    print("   a retenir de ce chapitre. Un bac a sable parfait ne fait rien")
    print("   contre la troisieme ; une sortie typee ne fait rien contre la")
    print("   premiere. Les cinq chapitres suivants les prennent une par une.")

    print("\n   Au chapitre suivant : contraindre ce que l'agent rend.\n")


if __name__ == "__main__":
    main()
