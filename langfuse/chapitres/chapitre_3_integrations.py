"""Chapitre 3 — Les integrations : trois chemins, un seul format.

    uv run python chapitres/chapitre_3_integrations.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from opentelemetry import trace                          # noqa: E402

from jobportal import console                            # noqa: E402
from jobportal.assistant import repondre                 # noqa: E402
from jobportal.collecteur import PREFIXE, brancher       # noqa: E402


def main() -> None:
    console.utf8()
    client, collecteur = brancher()

    print("1. TROIS CHEMINS, UN SEUL FORMAT\n")
    for chemin, quoi in (
            ("@observe()", "le SDK Python, directement"),
            ("OpenTelemetry", "Spring AI, LangChain4j, n'importe quel OTEL"),
            ("callback", "LiteLLM, LangChain : le framework appelle Langfuse")):
        print(f"   {chemin:<18}{quoi}")
    print("\n   Les trois produisent la MEME chose : des spans OTEL. C'est ce")
    print("   qui permet de tracer une application Spring et un script Python")
    print("   dans le meme tableau de bord, sans les faire se ressembler.")

    print("\n2. LA PREUVE : UN SPAN OTEL BRUT DANS LA MEME TRACE\n")
    tracer = trace.get_tracer("jobportal.maison")
    with tracer.start_as_current_span("verification-eligibilite") as span:
        span.set_attribute("candidat.anciennete_mois", 18)
        repondre("Quelles offres DevOps ?", "diaguily", "s-42")
    client.flush()

    for profondeur, o in collecteur.arbre():
        print(f"   {'  ' * profondeur}{o.nom:<26}{o.genre}")
    print("\n   Le span du haut n'a AUCUN decorateur Langfuse : c'est de")
    print("   l'OpenTelemetry ordinaire. Il apparait pourtant dans la trace,")
    print("   avec les autres en dessous. Rien a integrer — c'est deja le")
    print("   meme protocole.")

    print("\n3. CE QUE LANGFUSE AJOUTE PAR-DESSUS OTEL\n")
    attributs = set()
    for o in collecteur.observations:
        attributs |= {c for c in o.attributs if c.startswith(PREFIXE)}
    for attribut in sorted(attributs)[:8]:
        print(f"   {attribut}")
    print("\n   Des attributs conventionnels. Un span sans eux reste lisible")
    print("   comme une etape, mais il n'a ni entree, ni sortie, ni cout —")
    print("   c'est ce qui distingue une trace d'observabilite classique")
    print("   d'une trace de LLM.")

    print("\n4. LA CONFIGURATION SPRING BOOT, TELLE QU'ELLE EST\n")
    for ligne in (
            "management:",
            "  tracing:",
            "    sampling.probability: 1.0",
            "otel:",
            "  exporter:",
            "    otlp:",
            "      endpoint: http://localhost:3000/api/public/otel",
            '      headers: "Authorization=Basic ${LF_AUTH}"'):
        print(f"   {ligne}")
    print("\n   « sampling.probability: 1.0 » = on garde TOUT. C'est ce qu'on")
    print("   veut en developpement et rarement en production : a fort trafic,")
    print("   100 % des traces coute en stockage et en bande passante, pour")
    print("   une information qui se lit aussi bien sur 10 %.")
    print("\n   Le piege : l'echantillonnage se decide AVANT de savoir si la")
    print("   requete s'est mal passee. Un taux a 10 % perd 90 % des erreurs")
    print("   aussi. D'ou l'echantillonnage par tete — tout garder pour les")
    print("   requetes lentes ou en echec, echantillonner le reste.")

    print("\n5. LiteLLM : UN CALLBACK, ET LE COUT ARRIVE\n")
    print("   litellm_settings:")
    print('     success_callback: ["langfuse"]')
    print("\n   Le proxy connait le modele, les tokens et le tarif : il envoie")
    print("   des generations completes sans qu'on touche au code applicatif.")
    print("   C'est le chemin le plus rentable quand on a deja un proxy —")
    print("   et il ne trace que les APPELS MODELE, pas votre logique.")

    print("\n6. LES DEUX ENSEMBLE\n")
    print("   Application → OTEL → Langfuse   (vos etapes, votre logique)")
    print("   LiteLLM     → callback → Langfuse (les couts, exacts)")
    print("\n   Les deux se rejoignent si — et seulement si — ils partagent le")
    print("   meme identifiant de trace. Sans propagation, on obtient deux")
    print("   moities qui ne se parlent pas : une trace applicative sans cout,")
    print("   et des couts sans contexte.")


if __name__ == "__main__":
    main()
