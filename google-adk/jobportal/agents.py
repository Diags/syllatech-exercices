"""Les agents du portail — chapitres 1 a 5.

ADK distingue deux familles, et les confondre coute cher :

  · l'AGENT LLM (`Agent`) decide. Son `instruction` et la `description` de ses
    sous-agents pilotent la delegation, et chaque decision est un appel.
  · les AGENTS DE WORKFLOW (`SequentialAgent`, `ParallelAgent`, `LoopAgent`)
    n'appellent aucun modele pour s'orchestrer. L'ordre est ecrit en Python.

Le chapitre 4 le mesure : un pipeline sequentiel de deux agents coute deux
appels, un coordinateur qui delegue en coute trois.
"""

from __future__ import annotations

from google.adk import Agent
from google.adk.agents import LoopAgent, ParallelAgent, SequentialAgent

from .donnees import rechercher_offres, salaire_du_marche
from .modele import ModeleFactice


def modele(m=None, nom: str = "factice"):
    """Le modele est un PARAMETRE, jamais une chaine en dur.

    `Agent(model="gemini-flash-latest")` resout un nom vers un client Google,
    qui demande une cle. Passer un objet `BaseLlm` court-circuite cette
    resolution — c'est ce qui rend ce projet executable et ses tests possibles.
    """
    return m if m is not None else ModeleFactice(nom)


# --------------------------------------------- chapitres 1 et 2 : un agent

def assistant(m=None, outils: bool = True) -> Agent:
    return Agent(
        name="assistant",
        model=modele(m, "assistant"),
        instruction="Tu aides les candidats du portail syllatech.",
        tools=[rechercher_offres, salaire_du_marche] if outils else [],
    )


# ------------------------------------------- chapitre 3 : la delegation

def coordinateur(m=None) -> Agent:
    """Un agent racine qui oriente vers le bon expert.

    ⚠️ C'est la `description` d'un sous-agent — pas son `instruction` — que le
    coordinateur lit pour choisir. Une description absente ou vague produit une
    delegation au hasard, et aucune erreur ne le signale.
    """
    expert_offres = Agent(
        name="expert_offres",
        model=modele(m, "expert_offres"),
        description="Repond aux questions sur les offres d'emploi du portail.",
        tools=[rechercher_offres],
    )
    expert_salaires = Agent(
        name="expert_salaires",
        model=modele(m, "expert_salaires"),
        description="Repond aux questions de remuneration et de salaire.",
        tools=[salaire_du_marche],
    )
    return Agent(
        name="coordinateur",
        model=modele(m, "coordinateur"),
        instruction="Oriente la question vers le bon expert.",
        sub_agents=[expert_offres, expert_salaires],
    )


# ------------------------------------- chapitre 4 : les agents de workflow

def pipeline(m=None) -> SequentialAgent:
    """Deux agents en chaine, relies par l'ETAT de session.

    `output_key="analyse"` ecrit la reponse de l'analyste dans l'etat ; le
    `{analyse}` de l'instruction du redacteur est substitue par ADK AVANT
    l'appel. Le lien n'est donc pas un passage d'argument : c'est une variable
    de session, et elle survit a l'agent qui l'a ecrite.

    Corollaire qui surprend : une cle mal orthographiee ne leve rien. Le
    `{analyse}` reste litteral dans l'instruction, et le redacteur travaille
    sur le mot « {analyse} ».
    """
    analyste = Agent(
        name="analyste",
        model=modele(m, "analyste"),
        instruction="Analyse les offres du portail.",
        tools=[rechercher_offres],
        output_key="analyse",
    )
    redacteur = Agent(
        name="redacteur",
        model=modele(m, "redacteur"),
        instruction="Redige une synthese a partir de {analyse}.",
    )
    return SequentialAgent(name="pipeline_offres",
                           sub_agents=[analyste, redacteur])


def eventail(m=None) -> ParallelAgent:
    """Deux agents lances EN MEME TEMPS, sur des sous-questions independantes.

    Chacun ecrit sa propre cle d'etat. Deux agents qui ecriraient la MEME cle
    se marcheraient dessus — sans erreur, et le dernier gagnerait.
    """
    return ParallelAgent(
        name="eventail",
        sub_agents=[
            Agent(name="cote_offres", model=modele(m, "cote_offres"),
                  instruction="Cherche les offres.", tools=[rechercher_offres],
                  output_key="offres"),
            Agent(name="cote_salaires", model=modele(m, "cote_salaires"),
                  instruction="Cherche les salaires.", tools=[salaire_du_marche],
                  output_key="salaires"),
        ])


def boucle(m=None, tours: int = 3) -> LoopAgent:
    """Le meme agent, repete — avec une BORNE.

    `max_iterations` n'est pas une precaution : sans elle, un LoopAgent tourne
    jusqu'a ce qu'un sous-agent leve une escalade. Un agent qui reformule au
    lieu de conclure ne la leve jamais.
    """
    return LoopAgent(
        name="affinage",
        max_iterations=tours,
        sub_agents=[Agent(name="affineur", model=modele(m, "affineur"),
                          instruction="Ameliore la synthese.",
                          output_key="synthese")],
    )
