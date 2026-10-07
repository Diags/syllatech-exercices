"""Chapitre 1 — Démarrer avec agentgateway.

    uv run python chapitres/chapitre_1_demarrer.py

agentgateway est un proxy écrit en Rust. Ce projet ne le lance pas : il lit
des configurations, et il les valide avec **le schéma que le proxy publie
lui-même**. Tout ce que ce chapitre affirme sur la grammaire se lit dans
`amont/config.schema.json` ou dans les 27 configurations d'exemple du dépôt.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collections import Counter                                  # noqa: E402

from jobportal import schema_publie                              # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    CONFIGS, EXEMPLES_AMONT, PORTAIL, SCHEMA, ligne, plier, tableau,
    titre, utf8,
)
from jobportal.config import (                                   # noqa: E402
    CORRESPONDANCE_PAR_DEFAUT, SECTIONS, charger, charger_dossier,
)
from jobportal.routage import Requete, candidates                # noqa: E402


def principal() -> None:
    utf8()

    titre(1, "CE QUI EST INSTALLE, ET CE QUI NE L'EST PAS")
    schema = schema_publie.document()
    for quoi, etat in [
        ("agentgateway (le proxy Rust)", "absent — un binaire, ou une image"),
        ("un backend LLM", "absent — il faudrait une cle d'API"),
        ("un serveur MCP", "absent — il faudrait npx et du reseau"),
        ("le schema de configuration publie",
         f"{SCHEMA.stat().st_size // 1024} Kio, {len(schema['$defs'])} definitions"),
        ("les configurations d'exemple",
         f"{len(list(EXEMPLES_AMONT.glob('*.yaml')))} fichiers du depot"),
    ]:
        ligne(quoi, etat, 34)
    print()
    for l in plier(
        "Le schema n'est pas une piece justificative : c'est LE verificateur. "
        "Le `schema/README.md` amont le presente ainsi — « The schema for the "
        "configuration file (passed with `--file` to agentgateway) » — et "
        "c'est du JSON Schema 2020-12. Valider une configuration ici, c'est "
        "donc faire ce que le proxy fait au demarrage, sans le demarrer."):
        print(f"   {l}")

    titre(2, "QUATORZE SECTIONS, DONT UNE QUE LE COURS ENSEIGNE")
    racine = schema["properties"]
    tableau(["section", "ce que le schema en dit"],
            [[s, (racine[s].get("description") or "").split(".")[0]
              .replace("\n", " ")[:58]] for s in SECTIONS], [20, 62])
    print()
    for l in plier(
        "`binds` porte sa propre mise en garde : « the LOW-LEVEL API for "
        "configuring the proxy ». C'est pourtant la grammaire du cours — bind "
        "→ listener → route → backend — et c'est un bon choix : c'est celle "
        "qui montre ou les politiques s'attachent. Les raccourcis `llm:` et "
        "`mcp:` font la meme chose en moins de lignes, et cachent la "
        "structure."):
        print(f"   {l}")

    titre(3, "CE QUE LES EXEMPLES DU DEPOT UTILISENT VRAIMENT")
    compte: Counter[str] = Counter()
    configs = charger_dossier(EXEMPLES_AMONT)
    for config in configs:
        compte.update(config.sections)
    tableau(["section", "exemples qui l'utilisent", "part"],
            [[s, str(n), f"{n / len(configs):.0%}"]
             for s, n in compte.most_common(7)], [22, 26, 10])
    print()
    ligne("configurations d'exemple", str(len(configs)), 34)
    ligne("acceptees par le schema publie",
          str(sum(1 for c in configs if not schema_publie.verifier(c))), 34)
    print()
    for l in plier(
        "Les 27 passent. C'est ce qui rend l'outil credible quand il refuse "
        "une configuration : il ne refuse pas ce que le projet amont publie."):
        print(f"   {l}")

    titre(4, "LE PROXY MINIMAL DU SUPPORT, PASSE AU SCHEMA")
    doc = charger(CONFIGS / "du-cours" / "ch1-mcp-minimal.yaml")
    print("   configs/du-cours/ch1-mcp-minimal.yaml :\n")
    for l in (CONFIGS / "du-cours" / "ch1-mcp-minimal.yaml") \
            .read_text(encoding="utf-8").splitlines()[2:]:
        print(f"      {l}")
    print()
    erreurs = schema_publie.verifier(doc)
    ligne("erreurs du schema publie", str(len(erreurs)), 34)
    ligne("ports ouverts", ", ".join(str(p) for p in doc.ports()), 34)
    ligne("routes", str(len(doc.routes())), 34)
    print()
    for l in plier(
        "Il passe. Le chapitre 1 du support est exact — et c'est le seul des "
        "cinq. Les chapitres 2 a 5 mesurent les autres."):
        print(f"   {l}")

    titre(5, "LE DEFAUT QUI N'EST ECRIT NULLE PART")
    ligne("LocalRoute.matches, defaut du schema",
          str(schema_publie.defaut("LocalRoute", "matches")), 38)
    ligne("ce que ce projet applique", str(CORRESPONDANCE_PAR_DEFAUT), 38)
    print()
    route = doc.routes()[0]
    ligne("la route du support ecrit-elle `matches` ?",
          "non" if not route.correspondances_ecrites else "oui", 42)
    print()
    print("   Ce qu'elle attrape, alors :\n")
    for chemin in ["/mcp", "/v1/chat/completions", "/", "/admin/tout-casser"]:
        prises = candidates(doc, Requete(chemin))
        ligne(f"  GET {chemin}", "PREND" if prises else "passe", 38)
    print()
    for l in plier(
        "Une route qui ne dit rien attrape tout. Ce n'est pas un piege du "
        "cours : c'est le defaut declare par le schema, et il est raisonnable "
        "pour un proxy a une seule route. Il cesse de l'etre a la deuxieme — "
        "et rien dans le fichier ne le montre, parce que la ligne qui le dit "
        "n'y est pas."):
        print(f"   {l}")

    titre(6, "LA MEME CHOSE, ECRITE POUR LE PORTAIL")
    portail = charger(PORTAIL / "01-mcp.yaml")
    ligne("erreurs du schema", str(len(schema_publie.verifier(portail))), 34)
    ligne("routes", str(len(portail.routes())), 34)
    ligne("la route ecrit-elle `matches` ?",
          "oui" if portail.routes()[0].correspondances_ecrites else "non", 34)
    print()
    for chemin in ["/mcp", "/mcp/tools", "/v1/chat", "/mcpvoisin"]:
        prises = candidates(portail, Requete(chemin))
        ligne(f"  GET {chemin}",
              "PREND" if prises else "passe — aucune route", 38)
    print()
    for l in plier(
        "La derniere ligne merite un mot : `/mcpvoisin` ne correspond PAS a "
        "`pathPrefix: /mcp`. Un prefixe de la Gateway API est un prefixe de "
        "SEGMENT, pas de chaine. Le schema ne le precise pas ; ce projet "
        "applique la convention et la fixe dans `tests/test_routage.py`, pour "
        "qu'elle puisse se contester."):
        print(f"   {l}")

    titre(7, "CE QUE LE PROJET VA MESURER")
    for quoi, ou in [
        ("`match` au lieu de `matches`, et `openai` au lieu de `openAI`",
         "chapitre 2"),
        ("ou vivent vraiment budgets, bascule et repartition", "chapitre 2"),
        ("les quatre facons d'atteindre un serveur MCP", "chapitre 3"),
        ("le prefixage des noms d'outils, et ce qu'il casse", "chapitre 3"),
        ("A2A n'est pas un backend, et l'inference n'est pas un signal",
         "chapitre 4"),
        ("`mode: optional` — le defaut qui laisse passer sans jeton",
         "chapitre 5"),
        ("les regles CEL, evaluees pour de bon", "chapitre 5"),
        ("ce qu'un guardrail regex rate, compte sur un corpus", "chapitre 5"),
        ("ce que repointer une base URL change, et ne change pas",
         "chapitre 6"),
    ]:
        print(f"   {quoi:<62}{ou}")

    print("\n   Au chapitre suivant : la passerelle LLM.\n")


if __name__ == "__main__":
    principal()
