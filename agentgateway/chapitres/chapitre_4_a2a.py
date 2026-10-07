"""Chapitre 4 — A2A et routage d'inférence : deux mécanismes, deux endroits.

    uv run python chapitres/chapitre_4_a2a.py

Le support présente A2A comme un type de backend et le routage d'inférence
comme une liste de signaux GPU. Les deux sont ailleurs, et savoir où change
ce qu'on écrit : A2A est une **politique de route**, l'inférence une
**politique de backend** qui délègue la décision à un service tiers.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import schema_publie                              # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    CONFIGS, EXEMPLES_AMONT, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import (                                   # noqa: E402
    FOURNISSEURS, TYPES_DE_BACKEND, charger, depuis_texte,
)

CORRIGE = """
binds:
- port: 3000
  listeners:
  - routes:
    # A2A : une politique sur la route, un backend ordinaire.
    - name: pair-analyste
      matches:
      - path:
          pathPrefix: /a2a
      policies:
        a2a: {}
      backends:
      - host: agent-analyste:8080
    # Inference : une politique sur le BACKEND, qui delegue le choix du
    # noeud a un Endpoint Picker externe.
    - name: modele-auto-heberge
      matches:
      - path:
          pathPrefix: /v1/chat/completions
      backends:
      - service:
          name: default/vllm
          port: 8000
        policies:
          inferenceRouting:
            endpointPicker:
              host: 127.0.0.1:9002
            destinationMode: passthrough
services:
- name: vllm
  namespace: default
  hostname: vllm
  vips: []
  ports:
    8000: 8000
