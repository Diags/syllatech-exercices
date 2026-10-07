"""Chapitre 6 — Mettre la passerelle devant l'existant.

    uv run python chapitres/chapitre_6_integration.py

L'insertion la moins risquée ne touche pas au code : on repointe une base
URL. Ce chapitre regarde ce que cela change réellement — et ce que cela ne
change pas, ce qui est la moitié de la réponse.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from jobportal import schema_publie                              # noqa: E402
from jobportal.commun import (                                   # noqa: E402
    AMONT, EXEMPLES_AMONT, PORTAIL, ligne, plier, tableau, titre, utf8,
)
from jobportal.config import charger, charger_dossier             # noqa: E402
from jobportal.routage import Requete, candidates, chevauchements  # noqa: E402


ETAPES = [
    ("1. observer", ["accessLog"], "aucun risque : on ne refuse rien"),
    ("2. brider", ["localRateLimit", "remoteRateLimit"],
     "on limite, on ne bloque pas encore"),
    ("3. authentifier", ["jwtAuth", "apiKey", "oidc"],
     "avec `mode: strict`, sinon rien ne change"),
    ("4. autoriser", ["authorization", "mcpAuthorization"],
     "des regles CEL, ecrites defensivement"),
    ("5. filtrer", ["ai", "mcpGuardrails"],
     "avec `action: reject`, sinon on masque"),
]


def principal() -> None:
    utf8()

    titre(1, "REPOINTER UNE BASE URL : CE QUI CHANGE, ET CE QUI NE CHANGE PAS")
    tableau(["cote", "avant", "apres"], [
        ["l'application", "ANTHROPIC_BASE_URL=api.anthropic.com",
         "…=agentgateway:3000"],
        ["le format des requetes", "inchange", "inchange"],
        ["le code", "inchange", "inchange"],
        ["qui detient la cle d'API", "l'application", "le proxy"],
        ["qui voit les prompts", "l'application", "le proxy AUSSI"],
        ["ce qui casse si le proxy tombe", "rien", "tout"],
    ], [34, 38, 26])
    print()
    for l in plier(
        "Les trois premieres lignes sont l'argument du chapitre, et il est "
        "juste. Les trois dernieres sont ce qu'on achete avec : la cle "
        "quitte l'application — c'est un gain —, les prompts passent par un "
        "point unique — c'est un gain ET une concentration —, et la "
        "disponibilite de tout le systeme devient celle du proxy."):
        print(f"   {l}")

    titre(2, "DURCIR CRAN PAR CRAN")
    politiques = set(schema_publie.definitions()["FilterOrPolicy"]["properties"])
    tableau(["etape", "politiques", "la ligne a ne pas oublier"],
            [[etape, ", ".join(p for p in noms if p in politiques), note]
             for etape, noms, note in ETAPES], [18, 32, 42])
    print()
    ligne("politiques de route disponibles", str(len(politiques)), 34)
    print()
    for l in plier(
        "Les trois dernieres notes sont les defauts mesures aux chapitres "
        "precedents. Ils ont tous la meme forme : la politique est POSEE, "
        "elle s'affiche dans le fichier, elle passe le schema — et elle "
        "n'applique pas ce qu'on croit."):
        print(f"   {l}")

    titre(3, "CE QUE LE PORTAIL A REELLEMENT POSE")
    for chemin in sorted(PORTAIL.glob("*.yaml")):
        config = charger(chemin)
        posees = config.politiques_posees()
        ligne(chemin.name,
              ", ".join(f"{n}×{c}" for n, c in posees.items()) or "(aucune)", 22)
    print()
    for l in plier(
        "Trois fichiers, trois responsabilites. Les separer n'est pas une "
        "coquetterie : `agentgateway --file` prend UN fichier, donc les "
        "reunir est un geste de deploiement — et c'est le bon moment pour "
        "relire ce que l'assemblage produit."):
        print(f"   {l}")

    titre(4, "CE QU'UNE RELECTURE HUMAINE RATE")
    fusion = charger(PORTAIL / "01-mcp.yaml")
    ajoutee = {"name": "tout-le-reste", "backends": [{"host": "ancien:8080"}]}
    fusion.brut["binds"][0]["listeners"][0]["routes"].append(ajoutee)
    ligne("routes apres fusion", str(len(fusion.routes())), 30)
    ligne("erreurs du schema", str(len(schema_publie.verifier(fusion))), 30)
    print()
    requetes = [Requete("/mcp"), Requete("/mcp/tools"), Requete("/v1/chat"),
                Requete("/")]
    tableau(["requete", "routes candidates"],
            [[str(r), ", ".join(c.route.nom for c in candidates(fusion, r))]
             for r in requetes], [24, 46])
    print()
    ambigues = chevauchements(fusion, requetes)
    ligne("requetes que DEUX routes attrapent", str(len(ambigues)), 38)
    print()
    for l in plier(
        "La route ajoutee n'ecrit aucun `matches` : elle attrape tout, y "
        "compris ce que la premiere attrapait. Le fichier est valide, et "
        "l'outil `essayer_route.py` sort en erreur — c'est le genre de "
        "controle qui a sa place dans une CI, parce qu'aucune relecture ne le "
        "fait de maniere fiable."):
        print(f"   {l}")

    titre(5, "L'OBSERVABILITE, ET LE MEME CEL")
    champs = schema_publie.definitions()["AccessLogFields"]["properties"]
    for nom, corps in champs.items():
        ligne(f"AccessLogFields.{nom}",
              " ".join(corps.get("description", "").split()), 30)
    print()
    exemple = charger(EXEMPLES_AMONT / "traffic-a2a.yaml")
    ligne("`amont/exemples/traffic-a2a.yaml`",
          str(exemple.brut.get("frontendPolicies")), 34)
    print()
    for l in plier(
        "Le journal d'acces se declare en CEL, avec le meme contexte que les "
        "regles d'autorisation — `amont/cel.md` le documente champ par champ. "
        "C'est la meilleure nouvelle du chapitre : ce qu'on a appris a ecrire "
        "pour autoriser sert a journaliser, et inversement."):
        print(f"   {l}")
    print()
    for l in plier(
        "Une precaution vaut d'etre dite : `request.body` est dans le "
        "contexte. Le mettre dans un journal met les prompts dans le journal "
        "— avec ce que les utilisateurs y ont ecrit."):
        print(f"   {l}")

    titre(6, "KUBERNETES, ET CE QUE LE DEPOT EN DIT")
    readme = (AMONT / "README.md").read_text(encoding="utf-8")
    vues: set[str] = set()
    for reperage in ("Kubernetes", "Gateway API"):
        for l in readme.splitlines():
            # Le README melange markdown et liens : on garde le LIBELLE
            # du lien et on jette l'URL, sans quoi la phrase commence par
            # un tiret orphelin.
            propre = re.sub(r"\[([^\]]+)\]\([^)]+\)",
                            lambda m: m.group(1),
                            " ".join(l.split())).strip("*- ")
            if reperage not in propre or propre in vues:
                continue
            vues.add(propre)
            for morceau in plier(propre, 62):
                print(f"      {morceau}")
            print()
            break
    for l in plier(
        "Le support annonce des ressources `Gateway` et `HTTPRoute`, et un "
        "deploiement progressif a 10 % puis 100 %. Ce projet ne peut ni le "
        "confirmer ni le dementir : il n'a pas de cluster, et le dossier "
        "`amont/` ne contient aucun manifeste Kubernetes. C'est une limite a "
        "dire, pas a combler par une supposition."):
        print(f"   {l}")

    titre(7, "CE QUE CE PROJET NE PROUVE PAS")
    for limite in [
        "le proxy ne tourne pas : aucune requete n'a traverse agentgateway,",
        "  et donc aucune latence, aucun cout, aucun repli n'est mesure ;",
        "la regle de precedence entre routes candidates n'est pas reproduite",
        "  — elle n'est ecrite nulle part dans `amont/`, et ce projet liste",
        "  les candidates au lieu de designer un vainqueur ;",
        "les motifs des builtins de guardrails sont ceux de ce projet, pas",
        "  ceux d'agentgateway : le chapitre 5 mesure un garde-fou regex,",
        "  pas le sien ;",
        "les fonctions CEL propres a agentgateway (25, dont `default` et",
        "  `coalesce`) ne sont pas evaluees — elles sont signalees.",
    ]:
        print(f"   {limite}" if limite.startswith("  ") else f"   · {limite}")
    print()
    configs = charger_dossier(EXEMPLES_AMONT)
    ligne("configurations d'exemple du depot", str(len(configs)), 38)
    ligne("acceptees par la couche A",
          str(sum(1 for c in configs if not schema_publie.verifier(c))), 38)
    print()
    for l in plier(
        "Ce qui EST reel : `amont/config.schema.json` est le document que le "
        "proxy publie, copie sans retouche, et la validation ne transcrit "
        "rien. Les regles CEL et les expressions regulieres sont executees. "
        "Les quatre derives des chapitres 2 a 5 se verifient sans rien "
        "lancer, sur des fichiers qui sont dans ce depot."):
        print(f"   {l}")

    print("\n   uv run python outils/verifier_config.py VOTRE.yaml\n")


if __name__ == "__main__":
    principal()
