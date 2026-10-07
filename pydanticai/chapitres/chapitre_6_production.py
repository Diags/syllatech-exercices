"""Chapitre 6 — Observabilite, MCP, et ce qui casse en montant de version.

    uv run python chapitres/chapitre_6_production.py
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pydantic_ai import Agent, capture_run_messages           # noqa: E402
from pydantic_ai.models.test import TestModel                 # noqa: E402

from jobportal import console                                 # noqa: E402
from jobportal.agents import Deps, agent_offres               # noqa: E402
from jobportal.donnees import DatabaseConn                    # noqa: E402
from jobportal.modele import modele_conseiller                # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def main() -> None:
    console.utf8()

    print("1. TRACER SANS RIEN INSTALLER — capture_run_messages\n")
    deps = Deps(candidat_id=5, db=DatabaseConn())
    with capture_run_messages() as messages:
        agent_offres(modele_conseiller()).run_sync("Mes offres ?", deps=deps)
    for message in messages:
        for part in message.parts:
            detail = getattr(part, "tool_name", "") or str(getattr(part, "content", ""))[:46]
            print(f"   {type(part).__name__:<18}{detail}")
    print("\n   Logfire n'est pas necessaire pour VOIR ce qui se passe.")
    print("   capture_run_messages est dans la bibliotheque, sans compte ni")
    print("   reseau, et c'est ce qu'on veut dans un test qui echoue.")

    print("\n2. LOGFIRE — trois lignes, et c'est de l'OpenTelemetry\n")
    print("     import logfire")
    print("     logfire.configure()")
    print("     logfire.instrument_pydantic_ai()")
    print("\n   Le point a retenir n'est pas le produit : c'est qu'il s'agit")
    print("   d'OpenTelemetry standard. N'importe quel collecteur OTEL recoit")
    print("   ces traces — Jaeger, Grafana, votre APM. On ne s'attache donc")
    print("   pas a un fournisseur en instrumentant.")

    print("\n3. MCP : LE NOM DE CLASSE DE LA VIDEO N'EXISTE PLUS\n")
    print("     from pydantic_ai.mcp import MCPServerStdio        # 1.x")
    print("     from pydantic_ai.mcp import MCPToolset            # 2.x\n")
    try:
        import pydantic_ai.mcp as m
        print(f"   exporte : {[n for n in m.__all__ if 'MCP' in n]}")
    except ImportError as e:
        print(f"   ImportError : {str(e)[:96]}…")
        print("\n   Deux choses a la fois, et c'est ce qui deroute : l'extra")
        print("   « pydantic-ai-slim[mcp] » manque, donc l'import echoue AVANT")
        print("   d'atteindre le nom de la classe. Installez l'extra, et vous")
        print("   decouvrirez alors que MCPServerStdio n'existe plus non plus.")
    print("\n   La forme 2.x : MCPToolset(\"serveur.py\") ou MCPToolset(url),")
    print("   puis Agent(..., toolsets=[toolset]). Une seule classe pour tous")
    print("   les transports, au lieu d'une par transport.")

    print("\n4. BORNER LES VERSIONS — la lecon des trois derives ci-dessus\n")
    projet = tomllib.loads((RACINE / "pyproject.toml").read_text(encoding="utf-8"))
    for dependance in projet["project"]["dependencies"]:
        print(f"   {dependance}")
    print("\n   Trois APIs de ce cours ont change entre 1.x et 2.x : le nom du")
    print("   serveur MCP, la construction du graphe, et le paquet lui-meme")
    print("   (pydantic-ai-slim plutot que pydantic-ai, pour ne pas tirer tous")
    print("   les clients de fournisseurs). Une borne haute n'est pas de la")
    print("   prudence excessive : c'est la seule chose qui distingue « ca")
    print("   marchait hier » d'un projet qu'on peut donner a quelqu'un.")

    print("\n5. CE QU'IL FAUT SURVEILLER EN PRODUCTION\n")
    espion = TestModel()
    resultat = Agent(espion, output_type=str).run_sync("x")
    print(f"   usage      {resultat.usage}")
    print("   Les tokens sont dans le resultat, a chaque run. Les agreger par")
    print("   requete utilisateur coute trois lignes et evite la surprise en")
    print("   fin de mois. Un agent a outils peut faire dix allers-retours")
    print("   pour une seule question : c'est la que la facture se fait.")


if __name__ == "__main__":
    main()
