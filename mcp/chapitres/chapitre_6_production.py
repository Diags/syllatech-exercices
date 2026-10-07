"""Chapitre 6 — Intégration et production.

Un serveur MCP en production, ce n'est pas un serveur de plus : c'est un
serveur qu'on observe, dont on versionne le contrat, et dont on borne le
périmètre. Ce chapitre instrumente un appel réel et affiche sa trace.

    uv run python chapitres/chapitre_6_production.py
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

from jobportal import console               # noqa: E402
from jobportal.serveur import creer_candidature, rechercher_offres   # noqa: E402


@dataclass
class Trace:
    outil: str
    duree_ms: float
    etat: str
    detail: str


def appeler(nom, fonction, *args):
    """Le minimum vital d'observabilite : combien de temps, et quel etat.
    Sans cela, un outil lent ou cassé ne se voit que dans les plaintes."""
    depart = time.perf_counter()
    try:
        resultat = fonction(*args)
        return Trace(nom, (time.perf_counter() - depart) * 1000, "OK",
                     f"{len(resultat)} resultat(s)" if isinstance(resultat, list) else str(resultat)[:48])
    except Exception as e:   # noqa: BLE001 — on trace l'echec au lieu de le masquer
        return Trace(nom, (time.perf_counter() - depart) * 1000, "ERREUR", str(e)[:48])


def main() -> None:
    console.utf8()
    print("Traces de quatre appels d'outils :\n")
    print(f"  {'outil':<22} {'duree':>9}  {'etat':<7} detail")
    traces = [
        appeler("rechercher_offres", rechercher_offres, "python"),
        appeler("rechercher_offres", rechercher_offres, "kubernetes"),
        appeler("creer_candidature", creer_candidature, "JP-001", "CV de test"),
        appeler("creer_candidature", creer_candidature, "JP-999", "CV de test"),
    ]
    for t in traces:
        print(f"  {t.outil:<22} {t.duree_ms:>7.2f}ms  {t.etat:<7} {t.detail}")

    echecs = [t for t in traces if t.etat != "OK"]
    print(f"\n  {len(traces)} appels, {len(echecs)} echec(s).")
    if echecs:
        print(f"  Le dernier echoue volontairement : l'offre JP-999 n'existe pas.")
        print("  Remarquez que l'erreur est TRACEE, pas avalee : un outil qui")
        print("  renvoie silencieusement une liste vide est indebuggable.")

    print("\nTrois regles pour la mise en production :")
    print("  1. Versionnez le contrat. Les noms d'outils et leurs parametres")
    print("     sont une API publique : les renommer casse les agents en place.")
    print("  2. Bornez le perimetre. N'exposez que le necessaire, en lecture")
    print("     seule par defaut ; l'ecriture demande une permission explicite.")
    print("  3. Observez. Nom de l'outil, duree, etat : trois colonnes suffisent")
    print("     a reperer l'outil lent que personne n'ose signaler.")
    print("\nUne gateway peut ensuite federer plusieurs serveurs derriere un seul")
    print("point d'entree — c'est le sujet du cours agentgateway.")


if __name__ == "__main__":
    main()
