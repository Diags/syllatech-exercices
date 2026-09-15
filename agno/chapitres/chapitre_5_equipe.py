"""Chapitre 5 — Equipes d'agents : ce que la delegation coute vraiment.

    uv run python chapitres/chapitre_5_equipe.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                              # noqa: E402
from jobportal.agents import conseiller_outille, equipe    # noqa: E402
from jobportal.modele import ModeleFactice                 # noqa: E402


class Compteur(ModeleFactice):
    """Compte les appels au modele, tous membres confondus."""

    total = 0

    def invoke(self, messages=None, **kwargs):
        Compteur.total += 1
        self.signes = getattr(self, "signes", 0) + sum(
            len(str(m.content or "")) for m in (messages or []))
        return super().invoke(messages=messages, **kwargs)


def main() -> None:
    console.utf8()
    question = "Le marche DevOps a Lyon, offres et salaires ?"

    print("1. UN AGENT SEUL\n")
    Compteur.total = 0
    seul = Compteur()
    resultat = conseiller_outille(seul).run(question)
    appels_seul, signes_seul = Compteur.total, seul.signes
    print(f"   {resultat.content[:104]}")
    print(f"\n   {appels_seul} appel(s) au modele, {signes_seul} signes envoyes.")

    print("\n2. UNE EQUIPE DE DEUX SPECIALISTES\n")
    Compteur.total = 0
    resultat = equipe(Compteur()).run(question)
    print(f"   {str(resultat.content)[:160]}")
    print(f"\n   {Compteur.total} appel(s) au modele.")

    print("\n3. LA FACTURE\n")
    print(f"   {'agent seul':<28}{appels_seul:>4} appel(s)")
    print(f"   {'equipe de deux':<28}{Compteur.total:>4} appel(s)")
    print(f"\n   {Compteur.total / max(appels_seul, 1):.0f}x plus. Et c'est normal :")
    print("   le coordinateur reflechit, delegue, attend, puis synthetise.")
    print("   Chaque membre est un agent COMPLET, avec son modele et ses")
    print("   outils. Une equipe de trois, ce sont au moins quatre additions.")

    print("\n4. QUAND UNE EQUIPE VAUT SON PRIX\n")
    cas = [
        ("oui", "des specialites vraiment differentes", "web + base interne + juridique"),
        ("oui", "des outils incompatibles dans un seul agent", "20 outils diluent le choix"),
        ("non", "deux agents qui font la meme chose", "un seul suffisait"),
        ("non", "une question a une seule etape", "le coordinateur ne sert a rien"),
        ("non", "pour « paralleliser »", "en mode coordinate, il attend chaque membre"),
    ]
    for verdict, cas_, raison in cas:
        print(f"   {verdict:<5}{cas_:<44}{raison}")

    print("\n5. LE PIEGE DU MODE COORDINATE\n")
    print("   Le coordinateur delegue par IDENTIFIANT de membre, derive du")
    print("   nom : « Analyste offres » devient « analyste-offres ». Deleguer")
    print("   au NOM echoue avec « Member with ID ... not found » — une erreur")
    print("   que le modele voit et corrige, au prix d'un tour supplementaire.")
    print("\n   Des noms de membres courts et distincts ne sont donc pas de la")
    print("   cosmetique : ils reduisent le nombre de tours.")


if __name__ == "__main__":
    main()
