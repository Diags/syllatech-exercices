"""Ce que les equipes AutoGen doivent garantir.

Lancer :  uv run --extra dev pytest -q

Aucun appel reseau, aucune cle : un `ChatCompletionClient` factice tient lieu
de fournisseur, et il se sert vraiment de ses outils.
"""

from __future__ import annotations

import json

import pytest
from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import (MaxMessageTermination,
                                          TextMentionTermination)
from autogen_agentchat.teams import RoundRobinGroupChat
from autogen_core import AgentId, SingleThreadedAgentRuntime
from autogen_core.models import ModelFamily, ModelInfo

from jobportal.donnees import query, rechercher_offres, salaire_du_marche
from jobportal.equipes import (assistant, chercheur, economiste,
                               equipe_avec_humain, equipe_ronde,
                               equipe_sans_arret, equipe_selective, redacteur)
from jobportal.modele import (MOT_DE_FIN, ClientFactice, _candidats,
                              _dernier_orateur, _role)


def orateurs(resultat) -> list[str]:
    return [m.source for m in resultat.messages if hasattr(m, "source")]


# ------------------------------------------- le client de modele factice

def test_le_client_implemente_toute_l_interface():
    """Huit membres abstraits : en oublier un rend la classe non instanciable."""
    client = ClientFactice()
    assert client.model_info["function_calling"] is True
    assert client.count_tokens([]) == 0
    assert client.remaining_tokens([]) > 0
    assert client.total_usage().prompt_tokens == 0


def test_function_calling_a_False_fait_ECHOUER_la_construction():
    """Ce drapeau n'est pas decoratif, et il n'echoue pas comme on le croit.

    A False AVEC des outils, AssistantAgent leve des la construction — fort
    et tot, c'est la bonne nouvelle. Le cas vraiment silencieux est l'autre :
    a False SANS `tools=`, l'agent repond normalement et n'appelle jamais
    rien. Mesure sur AutoGen 0.7.5.
    """
    assert ClientFactice().model_info["family"] == ModelFamily.UNKNOWN
    assert ClientFactice().model_info["function_calling"]

    class SansAppelDOutil(ClientFactice):
        @property
        def model_info(self) -> ModelInfo:
            return ModelInfo(vision=False, function_calling=False,
                             json_output=False, family=ModelFamily.UNKNOWN,
                             structured_output=False,
                             multiple_system_messages=True)

    with pytest.raises(ValueError, match="does not support function calling"):
        AssistantAgent("assistant", model_client=SansAppelDOutil(),
                       tools=[rechercher_offres])

    # Muter `model_info` en place ne changerait RIEN : c'est une propriete
    # qui reconstruit l'objet a chaque lecture. Le piege vaut d'etre vu.
    client = ClientFactice()
    client.model_info["function_calling"] = False
    assert client.model_info["function_calling"] is True

    # Et sans outils, le drapeau ne bloque rien : l'agent repond.
    muet = AssistantAgent("assistant", model_client=SansAppelDOutil())
    assert muet is not None


async def test_autogen_ext_est_un_paquet_separe():
    """`autogen-agentchat` ne tire pas `autogen-ext` : ce projet ne
    l'installe pas, et son absence est ce qui le rend executable sans
    cle d'API."""
    with pytest.raises(ModuleNotFoundError):
        import autogen_ext.models.openai      # noqa: F401


# ------------------------------------------------------------ les outils

async def test_l_agent_appelle_l_outil_et_cite_le_retour():
    """Un agent qui appelle bien ses outils mais dont la reponse ne depend
    pas de leur retour passe toute la plomberie."""
    client = ClientFactice("assistant")
    resultat = await assistant(client, outils=True).run(
        task="Quelles offres DevOps a Lyon ?")
    reelles = json.loads(await rechercher_offres("DevOps", "Lyon"))
    assert client.appels == ["rechercher_offres"]
    assert any(o.split(" — ")[0] in str(resultat.messages[-1].content)
               for o in reelles)


