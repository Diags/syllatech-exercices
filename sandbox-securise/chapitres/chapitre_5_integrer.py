"""Chapitre 5 — Integrer un bac a sable dans un service existant.

    uv run python chapitres/chapitre_5_integrer.py
"""
from __future__ import annotations
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.conteneur import durcie                 # noqa: E402
from jobportal.evasions import CODE_HONNETE            # noqa: E402
from jobportal.niveaux import DELAI, naif, processus   # noqa: E402


def main() -> None:
    console.utf8()

    print("1. LE SERVICE, EN QUATRE DECISIONS\n")
    decisions = [
        ("un bac a sable PAR soumission", "jetable : rien ne survit a l'execution"),
        ("un nom unique", "sans lui, deux soumissions se marchent dessus"),
        ("un delai cote APPELANT", "le bac a sable peut mentir ; le client, non"),
        ("la sortie tronquee", "10 Mo de stdout est aussi un deni de service"),
    ]
    for quoi, pourquoi in decisions:
        print(f"   {quoi:<34}{pourquoi}")

    print("\n2. LE DELAI EST UN CONTRAT, PAS UNE SUGGESTION\n")
    debut = time.perf_counter()
    r = processus("while True:\n    pass", delai=1.0)
    duree = time.perf_counter() - debut
    print(f"   boucle infinie, delai 1 s → arretee en {duree:.2f} s")
    print(f"   motif : {r.motif}")
    print("\n   Le meme code, sans delai, figerait le service jusqu'au")
    print("   redemarrage. Un seul candidat, une seule ligne.")

    print("\n3. LE CODE HONNETE NE DOIT RIEN PERDRE\n")
    for nom, f in (("naif", naif), ("processus", processus)):
        debut = time.perf_counter()
        r = f(CODE_HONNETE)
        print(f"   {nom:<12}{r.sortie!r:<8}{(time.perf_counter() - debut) * 1000:>6.0f} ms")
    print("\n   Le surcout d'un processus est reel et mesurable. C'est le prix")
    print("   du niveau 3, et il se compare a ce qu'on protege — pas a zero.")

    print("\n4. CE QUE LA COUCHE HTTP DOIT AJOUTER\n")
    ajouts = [
        ("une file d'attente", "sinon N soumissions = N conteneurs simultanes"),
        ("une limite par utilisateur", "sinon un seul compte sature la machine"),
        ("un journal", "qui a soumis quoi, et ce que ca a rendu"),
        ("un kill switch", "debrancher l'execution sans redeployer"),
    ]
    for quoi, pourquoi in ajouts:
        print(f"   {quoi:<28}{pourquoi}")
    print("\n   Le bac a sable protege la MACHINE. La file et les quotas")
    print("   protegent le SERVICE — ce sont deux problemes, et le second")
    print("   s'oublie parce qu'il ne ressemble pas a de la securite.")

    print("\n5. LA COMMANDE QUE LE SERVICE LANCE\n")
    print("   " + durcie(image="runner:python", code="<code du candidat>",
                         runtime="runsc"))
    print(f"\n   Delai cote appelant : {DELAI:g} s. Le conteneur a ses propres")
    print("   bornes ; l'appelant n'a pas a leur faire confiance.")


if __name__ == "__main__":
    main()
