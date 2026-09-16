"""Ce que les graphes doivent garantir, vérifié automatiquement.

Lancer :  uv run --extra dev pytest -q

Ces tests ne sont pas décoratifs. Chacun fige une propriété que le cours
énonce — et deux d'entre eux auraient attrapé des bugs réels commis en
écrivant ce projet : un routage qui bouclait à l'infini, et un modèle
factice qui appelait toujours le même outil quel qu'il soit.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "chapitres"))

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.types import Command

from jobportal.modele import ModeleFactice, modele
from jobportal.outils import OUTILS, rechercher_offres


# ---------------------------------------------------------------- le modèle

def test_le_modele_factice_ne_demande_pas_d_outil_sans_outil():
    m = modele()
    assert not m.invoke([HumanMessage(content="Trouve des offres")]).tool_calls


def test_il_demande_un_outil_quand_la_question_s_y_prete():
    m = modele().bind_tools(OUTILS)
    r = m.invoke([HumanMessage(content="Trouve-moi des offres Python")])
    assert r.tool_calls and r.tool_calls[0]["name"] == "rechercher_offres"
    assert r.tool_calls[0]["args"]["mot_cle"] == "Python"


def test_il_appelle_l_outil_qu_on_lui_a_lie_et_pas_un_autre():
    """Bug réel : le nom de l'outil était codé en dur. Deux agents avec des
    outils différents, et le second appelait l'outil du premier."""
    @tool
    def tendances_marche(mot_cle: str) -> str:
        """Tendance du marche."""
        return "en hausse"

    m = modele().bind_tools([tendances_marche])
    r = m.invoke([HumanMessage(content="Tendance des offres Python ?")])
    assert r.tool_calls[0]["name"] == "tendances_marche"


def test_il_se_tait_apres_un_resultat_d_outil():
    """Sans cette règle, la boucle agentique ne s'arrêterait jamais."""
    m = modele().bind_tools(OUTILS)
    r = m.invoke([HumanMessage(content="offres"),
                  ToolMessage(content="JP-002", tool_call_id="x")])
    assert not r.tool_calls and "JP-002" in r.content


def test_bind_tools_rend_un_nouveau_modele():
    """Le graphe garde souvent un modèle nu À CÔTÉ du modèle outillé : si
    bind_tools modifiait le modèle en place, les deux seraient le même."""
    nu = modele()
    outille = nu.bind_tools(OUTILS)
    assert outille is not nu
    assert nu.outils == []
    assert outille.outils == OUTILS


# ---------------------------------------------------------------- chapitre 2

def test_les_reducteurs_concatenent_ou_remplacent():
    from chapitre_2_etat import construire
    final = construire().invoke({"messages": [], "etapes": [], "score": 0})
    assert final["etapes"] == ["analyse", "notation"]   # operator.add concatène
    assert final["score"] == 5                          # sans réducteur, écrase
    assert len(final["messages"]) == 2                  # add_messages concatène


# ---------------------------------------------------------------- chapitre 3

def test_le_cycle_s_arrete_sur_sa_condition():
    """Bug réel : un routage mal écrit boucle à l'infini, et LangGraph lève
    une erreur de récursion APRES avoir brûlé dix mille tours."""
    from chapitre_3_conditionnel import MAX_TOURS, construire
    final = construire().invoke({"messages": [], "tours": 0})
    assert final["tours"] == MAX_TOURS


# ---------------------------------------------------------------- chapitre 4

def test_la_boucle_agentique_execute_l_outil_et_revient():
    from chapitre_4_react import construire_a_la_main
    final = construire_a_la_main().invoke(
        {"messages": [HumanMessage(content="Trouve-moi des offres Python")]})
    types = [type(m).__name__ for m in final["messages"]]
    assert types == ["HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    # Le modèle a DEMANDE, le graphe a EXECUTE : la séparation est le propos.
    assert final["messages"][1].tool_calls
    assert "JP-002" in final["messages"][2].content


# ---------------------------------------------------------------- chapitre 5

def test_le_graphe_s_arrete_sur_interrupt_puis_reprend():
    from chapitre_5_persistance import construire
    app = construire()
    fil = {"configurable": {"thread_id": "test-1"}}
    etat = app.invoke({"messages": [], "offre_id": "JP-002",
                       "brouillon": "", "envoye": False}, fil)
    assert etat.get("__interrupt__"), "le graphe aurait dû s'arrêter"
    assert app.get_state(fil).next == ("valider_envoi",)
    final = app.invoke(Command(resume=True), fil)
    assert final["envoye"] is True


def test_deux_fils_sont_independants():
    from chapitre_5_persistance import construire
    app = construire()
    for fil_id, accord, attendu in (("a", True, True), ("b", False, False)):
        fil = {"configurable": {"thread_id": fil_id}}
        app.invoke({"messages": [], "offre_id": "JP-001",
                    "brouillon": "", "envoye": False}, fil)
        assert app.invoke(Command(resume=accord), fil)["envoye"] is attendu


# ---------------------------------------------------------------- chapitre 6

def test_le_superviseur_depile_son_plan_et_termine():
    from chapitre_6_multi_agents import construire
    final = construire().invoke({
        "messages": [HumanMessage(content="Que dire des offres Python ?")],
        "plan": ["analyste", "chercheur"], "courant": "", "journal": [],
    })
    assert final["journal"] == ["superviseur → analyste", "superviseur → chercheur"]
    assert final["plan"] == [] and final["courant"] == ""


def test_chaque_specialiste_appelle_SON_outil():
    from chapitre_6_multi_agents import construire
    final = construire().invoke({
        "messages": [HumanMessage(content="Que dire des offres Python ?")],
        "plan": ["analyste", "chercheur"], "courant": "", "journal": [],
    })
    resultats = [m.content for m in final["messages"] if isinstance(m, ToolMessage)]
    assert len(resultats) == 2
    assert any("JP-002" in r for r in resultats)        # l'analyste
    assert any("hausse" in r for r in resultats)        # le chercheur
