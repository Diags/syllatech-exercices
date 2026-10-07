"""Les agents et les equipes — chapitres 1 a 5.

AutoGen se distingue par sa gestion de l'ARRET. Un `RoundRobinGroupChat` sans
condition tourne jusqu'a ce que quelqu'un dise le mot magique — et si personne
ne le dit, il tourne indefiniment. C'est le chapitre 4, et c'est ce que ce
module rend mesurable.
"""

from __future__ import annotations

from autogen_agentchat.agents import AssistantAgent, UserProxyAgent
from autogen_agentchat.conditions import (MaxMessageTermination,
                                          TextMentionTermination)
from autogen_agentchat.teams import RoundRobinGroupChat, SelectorGroupChat

from .donnees import rechercher_offres, salaire_du_marche
from .modele import MOT_DE_FIN, ClientFactice


def assistant(client=None, outils=False) -> AssistantAgent:
    return AssistantAgent(
        "assistant",
        model_client=client or ClientFactice("assistant"),
        tools=[rechercher_offres, salaire_du_marche] if outils else None,
        # `reflect_on_tool_use=True` ajoute UN ALLER-RETOUR : l'agent reformule
        # le retour de l'outil au lieu de le rendre brut. C'est plus lisible et
        # ce n'est pas gratuit — le chapitre 2 le compte.
        reflect_on_tool_use=outils,
        system_message="Tu es l'assistant du portail syllatech. Cite les offres.",
    )


def chercheur(client=None) -> AssistantAgent:
    return AssistantAgent(
        "chercheur",
        model_client=client or ClientFactice("chercheur"),
        tools=[rechercher_offres],
        reflect_on_tool_use=True,
        system_message="Tu es le chercheur. Analyse le marche, puis passe la "
                       "main au redacteur.",
    )


def redacteur(client=None) -> AssistantAgent:
    return AssistantAgent(
        "redacteur",
        model_client=client or ClientFactice("redacteur", dit_le_mot_de_fin=True),
        system_message=f"Tu es le redacteur. Redige la synthese, puis termine "
                       f"ton message par {MOT_DE_FIN}.",
    )


def economiste(client=None) -> AssistantAgent:
    return AssistantAgent(
        "economiste",
        model_client=client or ClientFactice("economiste"),
        tools=[salaire_du_marche],
        reflect_on_tool_use=True,
        system_message="Tu es l'economiste. Donne les salaires du marche.",
    )


# ------------------------------------------------------------ les equipes

def equipe_ronde(clients=None, borne: int = 10) -> RoundRobinGroupChat:
    """Chapitre 3 : chacun parle a son tour, dans l'ordre de la liste.

    La condition d'arret est un OU : le mot de fin, **ou** la borne. Les deux
    sont necessaires — le mot seul laisse une equipe tourner indefiniment si
    personne ne le prononce, la borne seule coupe une conversation utile.
    """
    a, b = (clients or (None, None))
    # >>> depart: composer la condition d'arret en OU : le mot de fin, ou la borne. Le mot seul laisse tourner une equipe qui ne conclut jamais ; la borne seule coupe une conversation utile. Quatre tests le verifient. NE RETIREZ PAS la borne du squelette : une equipe sans condition d'arret ne rend jamais la main, et vos tests ne s'arreteraient pas.
    #     return RoundRobinGroupChat([chercheur(a), redacteur(b)],
    #                                termination_condition=MaxMessageTermination(2))
    return RoundRobinGroupChat(
        [chercheur(a), redacteur(b)],
        termination_condition=(TextMentionTermination(MOT_DE_FIN)
                               | MaxMessageTermination(borne)),
    )
    # <<<


def equipe_sans_arret(borne: int = 6) -> RoundRobinGroupChat:
    """La meme, avec deux agents qui ne disent JAMAIS le mot de fin.

    Sans la borne, cette equipe ne s'arreterait pas. C'est le cas que le
    chapitre 4 doit montrer, et il n'est pas theorique : il suffit qu'un agent
    reformule au lieu de conclure.
    """
    muets = [AssistantAgent(nom, model_client=ClientFactice(nom),
                            system_message=f"Tu es {nom}. Continue la discussion.")
             for nom in ("alpha", "beta")]
    return RoundRobinGroupChat(muets,
                               termination_condition=MaxMessageTermination(borne))


def equipe_selective(borne: int = 12) -> SelectorGroupChat:
    """Chapitre 3 : un selecteur (un modele) choisit qui parle.

    Le selecteur est un APPEL DE PLUS a chaque tour — c'est le prix de la
    souplesse, et le chapitre 3 le compte. En ronde, l'ordre est gratuit.
    """
    return SelectorGroupChat(
        [chercheur(), economiste(), redacteur()],
        model_client=ClientFactice("selecteur"),
        termination_condition=(TextMentionTermination(MOT_DE_FIN)
                               | MaxMessageTermination(borne)),
    )


def equipe_avec_humain(reponses: list[str], borne: int = 8) -> RoundRobinGroupChat:
    """Chapitre 5 : l'humain est un MEMBRE de l'equipe, pas une interruption.

    `input_func` est le point d'extension : `input` en console, une fonction
    asynchrone cote web, ou — ici — une liste de reponses preparees. C'est ce
    qui rend le human-in-the-loop TESTABLE, et donc utilisable ailleurs qu'en
    demonstration.
    """
    file = list(reponses)

    def repondre(invite: str, jeton=None) -> str:
        return file.pop(0) if file else MOT_DE_FIN

    return RoundRobinGroupChat(
        [assistant(outils=True), UserProxyAgent("humain", input_func=repondre)],
        termination_condition=(TextMentionTermination(MOT_DE_FIN)
                               | MaxMessageTermination(borne)),
    )
