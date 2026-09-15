"""Chapitre 6 — Red teaming defensif : rejouer, mesurer, surveiller.

    uv run python chapitres/chapitre_6_redteam.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "outils"))

from jobportal import console                              # noqa: E402
from jobportal.attaques import ATTAQUES                    # noqa: E402
from jobportal.defenses import Agent, Configuration        # noqa: E402
from redteam import COUCHES, obeissances, passees, tableau  # noqa: E402


def main() -> None:
    console.utf8()
    tableau()

    print("\n  6. LE JOURNAL, ET CE QU'IL FAUT SURVEILLER\n")
    journal = []
    for attaque in ATTAQUES:
        resultat = Agent(Configuration.toutes()).analyser_cv(attaque.charge)
        journal += resultat.journal.actions()
        if resultat.bloquee_par:
            journal.append(f"bloque:{resultat.bloquee_par.split(' ')[0]}")
    compte: dict[str, int] = {}
    for action in journal:
        compte[action] = compte.get(action, 0) + 1
    for action, n in sorted(compte.items(), key=lambda x: -x[1]):
        print(f"   {n:>3}  {action}")
    print("\n   Trois signaux valent une alerte, et aucun n'est un plantage :")
    print("     · un REFUS d'outil — quelqu'un a demande ce qu'il ne peut pas ;")
    print("     · un blocage du garde d'entree — une tentative connue ;")
    print("     · instruction_suspecte_detectee — un document porteur d'ordres.")
    print("\n   Sans journal, une attaque bloquee est indiscernable d'une")
    print("   journee calme. Bloquer sans compter, c'est ignorer qu'on est")
    print("   attaque.")

    print("\n  7. LA CI — parce qu'une defense se degrade sans bruit\n")
    print("     # .github/workflows/redteam.yml")
    print("     on:")
    print("       schedule: [{ cron: \"0 6 * * 1\" }]")
    print("       pull_request:")
    print("         paths: [\"jobportal/defenses.py\", \"jobportal/attaques.py\"]")
    print("     jobs:")
    print("       redteam:")
    print("         steps:")
    print("           - run: uv run python outils/redteam.py --ci")
    print("\n   Une regle ajoutee au prompt, un outil ajoute a la liste, et la")
    print("   couverture baisse — sans qu'aucun test fonctionnel ne bouge.")
    print("   `--ci` rend 1 des qu'une attaque obtient une consequence.")

    print("\n  8. CE QUE CE HARNAIS NE PROUVE PAS\n")
    print(f"   · Il rejoue {len(ATTAQUES)} attaques CONNUES. Un corpus ne prouve")
    print("     que ce qu'il contient — zero attaque reussie ne veut pas dire")
    print("     zero vulnerabilite, et ne le voudra jamais.")
    print("   · Le modele est simule. Un vrai modele resiste mieux a certaines")
    print("     attaques et moins bien a d'autres ; seules VOS mesures, sur")
    print("     VOTRE modele, vous concernent.")
    print("   · promptfoo genere des variantes et attaque l'application HTTP")
    print("     reelle. C'est complementaire, pas redondant : ce harnais sert")
    print("     a ecrire les defenses, promptfoo a les eprouver.")
    print("\n   Le dire fait partie du travail. Un rapport de securite qui")
    print("   annonce « aucune vulnerabilite » sans dire ce qu'il a teste")
    print("   n'informe de rien.")


if __name__ == "__main__":
    main()
