"""Ce que les agents ADK doivent garantir.

Lancer :  uv run --extra dev pytest -q

Aucun appel reseau, aucune cle : un `BaseLlm` factice tient lieu de Gemini,
et il se sert vraiment de ses outils.
"""

from __future__ import annotations

import pytest
from google.adk import Agent
from google.adk.agents import SequentialAgent
from google.adk.memory import InMemoryMemoryService
from google.adk.models import LlmResponse
from google.adk.sessions import InMemorySessionService
from google.genai import types

from jobportal.agents import (assistant, boucle, coordinateur, eventail,
                              modele, pipeline)
from jobportal.donnees import query, rechercher_offres, salaire_du_marche
from jobportal.harnais import lancer
from jobportal.modele import ModeleFactice, _destinataire


# --------------------------------------------------- le modele factice

def test_baseLlm_n_a_qu_une_methode_abstraite():
    from google.adk.models import BaseLlm
    assert getattr(BaseLlm, "__abstractmethods__", set()) == {"generate_content_async"}


async def test_le_modele_factice_s_integre_a_un_agent():
    trace = await lancer(assistant(), "Quelles offres DevOps a Lyon ?")
    assert trace.final


# ------------------------------------------------------- les sessions

async def test_create_session_est_asynchrone():
    """Le cours l'appelle sans `await` : la session n'est jamais creee."""
    import inspect
    assert inspect.iscoroutinefunction(InMemorySessionService.create_session)


async def test_sans_await_la_session_n_existe_pas():
    service = InMemorySessionService()
    coroutine = service.create_session(app_name="jp", user_id="d", session_id="s")
    assert str(type(coroutine).__name__) == "coroutine"
    await coroutine          # sinon Python emet un avertissement au ramassage
    session = await service.get_session(app_name="jp", user_id="d", session_id="s")
    assert session is not None


async def test_deux_sessions_ne_se_voient_pas():
    service = InMemorySessionService()
    for nom in ("s1", "s2"):
        await service.create_session(app_name="jp", user_id="d", session_id=nom)
    s1 = await service.get_session(app_name="jp", user_id="d", session_id="s1")
    s2 = await service.get_session(app_name="jp", user_id="d", session_id="s2")
    assert s1.id != s2.id


# ---------------------------------------------------------- les outils

async def test_l_agent_appelle_l_outil_et_cite_le_retour():
    """Un agent qui appelle bien ses outils mais dont la reponse ne depend
    pas de leur retour passe toute la plomberie."""
    espion = ModeleFactice("assistant")
    trace = await lancer(assistant(espion), "Quelles offres DevOps a Lyon ?")
    reelles = rechercher_offres("DevOps", "Lyon")["offres"]
    assert espion.appels == ["rechercher_offres"]
    assert any(o.split(" — ")[0] in trace.final for o in reelles)


async def test_l_outil_choisi_depend_de_la_question():
    for question, attendu in (("Quelles offres Python ?", "rechercher_offres"),
                              ("Quel salaire pour Python ?", "salaire_du_marche")):
        espion = ModeleFactice("assistant")
        await lancer(assistant(espion), question)
        assert espion.appels == [attendu], question


def test_un_outil_rend_un_dict_avec_un_status():
    """La convention d'ADK : c'est ce qui permet au modele de distinguer
    « rien trouve » d'une panne."""
    assert rechercher_offres("DevOps", "Lyon")["status"] == "success"
    assert rechercher_offres("COBOL", "Lyon")["status"] == "error"
    assert "message" in rechercher_offres("COBOL", "Lyon")


def test_la_docstring_porte_les_args_et_le_returns():
    """ADK la lit pour decrire chaque parametre au modele."""
    doc = rechercher_offres.__doc__ or ""
    assert "Args:" in doc and "Returns:" in doc
    assert "mot_cle" in doc and "ville" in doc


# ------------------------------------------------------- la delegation

async def test_la_delegation_suit_la_description():
    """C'est la `description` d'un sous-agent — pas son `instruction` — que
    le coordinateur lit pour choisir."""
    for question, attendu in (("Quel salaire pour DevOps ?", "expert_salaires"),
                              ("Quelles offres DevOps ?", "expert_offres")):
        trace = await lancer(coordinateur(), question)
        assert attendu in trace.auteurs, (question, trace.auteurs)


def test_le_destinataire_se_choisit_sur_la_description():
    instruction = ("Agent name: expert_offres\n"
                   "Agent description: Repond sur les offres du portail.\n\n"
                   "Agent name: expert_salaires\n"
                   "Agent description: Repond sur salaire et remuneration.\n")
    assert _destinataire(instruction, "quel salaire pour devops") == "expert_salaires"
    assert _destinataire(instruction, "quelles offres devops") == "expert_offres"


async def test_la_delegation_ne_rebondit_pas():
    """ADK donne `transfer_to_agent` AUSSI aux sous-agents. Le choisir
    systematiquement fait rebondir la question jusqu'au RecursionError."""
    trace = await lancer(coordinateur(), "Quelles offres DevOps ?")
    assert trace.auteurs.count("coordinateur") <= 2, trace.auteurs


