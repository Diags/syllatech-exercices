"""Chapitre 1 — Le premier trace, et ce qu'il contient vraiment.

    uv run python chapitres/chapitre_1_demarrer.py
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import observe                        # noqa: E402

from jobportal import console                       # noqa: E402
from jobportal.assistant import repondre            # noqa: E402
from jobportal.collecteur import brancher           # noqa: E402


def main() -> None:
    console.utf8()
    client, collecteur = brancher()

    print("1. UN DECORATEUR, UN TRACE\n")
    print("     @observe()")
    print("     def assistant_carriere(question): ...")
    print("\n   C'est tout. Le SDK ouvre un span OpenTelemetry, y ecrit les")
    print("   entrees et les sorties, et le ferme au retour de la fonction.")

    repondre("Quelles offres DevOps ?", "diaguily", "s-42")
    client.flush()

    print("\n2. CE QUE LE COLLECTEUR A RECU\n")
    for profondeur, o in collecteur.arbre():
        print(f"   {'  ' * profondeur}{o.nom:<22}{o.genre:<12}{o.duree_ms:>6.1f} ms")

    print("\n3. LES ATTRIBUTS D'UN SPAN\n")
    racine = collecteur.racines[0]
    for cle, valeur in sorted(racine.metadonnees.items()):
        print(f"   {cle:<34}{str(valeur)[:48]}")

    print("\n4. CE PROJET N'EST PAS UNE SIMULATION\n")
    print("   Langfuse 3.x est bati sur OpenTelemetry. « @observe() » ouvre un")
    print("   span, et ce qui part vers le serveur, ce sont ces spans tels")
    print("   quels. On fournit ici notre propre TracerProvider :")
    print("\n     Langfuse(..., tracer_provider=le_notre)")
    print("\n   Le SDK est REEL. Seule la destination change — et c'est ce qui")
    print("   rend ce projet executable sans compte, sans cle, sans reseau.")

    print("\n5. LE PIEGE QUI COUTE UNE HEURE\n")
    print("     Langfuse(..., tracing_enabled=False)")
    print("\n   A False, « @observe() » devient un decorateur qui ne fait")
    print("   rien. Aucune erreur, aucune trace — et l'on cherche du cote du")
    print("   serveur, des cles, du reseau. La variable d'environnement")
    print("   LANGFUSE_TRACING_ENABLED fait la meme chose, a distance.")

    print("\n6. flush() N'EST PAS OPTIONNEL\n")
    print("   Les spans partent par lots. Un script qui se termine sans")
    print("   flush() perd ses dernieres traces — silencieusement. Dans un")
    print("   service long, le lot part tout seul ; dans un script, non.")


if __name__ == "__main__":
    main()