"""


def principal() -> None:
    utf8()

    titre(1, "LA CONFIGURATION DU SUPPORT, PASSEE AU SCHEMA")
    du_cours = charger(CONFIGS / "du-cours" / "ch4-a2a-et-inference.yaml")
    erreurs = schema_publie.verifier(du_cours)
    ligne("erreurs", str(len(erreurs)), 26)
    print()
    for chemin, message in erreurs:
        print(f"      {chemin}")
        print(f"        {message.split('  [dans')[0]}")
    print()
    for l in plier(
        "Deux idees justes, deux ecritures qui n'existent pas. Le reste du "
        "chapitre cherche ou elles vivent vraiment."):
        print(f"   {l}")

    titre(2, "LES DIX TYPES DE BACKEND, ET CE QUI N'EN EST PAS UN")
    tableau(["branche de LocalRouteBackend", "remarque"],
            [[t, "le support y attend aussi « a2a »" if t == "ai" else ""]
             for t in TYPES_DE_BACKEND], [32, 40])
    print()
    ligne("« a2a » est-il un backend ?",
          "oui" if "a2a" in TYPES_DE_BACKEND else "NON", 34)
    ligne("« a2a » est-il une politique de route ?",
          "oui" if "a2a" in schema_publie.definitions()["FilterOrPolicy"]
          ["properties"] else "non", 40)
    print()
    print("   `amont/exemples/traffic-a2a.yaml`, tel quel :\n")
    for ligne_ in (EXEMPLES_AMONT / "traffic-a2a.yaml") \
            .read_text(encoding="utf-8").splitlines()[5:]:
        print(f"      {ligne_}")
    print()
    for l in plier(
        "Le commentaire du fichier amont dit tout : « Mark this route as a2a "
        "traffic ». `a2a: {}` est un drapeau vide — il ne designe aucune "
        "destination. La destination reste un backend ordinaire, ici "
        "`host: localhost:9999`. La politique dit au proxy COMMENT lire le "
        "trafic, pas OU l'envoyer."):
        print(f"   {l}")

    titre(3, "LE ROUTAGE D'INFERENCE N'EST PAS UNE LISTE DE SIGNAUX")
    ligne("« selfHosted » est-il un fournisseur ?",
          "oui" if "selfHosted" in FOURNISSEURS else "NON — les huit sont "
          + ", ".join(FOURNISSEURS[:3]) + "…", 40)
    print()
    print("   `amont/exemples/llm-standalone-epp.yaml`, la partie qui compte :\n")
    epp = charger(EXEMPLES_AMONT / "llm-standalone-epp.yaml")
    backend = epp.routes()[0].backends[0]
    print(f"      backend      : {backend.get('service')}")
    print(f"      policies     : {backend.get('policies')}")
    print()
    politique = schema_publie.definitions().get("InferenceRouting", {})
    for champ, corps in politique.get("properties", {}).items():
        for l in plier(f"{champ} — {' '.join((corps.get('description') or '').split())}",
                       62):
            print(f"      {l}")
    print()
    phrase = next(l for l in (EXEMPLES_AMONT.parent / "README.md")
                  .read_text(encoding="utf-8").splitlines()
                  if "GPU utilization" in l)
    for l in plier(" ".join(phrase.split()).strip("*- "), 62):
        print(f"      {l}")
    print()
    for l in plier(
        "Les signaux du support sont donc REELS — le README amont les nomme. "
        "Ce qui ne l'est pas, c'est l'endroit : ils appartiennent aux "
        "« Kubernetes Inference Gateway extensions », pas a un champ de cette "
        "configuration."):
        print(f"   {l}")
    print()
    for l in plier(
        "`endpointPicker.host` est l'adresse d'un SERVICE TIERS. C'est lui "
        "qui lit `gpuUtilization`, l'etat du cache KV et la profondeur des "
        "files — agentgateway lui demande simplement « quel noeud ? » et "
        "route vers la reponse. La decision est prise ailleurs, et "
        "agentgateway ne fait que l'appliquer."):
        print(f"   {l}")

    titre(4, "LA VERSION CORRIGEE")
    corrige = depuis_texte(CORRIGE, "corrige")
    erreurs = schema_publie.verifier(corrige)
    ligne("erreurs du schema", str(len(erreurs)), 30)
    for chemin, message in erreurs[:3]:
        print(f"      {chemin} — {message[:80]}")
    ligne("routes", str(len(corrige.routes())), 30)
    print()
    tableau(["route", "politiques de route", "backend", "politiques de backend"],
            [[r.nom, ", ".join(sorted(r.politiques)) or "(aucune)",
              corrige.type_de_backend(r.backends[0]) if r.backends else "(aucun)",
              ", ".join(sorted((r.backends[0].get("policies") or {})))
              if r.backends else ""]
             for r in corrige.routes()], [22, 22, 12, 26])
    print()
    for l in plier(
        "Deux routes, deux etages de politique. La premiere pose `a2a` sur la "
        "ROUTE ; la seconde pose `inferenceRouting` sur le BACKEND. Cette "
        "difference d'un cran d'indentation est la seule chose a retenir du "
        "chapitre — et c'est celle qu'un exemple mal recopie efface."):
        print(f"   {l}")

    titre(5, "OU S'ATTACHE QUOI")
    tableau(["etage", "ce qu'on y pose", "exemple"], [
        ["frontendPolicies", "tout le trafic du proxy", "accessLog, http"],
        ["bind / listener", "un port, un protocole", "port, tls"],
        ["route.policies", "une route entiere",
         "jwtAuth, cors, a2a, mcpAuthorization"],
        ["backend.policies", "UNE destination",
         "backendTLS, inferenceRouting, backendAuth"],
    ], [20, 28, 40])
    print()
    for l in plier(
        "Un meme nom peut exister a deux etages et ne pas vouloir dire la "
        "meme chose : `policies` sur une route s'applique avant le choix du "
        "backend, `policies` sur un backend apres. Poser une authentification "
        "sur le backend plutot que sur la route, c'est authentifier apres "
        "avoir choisi ou envoyer — ce qui marche, et ne protege pas le choix."):
        print(f"   {l}")

    titre(6, "CE QUE CE CHAPITRE NE PEUT PAS MONTRER")
    for limite in [
        "aucun agent pair ne repond : `a2a: {}` marque un trafic que ce",
        "  projet ne fait pas circuler ;",
        "aucun Endpoint Picker ne tourne : le protocole entre agentgateway",
        "  et l'EPP n'est pas dans `amont/`, donc rien n'en est mesure ;",
        "les signaux GPU ne sont ni lus ni simules — ils appartiennent a",
        "  l'EPP, pas au proxy.",
    ]:
        print(f"   {limite}" if limite.startswith("  ") else f"   · {limite}")
    print()
    for l in plier(
        "Ce qui EST etabli tient en deux lignes du schema publie : `a2a` est "
        "dans `FilterOrPolicy`, pas dans les branches de `LocalRouteBackend` ; "
        "et `selfHosted` n'est pas dans `AIProvider`. Les deux se verifient "
        "sans rien lancer."):
        print(f"   {l}")

    print("\n   Au chapitre suivant : authentifier, autoriser, filtrer.\n")


if __name__ == "__main__":
    principal()
