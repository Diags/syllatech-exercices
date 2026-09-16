"""Chapitre 3 — Raisonner avant de conclure.

« Raisonne étape par étape » n'est pas une formule magique : c'est une
demande de faire apparaitre les etapes intermediaires. Ce chapitre montre ce
que cela change concretement — pas sur le score, mais sur ce qu'on peut
DEBUGGER.

    uv run python chapitres/chapitre_3_cot.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                   # noqa: E402
from jobportal.modele import modele                              # noqa: E402
from jobportal.prompts import V2, V3                             # noqa: E402

CAS = "Ambiance froide mais salaire correct"


def main() -> None:
    console.utf8()
    m = modele()

    sans = m.repondre(V2.format(entree=CAS), CAS)
    avec = m.repondre(V3.format(entree=CAS), CAS)

    print(f"Feedback : « {CAS} »\n")
    print(f"   sans demande de raisonnement : {sans.texte}")
    print(f"      raisonnement exposé : {sans.raisonnement or '(aucun)'}\n")
    print(f"   avec « raisonne étape par étape » : {avec.texte}")
    print("      raisonnement exposé :")
    for etape in avec.raisonnement:
        print(f"         · {etape}")

    print("\nLes deux peuvent donner la même conclusion. La différence n'est")
    print("pas là : c'est qu'on voit SUR QUOI la conclusion s'appuie.")
    print("\nQuand un classement vous surprend, la version sans raisonnement")
    print("ne vous laisse qu'une option : changer le prompt au hasard. La")
    print("version avec vous montre l'exemple qui a pesé — et donc lequel")
    print("corriger. C'est exactement ce qu'on a diagnostiqué au chapitre 2.")
    print("\nCoût : des sorties plus longues, donc plus lentes et plus chères.")
    print("À réserver aux tâches à plusieurs étapes, pas à une classification")
    print("triviale — sauf, justement, pendant la mise au point.")


if __name__ == "__main__":
    main()
