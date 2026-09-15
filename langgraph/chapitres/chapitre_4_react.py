"""Chapitre 4 — Outils et l'agent ReAct.

Le cycle complet, cette fois avec de vrais outils : le modèle demande, le
graphe exécute, le modèle reprend avec le résultat. Puis le raccourci
prêt-à-l'emploi, pour montrer qu'il fait exactement la même chose.

    uv run python chapitres/chapitre_4_react.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage                    # noqa: E402
from langgraph.graph import END, START, StateGraph                  # noqa: E402
from langgraph.graph.message import add_messages                    # noqa: E402
from langgraph.prebuilt import ToolNode, create_react_agent, tools_condition   # noqa: E402

from jobportal import console                                       # noqa: E402
from jobportal.modele import modele                                 # noqa: E402
from jobportal.outils import OUTILS                                 # noqa: E402


class State(TypedDict):
    messages: Annotated[list, add_messages]


def construire_a_la_main():
    """Le graphe écrit à la main : trois lignes font la boucle agentique."""
    outille = modele().bind_tools(OUTILS)

    def assistant(state: State) -> dict:
        return {"messages": [outille.invoke(state["messages"])]}

    g = StateGraph(State)
    g.add_node("assistant", assistant)
    # ToolNode lit les tool_calls du dernier message, exécute les outils
    # correspondants, et rend un ToolMessage par appel. On ne l'écrit pas.
    g.add_node("outils", ToolNode(OUTILS))
    g.add_edge(START, "assistant")
    # tools_condition EST le router du chapitre 3, déjà écrit : « des
    # tool_calls ? va aux outils. Sinon, termine. »
    g.add_conditional_edges("assistant", tools_condition, {"tools": "outils", END: END})
    g.add_edge("outils", "assistant")
    return g.compile()


def main() -> None:
    console.utf8()
    app = construire_a_la_main()
    question = "Trouve-moi des offres Python"

    print(f"Question : « {question} »\n")
    final = app.invoke({"messages": [HumanMessage(content=question)]})
    for m in final["messages"]:
        nom = type(m).__name__
        if getattr(m, "tool_calls", None):
            for a in m.tool_calls:
                print(f"   {nom:14} DEMANDE l'outil {a['name']}({a['args']})")
        else:
            print(f"   {nom:14} {str(m.content)[:76]}")

    print("\nDeux passages par le nœud « assistant », un par le nœud « outils ».")
    print("Le modèle n'a JAMAIS exécuté l'outil : il l'a demandé, et le graphe")
    print("l'a exécuté. Cette séparation est ce qui rend un agent contrôlable.\n")

    print("Le même comportement, en une ligne — avec une reserve :")
    agent = create_react_agent(modele(), OUTILS)
    r = agent.invoke({"messages": [HumanMessage(content=question)]})
    print(f"   create_react_agent → {len(r['messages'])} messages, "
          f"dernier : {str(r['messages'][-1].content)[:50]}")
    print("\n⚠️  create_react_agent est DÉPRÉCIÉ depuis LangGraph V1 : il a")
    print("   déménagé vers « from langchain.agents import create_agent », dans")
    print("   le paquet langchain, et disparaîtra en V2. Il fonctionne encore,")
    print("   en émettant l'avertissement que vous avez vu passer plus haut.")
    print("   Ce projet ne l'ajoute pas en dépendance pour un raccourci d'une")
    print("   ligne : le graphe écrit à la main, lui, ne bougera pas.")
    print("\nÉcrivez le graphe à la main tant que vous apprenez ; prenez le")
    print("raccourci quand vous avez compris ce qu'il cache.")


if __name__ == "__main__":
    main()
