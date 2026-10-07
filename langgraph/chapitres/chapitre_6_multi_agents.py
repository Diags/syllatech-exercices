"""Chapitre 6 — Multi-agents : un superviseur et ses spécialistes.

L'idée tient en une phrase : **un graphe compilé est un nœud**. On imbrique
donc un agent entier là où on mettait une fonction, et le superviseur n'est
rien de plus que l'arête conditionnelle du chapitre 3, à l'échelle des
agents.

Le superviseur route d'après l'ETAT, pas d'après son humeur : on lui donne un
plan dans l'état, il dépile. C'est ce qui rend un système multi-agents
débuggable — on peut lire, à tout instant, qui va parler ensuite et pourquoi.

    uv run python chapitres/chapitre_6_multi_agents.py
"""

from __future__ import annotations

import operator
import sys
from pathlib import Path
from typing import Annotated, TypedDict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import AIMessage, HumanMessage    # noqa: E402
from langchain_core.tools import tool                          # noqa: E402
from langgraph.graph import END, START, StateGraph             # noqa: E402
from langgraph.graph.message import add_messages               # noqa: E402
from langgraph.prebuilt import ToolNode, tools_condition       # noqa: E402

from jobportal import console                                  # noqa: E402
from jobportal.modele import modele                            # noqa: E402
from jobportal.outils import rechercher_offres                 # noqa: E402


@tool
def tendances_marche(mot_cle: str) -> str:
    """Donne une tendance de marche pour un mot-cle donne."""
    return (f"Les offres mentionnant « {mot_cle} » sont en hausse de 18 % "
            "sur douze mois (source factice, pour l'exemple).")


class EtatEquipe(TypedDict):
    messages: Annotated[list, add_messages]
    plan: list[str]        # les spécialistes qu'il reste à faire parler
    courant: str           # celui que le superviseur vient de désigner
    journal: Annotated[list[str], operator.add]


CONSIGNES = {
    "analyste": "Quelles offres d'emploi correspondent à Python ?",
    "chercheur": "Quelle tendance pour les offres d'emploi Python ?",
}


def agent_react(outils: list):
    """Construit un agent ReAct à la main, et le COMPILE.

    Le graphe rendu est un Runnable : il s'utilisera comme un nœud dans le
    graphe de l'équipe. C'est toute la mécanique de l'imbrication.

    Écrit à la main plutôt qu'avec create_react_agent, qui est déprécié
    depuis LangGraph V1 — voir le chapitre 4.
    """
    outille = modele().bind_tools(outils)

    class Etat(TypedDict):
        messages: Annotated[list, add_messages]

    def assistant(state: Etat) -> dict:
        return {"messages": [outille.invoke(state["messages"])]}

    g = StateGraph(Etat)
    g.add_node("assistant", assistant)
    g.add_node("outils", ToolNode(outils))
    g.add_edge(START, "assistant")
    g.add_conditional_edges("assistant", tools_condition, {"tools": "outils", END: END})
    g.add_edge("outils", "assistant")
    return g.compile()


def construire():
    analyste = agent_react([rechercher_offres])
    chercheur = agent_react([tendances_marche])

    def superviseur(state: EtatEquipe) -> dict:
        """Dépile le plan et désigne le prochain spécialiste.

        Le nom désigné va dans une clé DEDIEE de l'état, `courant`. C'est ce
        qui rend le routage lisible : à tout instant, l'état dit qui parle
        ensuite. Router d'après le dernier message, ou d'après un journal,
        marche jusqu'au jour où deux nœuds écrivent la même chose — et l'on
        obtient alors une boucle infinie, pas une erreur.
        """
        # TODO : dépiler « plan », poser le nom retiré dans « courant », déléguer avec CONSIGNES[nom], et journaliser. Rendre courant vide quand le plan l'est.
        return {"courant": ""}

    def aiguillage(state: EtatEquipe) -> str:
        """Rend le NOM du prochain nœud, ou END. L'état seul décide."""
        return state["courant"] or END

    team = StateGraph(EtatEquipe)
    team.add_node("superviseur", superviseur)
    team.add_node("analyste", analyste)       # un graphe compilé, comme nœud
    team.add_node("chercheur", chercheur)
    team.add_edge(START, "superviseur")
    team.add_conditional_edges("superviseur", aiguillage,
                               {"analyste": "analyste", "chercheur": "chercheur", END: END})
    team.add_edge("analyste", "superviseur")   # chacun revient au superviseur
    team.add_edge("chercheur", "superviseur")
    return team.compile()


def main() -> None:
    console.utf8()
    app = construire()
    print("   START ──> superviseur ──(plan)──> analyste  ──┐")
    print("                   ▲       └────────> chercheur ─┤")
    print("                   └────────────────────────────-┘")
    print("                   └──(plan vide)──> END\n")

    final = app.invoke({
        "messages": [HumanMessage(content="Que dire des offres Python ?")],
        "plan": ["analyste", "chercheur"],
        "courant": "",
        "journal": [],
    })

    print("Journal du superviseur :")
    for l in final["journal"]:
        print(f"   {l}")

    print("\nCe que l'équipe a produit :")
    for m in final["messages"]:
        if isinstance(m, AIMessage) and not m.content:
            continue          # le message qui ne portait qu'un appel d'outil
        print(f"   {type(m).__name__:14} {str(m.content)[:74]}")

    print("\nDeux agents complets ont tourné comme deux nœuds. Chacun a fait sa")
    print("propre boucle outil — le graphe de l'équipe n'en sait rien, et c'est")
    print("exactement ce qu'on veut : le superviseur orchestre, il ne supervise")
    print("pas le détail.\n")
    print("Pour livrer : « langgraph dev » en local, puis « langgraph deploy ».")
    print("Et stream() plutôt qu'invoke() dès qu'il y a une interface : sans")
    print("cela, l'utilisateur attend devant un écran vide pendant que trois")
    print("agents réfléchissent.")


if __name__ == "__main__":
    main()
