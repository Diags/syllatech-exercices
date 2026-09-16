"""Les agents du job portal — ceux des chapitres 1 à 5, exécutables.

Agno se distingue par ce qu'il embarque : mémoire, session, connaissances,
équipes, et une API de production, dans le même objet `Agent`. La contrepartie
est qu'il faut savoir **ce qui est chargé** et **ce qui coûte** — un agent avec
historique, mémoires et recherche de connaissances envoie beaucoup plus qu'on
ne croit, et c'est ce que ce projet rend visible.

Tous ces agents prennent leur modèle en paramètre : c'est ce qui rend le projet
exécutable sans clé, et ses tests possibles.
"""

from __future__ import annotations

from agno.agent import Agent
from agno.db.in_memory import InMemoryDb
from agno.team import Team
from agno.tools.reasoning import ReasoningTools

from .donnees import rechercher_offres, salaire_du_marche
from .modele import modele


# ------------------------------------------------- chapitre 1 : l'agent nu

def conseiller(m=None) -> Agent:
    return Agent(
        model=modele(m),
        instructions="Tu es un conseiller carriere du portail syllatech.",
        markdown=True,
    )


# ------------------------------------------- chapitre 2 : outils et raisonnement

def conseiller_outille(m=None, avec_raisonnement: bool = False) -> Agent:
    """Un agent qui interroge la base.

    `ReasoningTools` n'est pas un modèle de raisonnement : c'est un **outil**
    qui donne à l'agent de quoi poser ses étapes avant de répondre. La
    distinction compte — il fonctionne avec n'importe quel modèle, et il coûte
    des tours supplémentaires. Le chapitre 2 mesure ces tours.
    """
    outils = [rechercher_offres, salaire_du_marche]
    if avec_raisonnement:
        outils.append(ReasoningTools(add_instructions=True))
    return Agent(
        model=modele(m),
        tools=outils,
        instructions="Reponds en citant les offres rendues par tes outils.",
    )


# ----------------------------------------- chapitre 4 : mémoire et session

def conseiller_avec_memoire(m=None, db=None) -> Agent:
    """Historique de session ET mémoires utilisateur — deux choses distinctes.

    ⚠️ `enable_user_memories` N'EXISTE PLUS. Le cours l'écrit ; sur Agno 3.x
    `Agent(...)` lève `TypeError: unexpected keyword argument`. Il a été scindé
    en trois interrupteurs distincts, et la séparation est un progrès :

        update_memory_on_run    extraire des mémoires à chaque tour
        add_memories_to_context   les réinjecter dans le contexte
        enable_agentic_memory     laisser l'agent décider quoi retenir

    On peut donc écrire sans relire, ou relire sans écrire — ce que le
    booléen unique ne permettait pas.

    `add_history_to_context` rejoue les messages de **cette session**.
    Les mémoires, elles, sont des faits durables réutilisés dans **toutes**
    les sessions de l'utilisateur.

    Les confondre est l'erreur courante, et elle coûte : l'historique grossit
    à chaque tour et repart de zéro à la session suivante, là où une mémoire
    tient en une phrase et survit.

    `InMemoryDb` est ici volontaire : le cours montre `SqliteDb(db_file=...)`,
    qui demande SQLAlchemy et laisse un fichier derrière lui. La FORME est la
    même — `db=` sur l'agent — et passer à SQLite ne change qu'une ligne.
    """
    return Agent(
        model=modele(m),
        db=db if db is not None else InMemoryDb(),
        tools=[rechercher_offres],
        add_history_to_context=True,
        update_memory_on_run=True,
        add_memories_to_context=True,
        instructions="Retiens les preferences du candidat.",
    )


# --------------------------------------------- chapitre 5 : équipe d'agents

def equipe(m=None) -> Team:
    """Deux spécialistes et un coordinateur.

    Le point à comprendre : chaque membre est un agent **complet**, avec son
    propre modèle et ses propres outils. Une équipe de trois, ce sont donc au
    moins trois additions — et le chapitre 5 les compte.
    """
    analyste = Agent(
        name="Analyste offres",
        role="Interroge la base des offres du job portal",
        model=modele(m),
        tools=[rechercher_offres],
    )
    economiste = Agent(
        name="Analyste salaires",
        role="Donne les salaires du marche",
        model=modele(m),
        tools=[salaire_du_marche],
    )
    return Team(
        members=[analyste, economiste],
        model=modele(m),
        instructions="Combine les offres et les salaires en une reponse unique.",
    )


# ------------------------------------------- chapitre 3 : les connaissances

def conseiller_documente(m=None) -> Agent:
    """Un agent qui cherche dans la base documentaire avant de repondre.

    `search_knowledge=True` est ce que le cours appelle la « recherche
    agentique » : l'agent decide LUI-MEME quand chercher, au lieu qu'on lui
    colle systematiquement des extraits. La difference se mesure — chapitre 3.
    """
    from .connaissances import recherche
    return Agent(
        model=modele(m),
        knowledge_retriever=recherche,
        search_knowledge=True,
        instructions="Reponds en citant la documentation interne.",
    )
