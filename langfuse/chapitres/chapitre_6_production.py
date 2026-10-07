"""Chapitre 6 — L'integration complete, et ce qu'elle coute.

    uv run python chapitres/chapitre_6_production.py
"""
from __future__ import annotations

import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import console, donnees                      # noqa: E402
from jobportal.assistant import repondre                    # noqa: E402
from jobportal.collecteur import brancher                   # noqa: E402
from jobportal.evaluation import JEU_METIER, Registre, score_regle  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    console.utf8()
    client, collecteur = brancher()
    registre = Registre()

    print("1. LA CHAINE COMPLETE\n")
    for ligne in (
            "Utilisateur → application (assistant carriere)",
            "                │  OTEL → Langfuse   (les etapes, votre logique)",
            "                ▼",
            "            proxy LiteLLM",
            "                │  callback → Langfuse   (les couts, exacts)",
            "                ▼",
            "            Claude / GPT / local"):
        print(f"   {ligne}")

    print("\n2. UNE JOURNEE, SIMULEE\n")
    utilisateurs = ["diaguily", "marie", "paul", "diaguily", "marie"]
    for n, (cas, utilisateur) in enumerate(zip(JEU_METIER, utilisateurs)):
        texte = repondre(cas.entree, utilisateur, f"s-{utilisateur}")
        registre.create_score(trace_id=f"t-{n}", name="regle",
                              value=score_regle(texte, cas.attendu))
    client.flush()

    generations = collecteur.generations()
    total = 0.0
    for generation in generations:
        usage = json.loads(
            generation.metadonnees.get("observation.usage_details", "{}"))
        total += donnees.cout("haiku", usage.get("input", 0),
                              usage.get("output", 0))
    print(f"   {len(collecteur.racines)} traces")
    print(f"   {len(generations)} generations")
    print(f"   {len(registre.scores)} scores, moyenne {registre.moyenne('regle'):.0%}")
    print(f"   cout total : {total * 1000:.3f} millieme d'euro")

    print("\n3. LES QUATRE TABLEAUX QUI SERVENT\n")
    for tableau, question in (
            ("couts", "qui depense quoi, et depuis quand ?"),
            ("qualite", "la moyenne des scores baisse-t-elle ?"),
            ("prompts", "quelle version est en production, depuis quand ?"),
            ("sessions", "qu'est-il arrive a CE candidat, hier ?")):
        print(f"   {tableau:<12}{question}")
    print("\n   Le quatrieme est celui qu'on utilise vraiment. Les trois")
    print("   premiers se regardent une fois par semaine ; le quatrieme sert")
    print("   chaque fois que quelqu'un se plaint — et c'est le seul qui ne")
    print("   marche pas si l'on a oublie user_id et session_id.")

    print("\n4. CE QUE L'OBSERVABILITE COUTE\n")
    signes = sum(len(str(o.attributs)) for o in collecteur.observations)
    print(f"   {len(collecteur.observations)} spans, ~{signes} signes d'attributs")
    print("\n   Les entrees et les sorties sont stockees EN ENTIER. Sur un RAG")
    print("   qui passe 20 documents au modele, chaque trace pese ces 20")
    print("   documents. C'est ce qui fait exploser le stockage, bien avant le")
    print("   nombre de traces.")
    print("\n   Deux leviers : l'echantillonnage (garder 10 %, mais 100 % des")
    print("   erreurs) et le masquage — `Langfuse(mask=...)` remplace ce qu'on")
    print("   ne veut ni stocker ni voir.")

    print("\n5. CE QU'IL NE FAUT PAS TRACER\n")
    for quoi, pourquoi in (
            ("les donnees personnelles", "une trace est une base de donnees de plus"),
            ("les secrets dans les prompts", "ils apparaissent en clair dans l'interface"),
            ("les documents entiers", "le stockage suit, la lisibilite non"),
            ("chaque boucle interne", "mille spans par trace : plus personne ne lit")):
        print(f"   {quoi:<32}{pourquoi}")
    print("\n   Un trace est lu par tous ceux qui ont acces a Langfuse. La")
    print("   question n'est pas « est-ce utile ? » mais « qui a le droit de")
    print("   voir ca ? ».")

    print("\n6. LES VERSIONS\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   Langfuse 3.x est une reecriture sur OpenTelemetry : la 2.x")
    print("   avait sa propre file d'evenements et ses propres objets. Le code")
    print("   d'un article de 2024 ne se transpose donc pas ligne a ligne.")


if __name__ == "__main__":
    main()
