"""Chapitre 2 — La sortie typee : CrewAI valide, il ne demande pas.

    uv run python chapitres/chapitre_2_taches.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic import ValidationError                            # noqa: E402

from jobportal import console                                   # noqa: E402
from jobportal.equipe import Rapport, Tendance, equipe_typee     # noqa: E402
from jobportal.modele import ModeleFactice                      # noqa: E402


def main() -> None:
    console.utf8()

    print("1. UNE TACHE TYPEE\n")
    resultat = equipe_typee(ModeleFactice()).kickoff(inputs={"sujet": "DevOps"})
    rapport = resultat.pydantic
    print(f"   type      {type(rapport).__name__}")
    print(f"   tendances {len(rapport.tendances)}")
    for t in rapport.tendances:
        print(f"     · {t.titre[:48]:<50}impact={t.impact}  source={t.source}")
    print(f"   resume    {rapport.resume[:60]}")

    print("\n2. « VALIDE » VEUT DIRE EXECUTE\n")
    for essai in ({"titre": "K8s", "impact": 3, "source": "portail"},
                  {"titre": "K8s", "impact": 9, "source": "portail"}):
        try:
            Tendance(**essai)
            print(f"   accepte  {essai}")
        except ValidationError as e:
            print(f"   REFUSE   impact={essai['impact']} — {e.errors()[0]['msg']}")
    print("\n   `output_pydantic` ne DEMANDE pas au modele d'etre structure :")
    print("   CrewAI valide sa reponse contre le schema. C'est la difference")
    print("   entre un agent qu'on branche sur du code et un agent qu'on")
    print("   relit a la main.")

    print("\n3. LE SCHEMA EST AUSSI UN PROMPT\n")
    for nom, champ in Tendance.model_json_schema()["properties"].items():
        bornes = {k: v for k, v in champ.items()
                  if k in ("minimum", "maximum", "type")}
        print(f"   {nom:<10}{bornes}")
    print("\n   Les bornes ge/le deviennent minimum/maximum dans le schema")
    print("   envoye au modele. Une classe bien ecrite est un meilleur prompt")
    print("   que trois phrases d'expected_output.")

    print("\n4. expected_output RESTE UTILE\n")
    print("   Il decrit la FORME attendue en prose, et le modele le lit. Avec")
    print("   output_pydantic, il devient un doublon — gardez-le court, ou")
    print("   supprimez-le. Deux descriptions qui divergent valent mieux")
    print("   qu'une seule fausse, mais moins qu'une seule vraie.")


if __name__ == "__main__":
    main()
