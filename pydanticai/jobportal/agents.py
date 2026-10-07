"""Les agents du job portal — ceux des chapitres 1 à 3, exécutables.

Le fil directeur de PydanticAI tient en une phrase : **la sortie est un
modèle Pydantic, donc elle est validée**. Pas « le modèle a probablement
répondu un entier entre 0 et 10 » — un entier entre 0 et 10, ou une erreur.

Tout ce qui suit prend son modèle **en paramètre**. C'est ce qui rend les
tests possibles sans clé d'API, et c'est aussi ce qui permettra de changer de
fournisseur sans toucher au reste.
"""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext

from .donnees import DatabaseConn
from .modele import modele


# ------------------------------------------------------- chapitre 1 : sortie

class Analyse(BaseModel):
    """La sortie de l'agent conseil. Ces contraintes sont EXÉCUTÉES.

    `risque` hors de [0, 10] n'est pas « une réponse un peu bizarre » : c'est
    une `ValidationError`, et PydanticAI renvoie l'erreur au modèle pour qu'il
    se corrige. Un agent qui rend du texte libre vous laisse ce contrôle à
    écrire vous-même, à chaque appel, et vous l'oublierez une fois.
    """

    conseil: str = Field(min_length=1)
    risque: int = Field(ge=0, le=10, description="0 = sûr, 10 = très risqué")


def agent_conseil(m=None) -> Agent[None, Analyse]:
    return Agent(
        modele(m),
        instructions="Tu conseilles les candidats du portail syllatech.",
        output_type=Analyse,
    )


# --------------------------------------------- chapitre 2 : deps et outils

@dataclass
class Deps:
    """Les dépendances, injectées à l'exécution — pas des variables globales.

    C'est le point du chapitre 2, et il est plus profond qu'il n'y paraît : un
    outil ne « connaît » pas la base, il la reçoit. On peut donc en passer une
    autre en test, une autre par tenant, une autre par requête — sans toucher
    au code de l'agent.
    """

    candidat_id: int
    db: DatabaseConn


class Recommandation(BaseModel):
    resume: str
    offres_citees: list[str] = Field(default_factory=list)
    confiance: int = Field(ge=0, le=10)


def agent_offres(m=None) -> Agent[Deps, Recommandation]:
    agent = Agent(modele(m), deps_type=Deps, output_type=Recommandation)

    @agent.tool
    async def offres_du_candidat(ctx: RunContext[Deps],
                                 seulement_actives: bool) -> list[str]:
        """Liste les offres suivies par le candidat.

        La docstring est envoyée au modèle : c'est sa seule indication sur ce
        que fait l'outil. Les annotations de type, elles, deviennent le schéma
        des arguments. Retirer l'annotation de `seulement_actives` et le
        modèle ne saura plus quoi passer.
        """
        return await ctx.deps.db.offres(ctx.deps.candidat_id, seulement_actives)

    return agent


def agent_strict(m=None) -> Agent[Deps, Recommandation]:
    """Le même, avec un validateur de sortie — la deuxième ligne de défense.

    Pydantic valide la FORME. Un validateur de sortie valide le SENS : ici,
    qu'une offre citée existe réellement. Un modèle qui invente une offre
    plausible produit une sortie parfaitement valide au sens du schéma.
    """
    agent = agent_offres(m)

    @agent.output_validator
    async def les_offres_existent(ctx: RunContext[Deps],
                                  sortie: Recommandation) -> Recommandation:
        # TODO : lever ModelRetry si la sortie cite une offre absente de la base, en NOMMANT les offres fautives dans le message (il est renvoye au modele, qui recommence). Trois tests le verifient, dont un qui exige que le message contienne « n'existent pas ».
        return sortie

    return agent


# ------------------------------- chapitre 3 : instructions dynamiques

def agent_personnalise(m=None) -> Agent[Deps, Recommandation]:
    """Des instructions calculées à CHAQUE exécution.

    La différence avec `instructions=` en paramètre : celles-ci sont une
    fonction, réévaluée à chaque `run`. Le nom du candidat, la date, l'état
    de la base — tout ce qui change entre deux appels a sa place ici, et
    nulle part ailleurs.
    """
    agent = agent_offres(m)

    @agent.instructions
    async def ajouter_nom(ctx: RunContext[Deps]) -> str:
        nom = await ctx.deps.db.nom(ctx.deps.candidat_id)
        return f"Le candidat s'appelle {nom!r}."

    @agent.instructions
    def cadrer() -> str:
        return "Ne cite que des offres rendues par les outils."

    return agent
