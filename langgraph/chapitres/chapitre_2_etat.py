"""Chapitre 2 — L'état et ses réducteurs.

Deux nœuds qui écrivent la même clé : lequel gagne ? Ni l'un ni l'autre — le
REDUCTEUR décide. Sans réducteur, la valeur est remplacée ; avec, elle est
combinée. C'est la notion la plus utile du cours, et la plus vite oubliée.

    uv run python chapitres/chapitre_2_etat.py
"""

from __future__ import annotations

import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage    # noqa: E402
from langgraph.graph import END, START, StateGraph             # noqa: E402
from langgraph.graph.message import add_messages               # noqa: E402

from jobportal import console                                  # noqa: E402


# TODO : annoter les clés pour obtenir le comportement décrit en commentaire. Une clé sans réducteur est remplacée ; avec un réducteur, elle est combinée.
class State(TypedDict):
    messages: list        # doit CONCATENER les messages
    etapes: list[str]     # doit CONCATENER les étapes
    score: int            # doit être REMPLACE par le dernier nœud


def analyser(state: State) -> dict:
    return {"etapes": ["analyse"], "score": 8,
            "messages": [AIMessage(content="analyse faite")]}


def noter(state: State) -> dict:
    return {"etapes": ["notation"], "score": 5,
            "messages": [AIMessage(content="notation faite")]}


def construire():
    g = StateGraph(State)
    g.add_node("analyser", analyser)
    g.add_node("noter", noter)
    g.add_edge(START, "analyser")
    g.add_edge("analyser", "noter")
    g.add_edge("noter", END)
    return g.compile()


def main() -> None:
    console.utf8()
    app = construire()
    final = app.invoke({
        "messages": [HumanMessage(content="Évalue ce profil")],
        "etapes": [],
        "score": 0,
    })

    print("Deux nœuds ont écrit les MÊMES clés. Voici ce qu'il en reste :\n")
    print(f"   etapes   = {final['etapes']}")
    print("              → operator.add a CONCATENE les deux listes\n")
    print(f"   score    = {final['score']}")
    print("              → sans réducteur, le dernier écrit ECRASE le premier")
    print("                (analyser disait 8, noter dit 5 : il reste 5)\n")
    print(f"   messages = {len(final['messages'])} messages")
    for m in final["messages"]:
        print(f"              {type(m).__name__:14} {m.content}")
    print("              → add_messages a concaténé ET gardé l'ordre\n")

    print("La leçon : le type d'une clé d'état est une DECISION de conception.")
    print("« score: int » n'est pas une annotation, c'est une politique de")
    print("fusion — celle du dernier qui parle.")


if __name__ == "__main__":
    main()
