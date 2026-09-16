"""Chapitre 4 — Les prompts versionnes, et ce que ca deplace.

    uv run python chapitres/chapitre_4_prompts.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console                                  # noqa: E402
from jobportal.prompts import Depot, PromptIntrouvable          # noqa: E402


def main() -> None:
    console.utf8()
    depot = Depot()

    print("1. LA FORME REELLE\n")
    print("     prompt = get_client().get_prompt(\"assistant-carriere\",")
    print("                                       label=\"production\")")
    print("     texte  = prompt.compile(portail=\"syllatech\")")
    print("\n   ⚠️ get_prompt interroge l'API : il faut un serveur Langfuse.")
    print("   Ce chapitre implemente le MEME contrat en local — versions,")
    print("   labels, compilation — pour que le mecanisme soit mesurable.")

    print("\n2. TROIS VERSIONS, UN LABEL\n")
    depot.publier("assistant-carriere",
                  "Tu conseilles les candidats de {{portail}}.")
    depot.publier("assistant-carriere",
                  "Tu es le conseiller carriere de {{portail}}. Sois bref.")
    depot.publier("assistant-carriere",
                  "Tu es le conseiller carriere de {{portail}}. Cite toujours "
                  "les offres par leur intitule.",
                  labels={"production"})
    for version in depot.versions("assistant-carriere"):
        etiquettes = ", ".join(sorted(version.labels)) or "—"
        print(f"   v{version.numero}  [{etiquettes:<12}] {version.texte[:56]}")

    print("\n3. CHANGER DE PROMPT = DEPLACER UN LABEL\n")
    avant = depot.get_prompt("assistant-carriere").numero
    depot.etiqueter("assistant-carriere", 2, "production")
    apres = depot.get_prompt("assistant-carriere").numero
    print(f"   production : v{avant} → v{apres}")
    print("\n   AUCUN redeploiement applicatif. C'est l'argument central du")
    print("   chapitre — et c'est aussi le danger central : un prompt qui")
    print("   change sans passer par la revue de code change le comportement")
    print("   de la production sans aucune trace dans git.")
    depot.etiqueter("assistant-carriere", 3, "production")

    print("\n4. LA COMPILATION, ET SON PIEGE\n")
    prompt = depot.get_prompt("assistant-carriere")
    print(f"   variables attendues : {sorted(prompt.variables)}")
    print(f"   compile(portail=…)  : {prompt.compile(portail='syllatech')[:62]}")
    oubli = prompt.compile()
    print(f"   compile() sans rien : {oubli[:62]}")
    print("\n   « {{portail}} » part TEL QUEL au modele. Aucune erreur — juste")
    print("   un prompt qui parle d'une variable au lieu de sa valeur, et un")
    print("   modele qui fait de son mieux avec.")

    print("\n5. LE LABEL QUI N'EXISTE PAS\n")
    try:
        depot.get_prompt("assistant-carriere", label="staging")
    except PromptIntrouvable as souci:
        print(f"   PromptIntrouvable : {souci}")
    print("\n   En production, le SDK sert alors son CACHE si le reseau echoue")
    print("   — c'est voulu, et c'est le bon compromis : mieux vaut un prompt")
    print("   perime qu'un service arrete. Mais il faut le savoir, sinon on")
    print("   deploie une v4 qui n'arrive jamais et l'on cherche pourquoi.")

    print("\n6. CE QU'IL FAUT GARDER DANS GIT QUAND MEME\n")
    for quoi, pourquoi in (
            ("le nom du prompt", "c'est une dependance du code, comme une URL"),
            ("les variables attendues", "un renommage casse la compilation"),
            ("un prompt de repli", "si Langfuse est injoignable au demarrage"),
            ("le label utilise", "« production » ou « staging » est un choix de code")):
        print(f"   {quoi:<26}{pourquoi}")


if __name__ == "__main__":
    main()
