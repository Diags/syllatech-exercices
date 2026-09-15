"""Chapitre 1 — La structure d'un prompt.

Rôle, tâche, contraintes, format. Ce chapitre ne se contente pas de le dire :
il montre ce qu'un prompt structuré permet que le prompt nu ne permet pas —
être VERIFIE.

    uv run python chapitres/chapitre_1_structure.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                      # noqa: E402

NU = "Donne un avis sur cette offre."

STRUCTURE = """Tu es conseiller carriere pour syllatech.

## Tache
Analyse l'offre et donne un avis au candidat.

## Contraintes
- Fonde-toi UNIQUEMENT sur les infos fournies
- Si une info manque, dis-le explicitement

## Format de sortie (JSON)
{"avis": str, "risque": int (0-10), "manques": [str]}"""


SECTIONS = {
    "role": ("Tu es", "qui parle — fixe le registre et le point de vue"),
    "tache": ("## Tache", "ce qu'on demande — une seule chose, clairement"),
    "contraintes": ("## Contraintes", "ce qui est interdit — la partie qu'on oublie"),
    "format": ("## Format", "la forme de la sortie — ce qui la rend verifiable"),
}


def analyser(prompt: str) -> dict[str, bool]:
    return {nom: marque in prompt for nom, (marque, _) in SECTIONS.items()}


def main() -> None:
    console.utf8()
    for nom, prompt in (("Prompt nu", NU), ("Prompt structuré", STRUCTURE)):
        presence = analyser(prompt)
        note = sum(presence.values())
        print(f"\n{nom} — {note}/4 sections, {len(prompt)} signes")
        for cle, (_, role) in SECTIONS.items():
            coche = "✓" if presence[cle] else "·"
            print(f"   {coche} {cle:<12} {role}")

    print("\nLa section qui change tout est la dernière.")
    print("Un prompt sans format de sortie donne du texte : on ne peut que le")
    print("lire. Avec un format, la sortie devient une DONNEE — on peut la")
    print("valider, la tester, la stocker, et détecter une régression.")
    print("\nC'est tout l'objet du chapitre 4 : sorties structurées.")
    print("Et c'est ce qui rend le chapitre 6 possible : sans sortie")
    print("verifiable, aucun score, donc aucune amélioration mesurable.")


if __name__ == "__main__":
    main()