async def test_deleguer_coute_un_appel_de_plus():
    seul = ModeleFactice("assistant")
    await lancer(assistant(seul), "Quelles offres DevOps ?")
    coord = ModeleFactice("coordinateur")
    await lancer(coordinateur(coord), "Quelles offres DevOps ?")
    assert coord.tours == seul.tours + 1


# --------------------------------------------------- les workflows

async def test_output_key_ecrit_dans_l_etat():
    trace = await lancer(pipeline(), "Les offres DevOps")
    assert "analyse" in trace.etat
    assert trace.etat["analyse"]


async def test_le_second_agent_lit_ce_que_le_premier_a_ecrit():
    """Le lien n'est pas un passage d'argument : c'est une variable de
    session, substituee dans l'instruction AVANT l'appel."""
    trace = await lancer(pipeline(), "Les offres DevOps")
    assert "analyste" in trace.final, trace.final


async def test_une_cle_inconnue_leve_une_KeyError():
    """Bonne nouvelle : ADK refuse. Le defaut restant est que l'erreur
    arrive a l'EXECUTION, pas a la construction du pipeline."""
    casse = SequentialAgent(name="casse", sub_agents=[
        Agent(name="a", model=modele(None, "a"), instruction="Analyse.",
              output_key="analyse"),
        Agent(name="b", model=modele(None, "b"),
              instruction="Redige a partir de {analyze}."),
    ])
    with pytest.raises(KeyError, match="analyze"):
        await lancer(casse, "Les offres DevOps")


async def test_l_eventail_ecrit_deux_cles_distinctes():
    """Deux agents qui ecriraient la meme se marcheraient dessus — sans
    erreur, et le dernier gagnerait."""
    trace = await lancer(eventail(), "Les offres DevOps")
    assert set(trace.etat) == {"offres", "salaires"}


@pytest.mark.parametrize("tours", [1, 2, 3])
async def test_la_boucle_respecte_max_iterations(tours):
    """Sans borne, un LoopAgent tourne jusqu'a une escalade que personne ne
    leve."""
    espion = ModeleFactice("affineur")
    await lancer(boucle(espion, tours), "Ameliore")
    assert espion.tours == tours


async def test_un_workflow_paie_un_appel_par_etape():
    """L'ordre est ecrit en Python : personne ne decide, donc personne ne
    paie pour decider."""
    for n in (2, 3, 4):
        espion = ModeleFactice("chaine")
        chaine = SequentialAgent(name=f"c{n}", sub_agents=[
            Agent(name=f"e{i}", model=espion, instruction=f"Etape {i}.",
                  output_key=f"e{i}") for i in range(n)])
        await lancer(chaine, "x")
        assert espion.tours == n


# --------------------------------------------------------- la memoire

async def test_la_memoire_traverse_les_sessions():
    service = InMemorySessionService()
    await service.create_session(app_name="jp", user_id="d", session_id="s1")
    from google.adk.runners import Runner
    runner = Runner(agent=assistant(), app_name="jp", session_service=service)
    message = types.Content(role="user",
                            parts=[types.Part(text="Quelles offres DevOps ?")])
    async for _ in runner.run_async(user_id="d", session_id="s1",
                                    new_message=message):
        pass
    session = await service.get_session(app_name="jp", user_id="d", session_id="s1")

    memoire = InMemoryMemoryService()
    await memoire.add_session_to_memory(session)
    resultat = await memoire.search_memory(app_name="jp", user_id="d",
                                           query="DevOps")
    assert resultat.memories


# ------------------------------------------------------- les callbacks

async def test_un_callback_observe_sans_gener():
    vus = []

    def avant(callback_context, llm_request):
        vus.append(1)
        return None

    agent = Agent(name="observe", model=modele(None, "observe"),
                  instruction="Tu aides.", tools=[rechercher_offres],
                  before_model_callback=avant)
    trace = await lancer(agent, "Quelles offres DevOps ?")
    assert vus and trace.final


async def test_un_callback_peut_court_circuiter_le_modele():
    """Le meilleur endroit pour un garde-fou : avant l'appel, pas apres la
    reponse. Pas de tokens, pas de latence, pas de fuite."""
    espion = ModeleFactice("garde")

    def refuser(callback_context, llm_request):
        return LlmResponse(content=types.Content(
            role="model", parts=[types.Part(text="Hors perimetre.")]))

    agent = Agent(name="garde", model=espion, instruction="Tu aides.",
                  before_model_callback=refuser)
    trace = await lancer(agent, "La recette du cassoulet")
    assert trace.final == "Hors perimetre."
    assert espion.tours == 0, "le modele ne doit pas avoir ete appele"


# ---------------------------------------------------------- les donnees

def test_la_base_est_deterministe():
    assert query("DevOps") == query("DevOps")


def test_le_filtre_par_ville_fonctionne():
    for offre in query("DevOps", "Lyon"):
        assert offre["ville"] == "Lyon"


def test_le_salaire_median_est_reel():
    assert salaire_du_marche("Python")["status"] == "success"
    assert salaire_du_marche("COBOL")["status"] == "error"
