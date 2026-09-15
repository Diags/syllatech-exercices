"""Chapitre 5 — Persistance et validation humaine.

Deux mécanismes qui n'ont l'air de rien et qui changent tout :

  le POINT DE REPRISE  l'état est sauvegardé à chaque étape, sous un
                       identifiant de fil. Le graphe devient reprenable.
  l'INTERRUPTION       un nœud s'arrête et rend la main. L'humain décide,
                       le graphe reprend là où il en était.

Sans point de reprise, pas d'interruption possible : il n'y aurait rien où
revenir. Les deux vont ensemble, et c'est la raison d'être du chapitre.

    uv run python chapitres/chapitre_5_persistance.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langgraph.checkpoint.memory import InMemorySaver          # noqa: E402
from langgraph.graph import END, START, StateGraph             # noqa: E402
from langgraph.graph.message import add_messages               # noqa: E402
from langgraph.types import Command, interrupt                 # noqa: E402

from jobportal import console, donnees                         # noqa: E402


class State(TypedDict):
    messages: Annotated[list, add_messages]
    offre_id: str
    brouillon: str
    envoye: bool


def rediger(state: State) -> dict:
    """Prépare une candidature. Aucune décision irréversible ici."""
    detail = donnees.get_offre(state["offre_id"]).split("\n")[0]
    return {"brouillon": f"Candidature pour {detail} — CV joint."}


def valider_envoi(state: State) -> dict:
    """Le nœud qui rend la main.

    `interrupt(...)` lève une interruption : le graphe s'arrête ICI, l'état
    est déjà sauvegardé, et la valeur passée en argument est remontée à
    l'appelant pour être montrée à l'humain. À la reprise, `interrupt` rend
    ce que l'humain a répondu — et la fonction continue comme si de rien.
    """
    accord = interrupt({"a_valider": state["brouillon"]})
    return {"envoye": bool(accord)}


def envoyer(state: State) -> dict:
    if not state["envoye"]:
        return {"messages": [("ai", "Envoi annulé par l'utilisateur.")]}
    donnees.postuler(state["offre_id"], state["brouillon"])
    return {"messages": [("ai", f"Envoyé : {state['brouillon']}")]}


def construire():
    g = StateGraph(State)
    g.add_node("rediger", rediger)
    g.add_node("valider_envoi", valider_envoi)
    g.add_node("envoyer", envoyer)
    g.add_edge(START, "rediger")
    g.add_edge("rediger", "valider_envoi")
    g.add_edge("valider_envoi", "envoyer")
    g.add_edge("envoyer", END)
    # SANS checkpointer, interrupt() lèverait une erreur : il n'y aurait
    # aucun état sauvegardé où reprendre.
    return g.compile(checkpointer=InMemorySaver())


def main() -> None:
    console.utf8()
    app = construire()

    # L'identifiant de fil est la CLE de la persistance : deux utilisateurs,
    # deux fils, deux états indépendants.
    fil = {"configurable": {"thread_id": "utilisateur-42"}}

    print("Premier invoke : le graphe part, puis s'arrête sur interrupt.\n")
    etat = app.invoke({"messages": [], "offre_id": "JP-002",
                       "brouillon": "", "envoye": False}, fil)
    attente = etat.get("__interrupt__")
    print(f"   arrêté : {bool(attente)}")
    if attente:
        print(f"   à valider : {attente[0].value['a_valider']}")

    print("\nL'état est déjà sauvegardé. On peut l'inspecter sans reprendre :")
    instantane = app.get_state(fil)
    print(f"   prochain nœud : {instantane.next}")
    print(f"   brouillon en base : {instantane.values['brouillon'][:52]}…")

    print("\n… l'humain valide dans votre interface, quelques minutes plus tard …\n")
    final = app.invoke(Command(resume=True), fil)
    print(f"   envoye = {final['envoye']}")
    for m in final["messages"]:
        print(f"   {type(m).__name__:14} {m.content[:70]}")
    print(f"   candidatures en base : {len(donnees.candidatures())}")

    print("\nRefusons, sur un AUTRE fil — l'état du premier n'en sait rien :")
    fil2 = {"configurable": {"thread_id": "utilisateur-7"}}
    app.invoke({"messages": [], "offre_id": "JP-001", "brouillon": "", "envoye": False}, fil2)
    refus = app.invoke(Command(resume=False), fil2)
    print(f"   envoye = {refus['envoye']} — {refus['messages'][-1].content}")

    print("\nRetenez la forme : le graphe ne bloque pas un fil d'exécution en")
    print("attendant l'humain. Il s'arrête, rend la main, et reprend sur appel.")
    print("C'est ce qui permet d'attendre une validation pendant deux jours.")


if __name__ == "__main__":
    main()
