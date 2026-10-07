"""Chapitre 2 — Trace, span, generation : le troisieme change tout.

    uv run python chapitres/chapitre_2_traces.py
"""
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langfuse import observe                             # noqa: E402

from jobportal import console, donnees                   # noqa: E402
from jobportal.assistant import generer, repondre        # noqa: E402
from jobportal.collecteur import brancher                # noqa: E402


def main() -> None:
    console.utf8()
    client, collecteur = brancher()

    print("1. LE VOCABULAIRE, ET IL COMPTE\n")
    for mot, quoi in (
            ("trace", "une requete de bout en bout — l'unite qu'on regarde"),
            ("span", "une etape : une recherche, une validation, un appel HTTP"),
            ("generation", "un span SPECIAL : celui qui appelle un modele")):
        print(f"   {mot:<14}{quoi}")

    repondre("Quelles offres DevOps ?", "diaguily", "s-42")
    client.flush()
    print()
    for profondeur, o in collecteur.arbre():
        print(f"   {'  ' * profondeur}{o.nom:<22}{o.genre}")

    print("\n2. CE QU'UNE GENERATION PORTE EN PLUS\n")
    generation = collecteur.generations()[0]
    for cle in ("observation.model.name", "observation.usage_details"):
        print(f"   {cle:<32}{generation.metadonnees.get(cle, '—')}")
    print("\n   Le modele et l'usage. C'est a partir de la que Langfuse calcule")
    print("   le COUT, cote serveur, avec sa table de tarifs.")

    print("\n3. LE DEFAUT QUI SE VOIT DANS LA FACTURE, PAS DANS LA TRACE\n")
    collecteur.vider()

    @observe()                               # ← as_type oublie
    def generer_sans_type(question: str, docs: list[str]) -> str:
        client.update_current_generation(
            model="haiku", usage_details={"input": 30, "output": 20})
        return "reponse"

    generer_sans_type("x", ["a"])
    client.flush()
    oubli = collecteur.observations[0]
    print(f"   genre du span : {oubli.genre}")
    print(f"   porte-t-il le modele ? "
          f"{'oui' if 'observation.model.name' in oubli.attributs else 'NON'}")
    print("\n   Sans « as_type=\"generation\" », l'etape apparait bien dans la")
    print("   trace — au meme endroit, avec la meme duree. Elle n'entre")
    print("   simplement pas dans le tableau de bord des couts. On ne s'en")
    print("   apercoit qu'en comparant la facture du fournisseur au total")
    print("   affiche par Langfuse, souvent un mois plus tard.")

    print("\n4. user_id ET session_id NE SERVENT PAS A LA TRACE\n")
    collecteur.vider()
    repondre("Quelles offres Python ?", "diaguily", "s-42")
    repondre("Et en Java ?", "diaguily", "s-42")
    repondre("Bonjour", "autre-personne", "s-99")
    client.flush()
    racines = collecteur.racines
    print(f"   {len(racines)} traces enregistrees")
    print("\n   Ils servent a les RETROUVER : toutes les traces d'un candidat,")
    print("   tout le parcours d'une conversation. Sans eux, un tableau de")
    print("   bord montre des traces sans savoir de qui elles viennent — et")
    print("   l'on ne peut pas repondre a « qu'est-il arrive a cet")
    print("   utilisateur hier ? », qui est la question la plus frequente.")

    print("\n5. CE QUE CA COUTE, CALCULE ICI\n")
    total = 0.0
    for generation in collecteur.generations():
        usage = generation.metadonnees.get("observation.usage_details", "{}")
        import json
        u = json.loads(usage) if isinstance(usage, str) else {}
        prix = donnees.cout("haiku", u.get("input", 0), u.get("output", 0))
        total += prix
        print(f"   {u}  →  {prix * 1000:.4f} millieme d'euro")
    print(f"\n   total des {len(collecteur.generations())} generations : "
          f"{total * 1000:.4f} millieme d'euro")
    print("\n   Ridicule ici. A 100 000 requetes par jour, c'est la ligne qu'on")
    print("   regarde en premier — et elle n'existe que si les generations")
    print("   sont marquees comme telles.")


if __name__ == "__main__":
    main()
