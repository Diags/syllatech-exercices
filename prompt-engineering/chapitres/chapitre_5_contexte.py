"""Chapitre 5 — Context engineering : la fenêtre est une ressource.

Deux décisions, et elles se mesurent : dans quel ORDRE on empile, et ce
qu'on FAIT quand ça déborde.

    uv run python chapitres/chapitre_5_contexte.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees              # noqa: E402

SEUIL = 600          # en signes, pour l'exemple ; en jetons dans la vraie vie
GARDES = 4           # les N derniers tours restent intacts

INSTRUCTIONS = "Tu es conseiller carriere. Fonde-toi uniquement sur le contexte."


def taille(messages: list[dict]) -> int:
    return sum(len(m["content"]) for m in messages)


def resumer(tours: list[dict]) -> dict:
    """Un vrai resumé passerait par le modèle. Ici on compte, ce qui suffit
    à montrer la mécanique — et ce qui a le mérite d'être déterministe."""
    return {"role": "system",
            "content": f"[résumé de {len(tours)} tours antérieurs, "
                       f"{sum(len(t['content']) for t in tours)} signes]"}


def compacter(historique: list[dict]) -> tuple[list[dict], bool]:
    if taille(historique) <= SEUIL or len(historique) <= GARDES:
        return historique, False
    return [resumer(historique[:-GARDES])] + historique[-GARDES:], True


def main() -> None:
    console.utf8()
    contexte = "\n".join(o["titre"] + " — " + o["lieu"] for o in donnees.query(""))

    messages = [
        {"role": "system", "content": INSTRUCTIONS},           # 1. les règles
        {"role": "system", "content": "[résumé de la conversation]"},   # 2. le résumé
        {"role": "user", "content": contexte},                 # 3. les sources
        {"role": "user", "content": "Quelle offre pour un profil Python ?"},  # 4. la question
    ]
    print("L'ordre qui marche, et pourquoi :\n")
    raisons = ["les règles d'abord : elles cadrent tout ce qui suit",
               "le résumé ensuite : l'état de la conversation",
               "les sources après : volumineuses, et sans autorité propre",
               "la question EN DERNIER : c'est ce dont le modèle se souvient le mieux"]
    for m, r in zip(messages, raisons):
        print(f"   {m['role']:<7} {len(m['content']):>4} signes   {r}")

    print("\nQuand l'historique gonfle :\n")
    historique = [{"role": "user", "content": f"tour {i} : " + "blabla " * 12}
                  for i in range(1, 11)]
    print(f"   avant   : {len(historique):>2} messages, {taille(historique)} signes")
    compacte, agi = compacter(historique)
    print(f"   après   : {len(compacte):>2} messages, {taille(compacte)} signes"
          f"   (compaction {'faite' if agi else 'inutile'})")
    print(f"   gardés  : les {GARDES} derniers tours, intacts")
    print(f"   résumé  : {compacte[0]['content']}")

    print("\nPourquoi garder les derniers tours INTACTS : un résumé perd les")
    print("détails, et ce sont justement les derniers échanges qui portent la")
    print("demande en cours. Résumer tout l'historique fait oublier au modèle")
    print("ce qu'on vient de lui dire — le symptôme classique de la")
    print("conversation qui « perd le fil » après vingt tours.")


if __name__ == "__main__":
    main()
