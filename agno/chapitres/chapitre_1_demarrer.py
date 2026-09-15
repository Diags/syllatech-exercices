"""Chapitre 1 — Un agent Agno, et ce qu'il envoie vraiment.

    uv run python chapitres/chapitre_1_demarrer.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                          # noqa: E402
from jobportal.agents import conseiller                # noqa: E402
from jobportal.modele import ModeleFactice, en_factice  # noqa: E402


class Espion(ModeleFactice):
    """Le meme modele, qui garde ce qu'on lui a envoye."""

    def invoke(self, messages=None, **kwargs):
        self.vu = list(messages or [])
        return super().invoke(messages=messages, **kwargs)


def main() -> None:
    console.utf8()

    print("1. TROIS LIGNES, UN AGENT\n")
    espion = Espion()
    resultat = conseiller(espion).run("Comment devenir ingenieur IA ?")
    print(f"   {resultat.content[:96]}")
    if en_factice():
        print("\n   (modele factice : la reponse est plausible mais vide de sens.")
        print("    Ce qui compte ici est CE QUI A ETE ENVOYE, ci-dessous.)")

    print("\n2. CE QUE L'AGENT A REELLEMENT ENVOYE\n")
    for message in espion.vu:
        contenu = str(message.content or "")
        print(f"   {message.role:<10}{len(contenu):>5} signes  {contenu[:52]!r}")
    total = sum(len(str(m.content or "")) for m in espion.vu)
    print(f"\n   {len(espion.vu)} message(s), {total} signes au total.")
    print("\n   Un agent « nu » envoie peu. Retenez ce chiffre : les chapitres")
    print("   suivants ajoutent des outils, un historique, des memoires et des")
    print("   connaissances — et chacun le fait grossir. Agno rend ces")
    print("   fonctions faciles a activer, pas gratuites.")

    print("\n3. CE QUE RENVOIE UN run()\n")
    for champ in ("content", "messages", "tools", "metrics"):
        valeur = getattr(resultat, champ, None)
        apercu = (f"{len(valeur)} element(s)" if isinstance(valeur, list)
                  else str(valeur)[:52])
        print(f"   {champ:<12}{apercu}")

    print("\n4. print_response() N'EST PAS run()\n")
    print("   print_response affiche dans un cadre et rend None.")
    print("   run rend un objet RunOutput, avec le contenu, les messages, les")
    print("   outils appeles et les metriques.")
    print("\n   La difference compte des qu'on sort de la demonstration : tout")
    print("   ce projet utilise run(), parce qu'on ne teste pas un affichage.")


if __name__ == "__main__":
    main()
