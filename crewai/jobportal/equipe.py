"""Les agents, les tâches et les équipages — chapitres 1 à 4.

Le fil directeur de CrewAI tient dans trois champs : `role`, `goal`,
`backstory`. Ce ne sont pas des étiquettes : ils composent le prompt système
de l'agent, et ils décident de ce qu'il produit. Le chapitre 2 le montre en
changeant un seul mot.

Tout ici prend son modèle en paramètre — c'est ce qui rend le projet
exécutable sans clé et ses tests possibles.
"""

from __future__ import annotations

from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

from .donnees import rechercher_offres, salaire_du_marche
from .modele import ModeleFactice


def modele(m=None):
    return m if m is not None else ModeleFactice()


# ------------------------------------------- chapitre 2 : la sortie typée

class Tendance(BaseModel):
    titre: str
    impact: int = Field(ge=1, le=5)
    source: str


class Rapport(BaseModel):
    """La sortie structurée du chapitre 2.

    `output_pydantic` ne « demande » pas au modèle d'être structuré : CrewAI
    valide sa réponse contre ce schéma. Une réponse hors schéma n'est pas une
    réponse un peu bizarre, c'est une erreur — et c'est la différence entre un
    agent qu'on peut brancher sur du code et un agent qu'on relit à la main.
    """

    tendances: list[Tendance]
    resume: str


# ------------------------------------------------- les agents du portail

def chercheur(m=None, outils: bool = False) -> Agent:
    return Agent(
        role="Analyste du marche de l'emploi",
        goal="Identifier les tendances du recrutement tech",
        backstory="Expert en veille, precis et factuel. Cite toujours ses sources.",
        tools=[rechercher_offres, salaire_du_marche] if outils else [],
        llm=modele(m),
        verbose=False,
    )


def redacteur(m=None) -> Agent:
    return Agent(
        role="Redacteur de la newsletter",
        goal="Transformer une analyse en trois paragraphes lisibles",
        backstory="Ancien journaliste. Deteste le jargon et les superlatifs.",
        llm=modele(m),
        verbose=False,
    )


def economiste(m=None) -> Agent:
    return Agent(
        role="Analyste des remunerations",
        goal="Situer les salaires d'un metier par rapport au marche",
        backstory="Statisticien. Ne conclut jamais sans un chiffre.",
        tools=[salaire_du_marche],
        llm=modele(m),
        verbose=False,
    )


# ------------------------------------------------------- les équipages

def equipe_simple(m=None) -> Crew:
    """Chapitre 1 : un agent, une tâche."""
    agent = chercheur(m)
    tache = Task(description="Analyse les tendances {sujet} en France",
                 expected_output="Un rapport de cinq points cles", agent=agent)
    return Crew(agents=[agent], tasks=[tache], verbose=False)


def equipe_typee(m=None) -> Crew:
    """Chapitre 2 : la même, avec une sortie validée."""
    agent = chercheur(m)
    tache = Task(description="Analyse les tendances {sujet}",
                 expected_output="Rapport structure",
                 output_pydantic=Rapport, agent=agent)
    return Crew(agents=[agent], tasks=[tache], verbose=False)


def equipe_outillee(m=None) -> Crew:
    """Chapitre 3 : l'agent interroge la base avant de conclure."""
    agent = chercheur(m, outils=True)
    tache = Task(description="Quelles offres {sujet} le portail propose-t-il ?",
                 expected_output="La liste des offres trouvees", agent=agent)
    return Crew(agents=[agent], tasks=[tache], verbose=False)


def equipe_sequentielle(m=None) -> Crew:
    """Chapitre 4 : deux spécialistes, dans l'ordre.

    La seconde tâche reçoit le résultat de la première par `context`. Sans ce
    champ, elle repart de rien — et l'on obtient deux rapports indépendants là
    où l'on croyait avoir une chaîne.
    """
    analyste, plume = chercheur(m, outils=True), redacteur(m)
    veille = Task(description="Analyse les offres {sujet} du portail",
                  expected_output="Une liste d'offres", agent=analyste)
    redaction = Task(description="Redige la newsletter a partir de l'analyse",
                     expected_output="Trois paragraphes", agent=plume,
                     context=[veille])
    return Crew(agents=[analyste, plume], tasks=[veille, redaction],
                process=Process.sequential, verbose=False)


def equipe_hierarchique(m=None) -> Crew:
    """Chapitre 4 : un manager décompose et délègue.

    ⚠️ Le `manager_llm` est OBLIGATOIRE en mode hiérarchique, et c'est logique :
    le manager est un agent de plus, avec son propre coût. Une équipe de trois
    en hiérarchique, ce sont quatre additions — le chapitre 4 les compte.
    """
    return Crew(
        agents=[chercheur(m, outils=True), economiste(m), redacteur(m)],
        tasks=[Task(description="Fais le point sur le marche {sujet} : offres, "
                                "salaires, et une synthese lisible",
                    expected_output="Une note de synthese")],
        process=Process.hierarchical,
        manager_llm=modele(m),
        verbose=False,
    )