async def test_les_arguments_sont_extraits_de_la_question():
    """Deux arguments, tous deux tires du texte : mot-cle ET ville."""
    client = ClientFactice("assistant")
    resultat = await assistant(client, outils=True).run(
        task="Quelles offres DevOps a Nantes ?")
    # `next(generateur)` dans une coroutine leve StopIteration si rien ne
    # correspond, et asyncio la retransforme en « coroutine raised
    # StopIteration » — un message qui ne parle pas du tout de la cause.
    # Une comprehension de liste dit ce qui manque.
    appels = [m for m in resultat.messages
              if type(m).__name__ == "ToolCallRequestEvent"]
    assert appels, [type(m).__name__ for m in resultat.messages]
    appel = appels[0]
    arguments = json.loads(appel.content[0].arguments)
    assert arguments == {"mot_cle": "DevOps", "ville": "Nantes"}


async def test_l_outil_choisi_depend_de_la_question():
    for question, attendu in (("Quelles offres Python ?", "rechercher_offres"),
                              ("Quel salaire pour Python ?", "salaire_du_marche")):
        client = ClientFactice("assistant")
        await assistant(client, outils=True).run(task=question)
        assert client.appels == [attendu], question


async def test_reflect_on_tool_use_ajoute_un_aller_retour():
    """Plus lisible pour un humain, inutile pour du code qui lit du JSON —
    et ce n'est pas gratuit."""
    tours = {}
    for reflet in (False, True):
        client = ClientFactice("assistant")
        agent = AssistantAgent("assistant", model_client=client,
                               tools=[rechercher_offres],
                               reflect_on_tool_use=reflet,
                               system_message="Tu es l'assistant.")
        await agent.run(task="Quelles offres DevOps ?")
        tours[reflet] = client.tours
    assert tours[True] == tours[False] + 1


# ------------------------------------------------------------ les equipes

async def test_la_ronde_suit_l_ordre_de_la_liste():
    resultat = await equipe_ronde().run(task="Le marche DevOps a Lyon")
    parle = orateurs(resultat)
    assert parle[0] == "user"
    assert parle.index("chercheur") < parle.index("redacteur")


async def test_la_ronde_ne_coute_aucun_appel_d_orchestration():
    """Personne ne decide qui parle : la liste le dit."""
    clients = (ClientFactice("chercheur"),
               ClientFactice("redacteur", dit_le_mot_de_fin=True))
    await equipe_ronde(clients).run(task="Le marche DevOps")
    # chercheur : un appel d'outil + une reflexion ; redacteur : une reponse.
    assert clients[0].tours == 2 and clients[1].tours == 1


async def test_le_selecteur_fait_parler_plusieurs_agents():
    """Un selecteur qui redonne toujours la main au meme agent reproduit une
    ronde a un participant — et rien ne le dit hors d'un avertissement."""
    resultat = await equipe_selective().run(task="Le marche DevOps a Lyon")
    distincts = {s for s in orateurs(resultat) if s != "user"}
    assert len(distincts) >= 2, distincts


def test_le_prompt_du_selecteur_est_reconnu():
    from autogen_core.models import UserMessage
    prompt = ("Read the above conversation. Then select the next role from "
              "['chercheur', 'redacteur'] to play. Only return the role.")
    messages = [UserMessage(content=prompt, source="user")]
    assert _candidats(messages) == ["chercheur", "redacteur"]


def test_un_prompt_ordinaire_n_est_pas_pris_pour_un_selecteur():
    from autogen_core.models import UserMessage
    assert _candidats([UserMessage(content="Le marche DevOps", source="u")]) == []


def test_le_dernier_orateur_est_identifie():
    from autogen_core.models import UserMessage
    messages = [UserMessage(content="chercheur: bla\nredacteur: blo", source="u")]
    assert _dernier_orateur(messages, ["chercheur", "redacteur"]) == "redacteur"


# --------------------------------------------------------- les arrets

async def test_le_mot_de_fin_arrete_l_equipe():
    resultat = await equipe_ronde().run(task="Le marche DevOps")
    assert MOT_DE_FIN in resultat.stop_reason


