"""Chapitre 2 — LLM Gateway : une API, et trois façons de choisir le modèle.

    uv run python chapitres/chapitre_2_llm.py

Le support annonce « budgets, load balancing et failover se règlent au
proxy ». C'est vrai, et le schéma dit **où** — pas là où le support le
montre. Ce chapitre passe sa configuration au schéma publié, puis évalue
pour de bon les trois formes de routage d'un modèle virtuel.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import modeles, schema_publie                     # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    CONFIGS, EXEMPLES_AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import FOURNISSEURS, charger, depuis_texte  # noqa: E402


CORRIGE = """
binds:
- port: 3000
  listeners:
  - routes:
    - matches:
      - path:
          pathPrefix: /v1
      backends:
      - ai:
          name: claude
          provider:
            anthropic:
              model: claude-sonnet-5
"""


def principal() -> None:
    utf8()

    titre(1, "LA CONFIGURATION DU SUPPORT, PASSEE AU SCHEMA")
    du_cours = charger(CONFIGS / "du-cours" / "ch2-llm-deux-fournisseurs.yaml")
    erreurs = schema_publie.verifier(du_cours)
    ligne("erreurs", str(len(erreurs)), 26)
    print()
    for chemin, message in erreurs:
        print(f"      {chemin}")
        print(f"        {message.split('  [dans')[0]}")
    print()
    for l in plier(
        "Trois refus, et aucun n'est cosmetique : `agentgateway --file` ne "
        "demarrerait pas. Les deux premiers se corrigent en une ligne ; le "
        "troisieme demande de savoir ou vit vraiment la bascule."):
        print(f"   {l}")

    titre(2, "`match` N'EXISTE PAS, `matches` EST UNE LISTE")
    tableau(["ce que le support ecrit", "ce que le schema declare"], [
        ["match: { path: /v1 }", "matches: [ {path: {pathPrefix: /v1}} ]"],
        ["(un objet)", "(une liste de RouteMatch)"],
        ["(un chemin en chaine)", "exact | pathPrefix | regex"],
    ], [32, 46])
    print()
    corrige = depuis_texte(CORRIGE, "corrige")
    ligne("la version corrigee passe-t-elle ?",
          "oui" if not schema_publie.verifier(corrige) else "NON", 38)
    print()
    for l in plier(
        "La liste n'est pas un detail de syntaxe : plusieurs `matches` sur "
        "une route sont un OU. C'est ainsi qu'une route attrape a la fois "
        "`/v1/chat` et `/v1/completions` sans devenir un prefixe trop large."):
        print(f"   {l}")

    titre(3, "HUIT FOURNISSEURS, ET UNE MAJUSCULE")
    tableau(["cle du schema", "ce que le support ecrit"],
            [[f, "openai — refuse" if f == "openAI" else ""]
             for f in FOURNISSEURS], [20, 30])
    print()
    for l in plier(
        "`openAI` avec un I majuscule. Ce genre de faute est le pire cas "
        "d'une configuration : elle se relit sans rien voir, et le message du "
        "proxy dit « additional properties are not allowed », pas « vous "
        "vouliez dire openAI »."):
        print(f"   {l}")

    titre(4, "DEUX BACKENDS `ai` SUR UNE ROUTE : CE QUE CELA FAIT")
    print("   LocalRouteBackend porte un champ `weight` :\n")
    poids = schema_publie.definitions()["LocalRouteBackend"]["properties"]["weight"]
    for l in plier(poids["description"], 62):
        print(f"      {l}")
    ligne("      defaut", str(poids.get("default")), 26)
    print()
    for l in plier(
        "Deux backends sur une route, c'est donc une REPARTITION 50/50, pas "
        "une bascule : les deux fournisseurs recoivent du trafic en "
        "permanence. Le support appelle le second « secours » ; le proxy, "
        "lui, lui envoie la moitie des requetes."):
        print(f"   {l}")

    titre(5, "OU VIT VRAIMENT LA BASCULE")
    routage = schema_publie.definitions()["LocalLLMVirtualModelRouting"]
    for nom in ("weighted", "failover", "conditional"):
        texte = routage["properties"][nom]["description"].split(".")[0]
        ligne(f"llm.virtualModels[].routing.{nom}", "", 42)
        for l in plier(texte, 58):
            print(f"        {l}")
    print()
    for l in plier(
        "Trois formes, trois semantiques ecrites noir sur blanc — et la "
        "troisieme est la seule qui regarde la requete. Les trois vivent sous "
        "`llm.virtualModels`, pas dans les backends d'une route."):
        print(f"   {l}")

    titre(6, "LES TROIS FORMES, SUR LE CATALOGUE DU PORTAIL")
    portail = charger(PORTAIL / "02-llm.yaml")
    ligne("erreurs du schema", str(len(schema_publie.verifier(portail))), 30)
    ligne("modeles declares",
          ", ".join(modeles.modeles_declares(portail)), 30)
    ligne("modeles virtuels",
          ", ".join(m["name"] for m in modeles.modeles_virtuels(portail)), 30)
    print()
    for virtuel in modeles.modeles_virtuels(portail):
        forme = next(iter(virtuel["routing"]))
        print(f"   {virtuel['name']}  —  {forme}")
        tableau(["  cible", "  contrat"],
                [[f"  {m}", f"  {c}"]
                 for m, c in modeles.repartition(virtuel["routing"])],
                [22, 56])
        print()

    titre(7, "LE ROUTAGE CONDITIONNEL, EVALUE POUR DE BON")
    virtuel = next(m for m in modeles.modeles_virtuels(portail)
                   if "conditional" in m["routing"])
    print("   Chaque ligne est une vraie evaluation CEL, pas une comparaison")
    print("   de chaines : `cel-python` compile l'expression et l'applique.\n")
    cas = [
        ("urgence haute, 4000 jetons",
         {"llmRequest": {"metadata": {"urgence": "haute"}, "max_tokens": 4000}}),
        ("sans metadonnee, 200 jetons",
         {"llmRequest": {"max_tokens": 200}}),
        ("sans metadonnee, 4000 jetons",
         {"llmRequest": {"max_tokens": 4000}}),
        ("requete vide",
         {"llmRequest": {}}),
    ]
    tableau(["requete", "modele choisi", "par quelle regle"],
            [[etiquette] + _decider(virtuel["routing"], contexte)
             for etiquette, contexte in cas], [30, 16, 40])
    print()
    for l in plier(
        "La derniere ligne est celle qui compte. `llmRequest` vide : ni "
        "`metadata`, ni `max_tokens`. Les deux conditions commencent par "
        "`has(...)`, donc elles s'evaluent quand meme — et le repli prend. "
        "Sans `has(...)`, l'expression LEVERAIT au lieu de rendre faux, et le "
        "chapitre 5 montre ce que cela fait a une regle de securite."):
        print(f"   {l}")

    titre(8, "CE QUE CE PROJET NE PEUT PAS EVALUER")
    amont_cout = charger(EXEMPLES_AMONT / "llm-cost-routing.yaml")
    virtuel_amont = modeles.modeles_virtuels(amont_cout)[0]
    expression = virtuel_amont["routing"]["conditional"]["targets"][0]["when"]
    print("   La meme idee, dans `amont/exemples/llm-cost-routing.yaml` :")
    print()
    for l in plier(expression, 62):
        print(f"      {l}")
    print()
    ligne("fonctions hors CEL standard",
          ", ".join(modeles.extensions_utilisees(expression)), 34)
    try:
        modeles.evaluer(expression, {"llmRequest": {}})
        verdict = "evaluee"
    except modeles.ErreurDeCEL as erreur:
        verdict = str(erreur)[:52]
    ligne("ce que ce projet en fait", verdict, 34)
    print()
    for l in plier(
        "`default` et `coalesce` ne sont pas du CEL : agentgateway les AJOUTE, "
        "et `amont/cel-functions.md` en documente vingt-cinq. `cel-python` "
        "n'implemente que le standard. Ce projet le dit plutot que de deviner "
        "— un verificateur qui evalue de travers est pire qu'un verificateur "
        "qui s'abstient."):
        print(f"   {l}")

    titre(9, "CE QUI NE SE VOIT PAS DANS LA FICHE D'UN MODELE")
    tableau(["modele", "visibility", "ce que cela veut dire"],
            [[nom, modeles.visibilite(portail, nom),
              "demandable directement" if modeles.visibilite(portail, nom)
              == "(defaut)" else "seulement via un modele virtuel"]
             for nom in modeles.modeles_declares(portail)], [18, 14, 40])
    print()
    port = schema_publie.definitions()["LocalLLMConfig"]["properties"]["port"]
    ligne("llm.port, dans le schema",
          " ".join(port["description"].split()), 30)
    print()
    for l in plier(
        "Deux details qui evitent une mauvaise surprise : un modele "
        "`internal` ne peut pas etre demande par son nom — c'est ce qui "
        "empeche une application de contourner le modele virtuel et sa "
        "politique de cout ; et `llm.port` est marque deprecie dans le "
        "schema, au profit de `gateways`."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : federer des serveurs MCP.\n")


def _decider(routage, contexte) -> list[str]:
    try:
        decision = modeles.choisir(routage, contexte)
        return [decision.modele, decision.regle[:38]]
    except modeles.ErreurDeCEL as erreur:
        return ["(aucun)", f"ERREUR {str(erreur)[:30]}"]


if __name__ == "__main__":
    principal()
