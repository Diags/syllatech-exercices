"""Chapitre 3 — Arêtes conditionnelles et cycles.

Une arête normale dit « après A, va en B ». Une arête CONDITIONNELLE confie
la décision à une fonction. C'est ce qui fait la différence entre un
enchaînement et un agent : le graphe peut revenir en arrière.

    uv run python chapitres/chapitre_3_conditionnel.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage   # noqa: E402
from langgraph.graph import END, START, StateGraph            # noqa: E402
from langgraph.graph.message import add_messages              # noqa: E402

from jobportal import console                                 # noqa: E402

MAX_TOURS = 3


class State(TypedDict):
    messages: Annotated[list, add_messages]
    tours: int


def assistant(state: State) -> dict:
    tour = state["tours"] + 1
    return {"tours": tour, "messages": [AIMessage(content=f"réflexion {tour}")]}


def affiner(state: State) -> dict:
    return {"messages": [AIMessage(content=f"affinage après le tour {state['tours']}")]}


def router(state: State) -> str:
    """LA fonction qui décide. Elle rend un NOM de destination, pas un booléen.

    Le garde-fou sur le nombre de tours n'est pas décoratif : un cycle sans
    condition de sortie est une boucle infinie, et LangGraph finira par lever
    une erreur de récursion — après avoir brûlé autant d'appels au modèle.
    """
    # TODO : rendre END au-delà de MAX_TOURS, « affiner » sinon. Sans condition de sortie, le graphe boucle dix mille fois avant de lever une erreur.
    return END


def construire():
    g = StateGraph(State)
    g.add_node("assistant", assistant)
    g.add_node("affiner", affiner)
    g.add_edge(START, "assistant")
    # Le dictionnaire fait la correspondance entre ce que router() rend et les
    # nœuds réels. Sans lui, LangGraph ne saurait pas que END est une sortie.
    g.add_conditional_edges("assistant", router, {"affiner": "affiner", END: END})
    g.add_edge("affiner", "assistant")       # le retour : voilà le cycle
    return g.compile()


def main() -> None:
    console.utf8()
    app = construire()
    print("   START ──> assistant ──(router)──> affiner ──┐")
    print("                  ▲                             │")
    print("                  └─────────────────────────────┘")
    print("                  └──(router: tours >= 3)──> END\n")

    final = app.invoke({"messages": [HumanMessage(content="Analyse ce CV")], "tours": 0})
    print(f"Le graphe a bouclé {final['tours']} fois avant de sortir :\n")
    for m in final["messages"]:
        print(f"   {type(m).__name__:14} {m.content}")

    print("\nCe n'est plus un enchaînement : c'est une boucle que le graphe")
    print("décide lui-même de quitter. Toute la boucle agentique est là —")
    print("le chapitre 4 remplace juste router() par la question « le modèle")
    print("a-t-il demandé un outil ? ».")


if __name__ == "__main__":
    main()