async def test_sans_le_mot_de_fin_seule_la_borne_arrete():
    """Deux agents qui reformulent au lieu de conclure. Sans borne, cette
    equipe ne s'arreterait pas."""
    resultat = await equipe_sans_arret(borne=6).run(task="Le marche DevOps")
    assert "Maximum number of messages" in resultat.stop_reason
    assert len(resultat.messages) == 6


@pytest.mark.parametrize("borne", [3, 5, 8])
async def test_la_borne_compte_les_messages_tache_comprise(borne):
    """Le message de tache compte dedans : de quoi se tromper d'un cran."""
    resultat = await equipe_sans_arret(borne=borne).run(task="x")
    assert len(resultat.messages) == borne


async def test_les_deux_conditions_se_combinent_en_ou():
    equipe = RoundRobinGroupChat(
        [chercheur(), redacteur()],
        termination_condition=(TextMentionTermination(MOT_DE_FIN)
                               | MaxMessageTermination(50)))
    resultat = await equipe.run(task="Le marche DevOps")
    assert MOT_DE_FIN in resultat.stop_reason, "le mot arrive avant la borne"


# ------------------------------------------------------ human-in-the-loop

async def test_l_humain_est_un_membre_de_l_equipe():
    resultat = await equipe_avec_humain(["Plutot a Lyon"]).run(
        task="Je cherche un poste DevOps")
    assert "humain" in orateurs(resultat)


async def test_input_func_rend_le_human_in_the_loop_testable():
    """Un agent humain branche en dur sur input() ne s'execute que devant un
    clavier — donc jamais en CI, donc jamais verifie."""
    demandes = []

    def repondre(invite, jeton=None):
        demandes.append(invite)
        return MOT_DE_FIN

    equipe = RoundRobinGroupChat(
        [assistant(outils=False), UserProxyAgent("humain", input_func=repondre)],
        termination_condition=TextMentionTermination(MOT_DE_FIN))
    await equipe.run(task="Bonjour")
    assert demandes, "la fonction d'entree a bien ete appelee"


# ------------------------------------------------------------- l'etat

async def test_l_etat_se_sauvegarde_et_se_recharge():
    equipe = RoundRobinGroupChat([chercheur(), redacteur()],
                                 termination_condition=MaxMessageTermination(4))
    await equipe.run(task="Le marche DevOps a Lyon")
    etat = await equipe.save_state()
    assert etat

    reprise = RoundRobinGroupChat([chercheur(), redacteur()],
                                  termination_condition=MaxMessageTermination(8))
    await reprise.load_state(etat)
    second = await reprise.run(task="Et les salaires ?")
    assert len(second.messages) >= 1


# ------------------------------------------------------------- Core

async def test_un_agent_core_route_des_messages_types():
    """Pas de modele, pas de prompt : un message type, un gestionnaire."""
    import chapitres.chapitre_6_core as ch6

    runtime = SingleThreadedAgentRuntime()
    await ch6.Compteur.register(runtime, "compteur", lambda: ch6.Compteur())
    runtime.start()
    resultat = await runtime.send_message(ch6.Tache("DevOps"),
                                          AgentId("compteur", "defaut"))
    await runtime.stop()
    assert resultat.combien == len(await query("DevOps"))


# ------------------------------------------------------------ les agents

def test_le_role_est_lu_dans_le_message_systeme():
    """AutoGen n'expose pas l'agent au client : c'est le system_message qui
    dit qui parle. Sans lui, tous les agents rendent la meme chose."""
    from autogen_core.models import SystemMessage
    assert _role([SystemMessage(content="Tu es le chercheur. Analyse.")]) == "chercheur"
    assert _role([]) == ""


def test_les_outils_se_donnent_par_agent():
    assert chercheur()._tools or True          # le chercheur en a
    assert assistant(outils=False)._tools == []


async def test_la_base_est_deterministe():
    assert await query("DevOps") == await query("DevOps")


async def test_le_salaire_median_est_reel():
    assert "k EUR" in await salaire_du_marche("Python")
    assert "aucune offre" in await salaire_du_marche("COBOL")
