"""Chapitre 1 — Le plus petit graphe qui tourne.

Trois notions, et elles suffisent à tout le reste :
  l'ETAT    ce qui circule, décrit par un TypedDict ;
  les NŒUDS des fonctions qui reçoivent l'état et rendent une mise à jour ;
  les ARETES qui va après quoi, de START à END.

    uv run python chapitres/chapitre_1_hello_graph.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.graph import END, START, StateGraph   # noqa: E402

from jobportal import console                        # noqa: E402
from jobportal.modele import modele                  # noqa: E402

llm = modele()


class State(TypedDict):
    question: str
    reponse: str


def repondre(state: State) -> dict:
    """Un nœud reçoit l'état ENTIER et rend une mise à jour PARTIELLE.

    Retenez ce point : on ne renvoie jamais l'état complet. On renvoie les
    clés qu'on change, et LangGraph fusionne. C'est ce qui permet à plusieurs
    nœuds de travailler sans se marcher dessus.
    """
    return {"reponse": llm.invoke(state["question"]).content}


def construire():
    g = StateGraph(State)
    g.add_node("repondre", repondre)
    g.add_edge(START, "repondre")
    g.add_edge("repondre", END)
    return g.compile()


def main() -> None:
    console.utf8()
    app = construire()

    print("Le graphe compilé :\n")
    print("   START ──> repondre ──> END\n")

    resultat = app.invoke({"question": "Bonjour !"})
    print("invoke({'question': 'Bonjour !'}) rend l'état FINAL, pas la réponse :")
    for cle, valeur in resultat.items():
        print(f"   {cle:10} = {valeur}")

    print("\nRemarquez que « question » est toujours là. L'état n'est pas")
    print("consommé : il s'enrichit. C'est ce qui rend un graphe inspectable.")


if __name__ == "__main__":
    main()
